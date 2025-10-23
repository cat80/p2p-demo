import random
import selectors
import socket
import time
import heapq
from collections import deque


# =======================================================================
# Future, Task 和 Coroutine 的核心定义
# 这是整个异步模型的基石
# =======================================================================

class Future:
    """
    代表一个未来可能完成的操作的结果。
    Task 是 Future 的一种特殊形式。
    """

    def __init__(self, loop):
        self._loop = loop
        self._done = False
        self._result = None
        self._callbacks = []

    def set_result(self, result):
        """标记 Future 为完成并设置其结果。"""
        if self._done:
            return
        self._done = True
        self._result = result
        # 结果准备好后，执行所有回调函数
        for callback in self._callbacks:
            self._loop.call_soon(callback, self)

    def add_done_callback(self, fn):
        """添加一个在 Future 完成时运行的回调。"""
        if self._done:
            self._loop.call_soon(fn, self)
        else:
            self._callbacks.append(fn)

    def __await__(self):
        """
        允许在 Future 对象上使用 await 关键字。
        'yield self' 将控制权交还给事件循环，
        直到这个 Future 完成。
        """
        if not self._done:
            yield self  # 关键点：交出控制权
        return self._result


class Task(Future):
    """
    一个驱动协程执行的任务对象。
    """

    def __init__(self, coro, loop):
        super().__init__(loop)
        self._coro = coro
        # 立即安排任务的第一步执行
        self._loop.call_soon(self._step)

    def _step(self, future=None):
        """
        执行协程的一步。
        如果协程 await 了一个 future，这个方法会作为 future 的回调被调用。
        """
        try:
            if future:
                # 如果我们是被一个 future 唤醒的，它的结果就是 send 的值
                next_future = self._coro.send(future._result)
            else:
                # 任务开始
                next_future = self._coro.send(None)
        except StopIteration as e:
            # 协程执行完毕，设置 Task 的最终结果
            self.set_result(e.value)
        else:
            # 协程 await 了另一个 future，
            # 添加 _step 作为回调，当那个 future 完成时继续执行
            next_future.add_done_callback(self._step)


# =======================================================================
# 事件循环 (Event Loop)
# 这是异步应用的心脏
# =======================================================================

class EventLoop:
    def __init__(self):
        self._ready = deque()  # 存储立即要执行的回调
        self._scheduled = []  # 存储定时任务的最小堆
        self._selector = selectors.DefaultSelector()  # I/O 多路复用

    def call_soon(self, callback, *args):
        """安排一个回调函数尽快执行。"""
        self._ready.append((callback, args))

    def call_later(self, delay, callback, *args):
        """安排一个回调函数在指定的延迟后执行。"""
        when = time.monotonic() + delay
        heapq.heappush(self._scheduled, (when, callback, args))

    def add_reader(self, fd, callback, *args):
        """注册一个文件描述符，当它可读时执行回调。"""
        try:
            key = self._selector.get_key(fd)
            mask = key.events
            data = key.data
            is_new = False
        except KeyError:
            mask = 0
            data = {}
            is_new = True

        data['r'] = (callback, args)
        mask |= selectors.EVENT_READ

        if is_new:
            self._selector.register(fd, mask, data)
        else:
            self._selector.modify(fd, mask, data)

    def remove_reader(self, fd):
        """移除一个已注册的可读文件描述符。"""
        try:
            key = self._selector.get_key(fd)
            mask = key.events & ~selectors.EVENT_READ
            data = key.data
            data.pop('r', None)

            if not mask:
                self._selector.unregister(fd)
            else:
                self._selector.modify(fd, mask, data)
        except KeyError:
            pass  # 已经取消注册，忽略

    def add_writer(self, fd, callback, *args):
        """注册一个文件描述符，当它可写时执行回调。"""
        try:
            key = self._selector.get_key(fd)
            mask = key.events
            data = key.data
            is_new = False
        except KeyError:
            mask = 0
            data = {}
            is_new = True

        data['w'] = (callback, args)
        mask |= selectors.EVENT_WRITE

        if is_new:
            self._selector.register(fd, mask, data)
        else:
            self._selector.modify(fd, mask, data)

    def remove_writer(self, fd):
        """移除一个已注册的可写文件描述符。"""
        try:
            key = self._selector.get_key(fd)
            mask = key.events & ~selectors.EVENT_WRITE
            data = key.data
            data.pop('w', None)

            if not mask:
                self._selector.unregister(fd)
            else:
                self._selector.modify(fd, mask, data)
        except KeyError:
            pass  # 已经取消注册，忽略

    def run_forever(self):
        """运行事件循环，直到没有任务。"""
        while True:
            # 1. 执行所有已就绪的回调
            while self._ready:
                callback, args = self._ready.popleft()
                callback(*args)

            # 2. 检查是否有到期的定时任务
            now = time.monotonic()
            while self._scheduled and self._scheduled[0][0] <= now:
                _, callback, args = heapq.heappop(self._scheduled)
                self.call_soon(callback, *args)

            # 3. 计算 select 的超时时间
            if self._scheduled:
                timeout = self._scheduled[0][0] - time.monotonic()
                timeout = max(0, timeout)
            elif self._ready:
                timeout = 0
            else:
                # 如果没有定时任务也没有就绪任务，可以阻塞等待 I/O
                # 但如果连 I/O 都没有，就退出循环
                if not self._selector.get_map():
                    break
                timeout = None  # 阻塞直到 I/O 事件发生

            # 4. 等待 I/O 事件
            try:
                events = self._selector.select(timeout)
            except InterruptedError:
                continue

            for key, mask in events:
                # 重点：复制 data 字典，因为 remove_* 方法会修改它
                data = key.data.copy()

                # 处理读事件
                if mask & selectors.EVENT_READ:
                    read_callback_data = data.get('r')
                    if read_callback_data:
                        callback, args = read_callback_data
                        self.remove_reader(key.fileobj)
                        self.call_soon(callback, *args)

                # 处理写事件
                if mask & selectors.EVENT_WRITE:
                    write_callback_data = data.get('w')
                    if write_callback_data:
                        callback, args = write_callback_data
                        self.remove_writer(key.fileobj)
                        self.call_soon(callback, *args)


# 全局事件循环实例
_current_loop = None


def get_event_loop():
    """获取当前线程的事件循环实例。"""
    global _current_loop
    if _current_loop is None:
        _current_loop = EventLoop()
    return _current_loop


# =======================================================================
# 公共 API (类似 asyncio 的顶层函数)
# =======================================================================

def run(coro):
    """运行一个协程，直到它完成。"""
    loop = get_event_loop()
    task = Task(coro, loop)
    loop.run_forever()
    return task._result


def create_task(coro):
    """创建一个任务并安排它在事件循环上执行。"""
    loop = get_event_loop()
    return Task(coro, loop)


async def sleep(delay):
    """异步睡眠。"""
    loop = get_event_loop()
    future = Future(loop)
    loop.call_later(delay, future.set_result, None)
    await future


async def gather(*coros):
    """并发运行多个协程，并等待它们全部完成。"""
    loop = get_event_loop()
    tasks = [create_task(coro) for coro in coros]

    gather_future = Future(loop)
    if not tasks:
        gather_future.set_result([])
        return []

    remaining = len(tasks)

    def on_task_done(task_future):
        nonlocal remaining
        remaining -= 1
        if remaining == 0:
            results = [task._result for task in tasks]
            gather_future.set_result(results)

    for task in tasks:
        task.add_done_callback(on_task_done)

    return await gather_future


# =======================================================================
# 异步网络 I/O (Reader 和 Writer)
# =======================================================================

class Reader:
    def __init__(self, sock, loop):
        self._sock = sock
        self._loop = loop
        self._buffer = bytearray()

    async def read(self, n):
        """读取最多 n 个字节。"""
        future = Future(self._loop)
        self._loop.add_reader(self._sock.fileno(), self._on_readable, future)
        await future

        data = self._sock.recv(n)
        return data

    async def readline(self):
        """读取一行（以 \n 结尾）。"""
        while b'\n' not in self._buffer:
            data = await self.read(1024)
            if not data:
                # 对端关闭连接
                return self._buffer
            self._buffer.extend(data)

        line_end = self._buffer.find(b'\n')
        line = self._buffer[:line_end + 1]
        self._buffer = self._buffer[line_end + 1:]
        return line

    def _on_readable(self, future):
        """当 socket 可读时的回调。"""
        future.set_result(None)


class Writer:
    def __init__(self, sock, loop):
        self._sock = sock
        self._loop = loop

    async def write(self, data):
        """写入数据到 socket。"""
        future = Future(self._loop)
        self._loop.add_writer(self._sock.fileno(), self._on_writable, future)
        await future

        return self._sock.send(data)

    def _on_writable(self, future):
        """当 socket 可写时的回调。"""
        future.set_result(None)

    def close(self):
        """关闭 socket。"""
        self._sock.close()


async def open_connection(host, port):
    """打开一个到指定 host 和 port 的 TCP 连接。"""
    loop = get_event_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)

    try:
        sock.connect((host, port))
    except BlockingIOError:
        # 非阻塞 connect 会立即返回，需要等待连接建立
        pass

    # 等待 socket 变为可写，这表示连接已成功建立
    future = Future(loop)
    loop.add_writer(sock.fileno(), future.set_result, None)
    await future

    return Reader(sock, loop), Writer(sock, loop)


# =======================================================================
# 示例：一个带广播功能的聊天服务器
# =======================================================================

# 全局列表，用于存储所有连接的客户端 Writer 对象
ALL_CLIENT_WRITERS = []


async def broadcast(message, sender_writer):
    """向除发送者外的所有客户端广播消息。"""
    # 遍历 writer 列表的副本，以防在迭代时列表被修改
    for writer in ALL_CLIENT_WRITERS[:]:
        if writer is not sender_writer:
            try:
                await writer.write(message)
            except (ConnectionResetError, BrokenPipeError):
                # 如果写入时发现连接已断开，则从列表中移除
                print("广播时发现一个断开的连接，正在清理...")
                ALL_CLIENT_WRITERS.remove(writer)
                writer.close()


async def handle_client(reader, writer):
    """处理单个客户端连接的广播逻辑。"""
    client_address = writer._sock.getpeername()
    print(f"新的客户端连接: {client_address}")
    ALL_CLIENT_WRITERS.append(writer)

    # 向新客户端发送欢迎消息
    welcome_msg = f"欢迎 {client_address} 加入聊天室! 当前在线 {len(ALL_CLIENT_WRITERS)} 人。\n".encode('utf8')
    await writer.write(welcome_msg)

    # 向所有其他客户端广播新用户加入的消息
    join_msg = f"[系统消息] {client_address} 已加入聊天室。\n".encode('utf8')
    await broadcast(join_msg, writer)

    try:
        while True:
            data = await reader.readline()
            if not data:
                break

            # 准备要广播的消息
            broadcast_msg = f"[{client_address[0]}:{client_address[1]}]> {data.decode('utf8')}".encode('utf8')
            # 调用广播函数
            await broadcast(broadcast_msg, writer)

    except (ConnectionResetError, BrokenPipeError):
        print(f"与 {client_address} 的连接意外断开。")
    finally:
        # 无论如何，客户端断开时都执行清理
        print(f"客户端 {client_address} 断开连接")
        if writer in ALL_CLIENT_WRITERS:
            ALL_CLIENT_WRITERS.remove(writer)
        writer.close()
        # 广播用户离开的消息
        leave_msg = f"[系统消息] {client_address} 已离开聊天室。\n".encode('utf8')
        await broadcast(leave_msg, None)  # 发送者为 None，表示系统消息


async def echo_server(host, port):
    """启动回显服务器。"""
    loop = get_event_loop()
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(5)
    server_sock.setblocking(False)

    print(f"服务器已在 {host}:{port} 启动")

    while True:
        # 异步接受连接
        future = Future(loop)
        loop.add_reader(server_sock.fileno(), future.set_result, None)
        await future

        client_sock, addr = server_sock.accept()
        client_sock.setblocking(False)
        print(f"接受来自 {addr} 的连接")

        # 为每个客户端创建一个任务来处理
        reader = Reader(client_sock, loop)
        writer = Writer(client_sock, loop)
        create_task(handle_client(reader, writer))


async def client_reciver(reader):
    while True:
        response = await reader.readline()
        print(f'客户端收到:{response.decode().strip()}')  # 持续从服务器获取数据


async def client_write(writer, client_name=None):
    write_msg = f'客户端时间:{time.time()},客户端:{client_name}\n'
    write_bytes = write_msg.encode('utf-8')
    while True:
        await writer.write(write_bytes)
        await sleep(random.uniform(1, 4))


async def echo_client(host, port, client_name='default client'):
    """启动客户端并发送几条消息。"""
    print("客户端启动，尝试连接...")
    reader, writer = await open_connection(host, port)
    print(f"{client_name}连接成功，发送第一条消息...")

    await writer.write(f'hello ,i\'m {client_name}\n'.encode('utf8'))
    response = await reader.readline()
    print(response.decode('utf8').strip())
    task_reader = client_reciver(reader)
    task_writer = client_write(writer, client_name)
    await gather(task_reader, task_writer)


if __name__ == '__main__':
    HOST, PORT = '127.0.0.1', 8888


    async def main():
        # 并发运行服务器和客户端
        server_task = create_task(echo_server(HOST, PORT))

        # 等待一会确保服务器已启动
        await sleep(0.1)

        client_task = echo_client(HOST, PORT, 'client1')
        client_task2 = echo_client(HOST, PORT, 'client2')
        # 等待客户端完成
        await gather(client_task, client_task2)

        # 在这个简化版本中，服务器会一直运行。
        # 在真实应用中，需要一种机制来优雅地停止服务器。
        # 例如，可以取消 server_task
        # server_task.cancel()
        print("\n示例运行完毕。服务器仍在后台运行，可手动停止程序。")


    run(main())


