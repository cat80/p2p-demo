import socket
import selectors
from collections import deque
import time


# ======================================================================
# 核心调度器 (EventLoop)
# ======================================================================

class Scheduler:
    def __init__(self):
        self.ready_queue = deque()
        self.selector = selectors.DefaultSelector()
        # 用一个字典来映射 "文件描述符" 到 "等待它的任务"
        # 这样当 selector 告诉我们哪个文件描述符就绪时，我们能立刻找到对应的任务
        self.waiting_tasks = {}

    def add_task(self, task_generator):
        """将一个新任务（生成器）加入就绪队列"""
        self.ready_queue.append(task_generator)

    def wait_for_read(self, sock, task):
        """
        注册一个任务，使其等待某个 socket 变得可读。
        """
        # sock.fileno() 是 socket 的唯一标识符
        # 我们告诉 selector：“请监视这个 socket，一旦可读，就通知我”
        self.selector.register(sock, selectors.EVENT_READ, data=task)
        self.waiting_tasks[sock.fileno()] = task

    def wait_for_write(self, sock, task):
        """
        注册一个任务，使其等待某个 socket 变得可写。
        """
        self.selector.register(sock, selectors.EVENT_WRITE, data=task)
        self.waiting_tasks[sock.fileno()] = task

    def run(self):
        print("[调度器] 网络事件循环启动！")
        while self.ready_queue or self.waiting_tasks:
            # 1. 优先处理所有已就绪的任务
            while self.ready_queue:
                task = self.ready_queue.popleft()
                try:
                    # 恢复任务，直到下一个 yield
                    yield_event, sock = next(task)

                    # 根据任务 yield 的内容，决定是等待读还是等待写
                    if yield_event == 'read':
                        self.wait_for_read(sock, task)
                    elif yield_event == 'write':
                        self.wait_for_write(sock, task)
                    else:
                        # 如果 yield 了其他东西，我们假定它只是想让出CPU
                        self.add_task(task)

                except StopIteration:
                    print(f"[调度器] 任务 {task.__name__} 完成了。")

            # 2. 如果没有就绪任务了，就调用 selector 等待网络事件
            # select() 是唯一的阻塞点。它会等待，直到有已注册的 socket 准备就绪。
            events = self.selector.select()
            for key, mask in events:
                # 3. selector 被唤醒，处理所有就绪的事件
                task_to_resume = key.data
                sock = key.fileobj
                # 从 selector 的监视列表和我们的等待字典中移除
                self.selector.unregister(sock)
                del self.waiting_tasks[sock.fileno()]
                # 将被唤醒的任务重新放回就绪队列
                self.ready_queue.append(task_to_resume)

        print("[调度器] 所有任务完成，事件循环结束。")


# ======================================================================
# 异步任务 (生成器)
# ======================================================================

def handle_client(client_sock):
    """处理单个客户端连接的任务"""
    print(f"[服务器] 接受了新连接: {client_sock.getpeername()}")
    while True:
        # 暂停，并告诉调度器：当这个 socket 可读时，请唤醒我
        yield 'read', client_sock

        # 被唤醒后，我们知道现在可以安全地接收数据了
        try:
            data = client_sock.recv(1024)
            if not data:
                # 客户端关闭了连接
                print(f"[服务器] 客户端 {client_sock.getpeername()} 关闭了连接。")
                break

            print(f"[服务器] 收到来自 {client_sock.getpeername()} 的数据: {data.decode()}")

            # 暂停，并告诉调度器：当这个 socket 可写时，请唤醒我
            yield 'write', client_sock

            # 被唤醒后，我们知道现在可以安全地发送数据了
            client_sock.sendall(b'ECHO >> ' + data)
        except ConnectionResetError:
            print(f"[服务器] 客户端 {client_sock.getpeername()} 强制关闭了连接。")
            break

    client_sock.close()


def server(port):
    """监听连接的服务器主任务"""
    print(f"[服务器] 启动，监听端口 {port}...")
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_sock.setblocking(False)  # 关键！设置为非阻塞
    listen_sock.bind(('', port))
    listen_sock.listen(5)

    while True:
        # 暂停，并告诉调度器：当监听 socket 可读时（即有新连接进来），请唤醒我
        yield 'read', listen_sock

        # 被唤醒后，我们知道现在可以安全地接受连接了
        client_sock, addr = listen_sock.accept()
        client_sock.setblocking(False)  # 同样设置为非阻塞

        # 为这个新客户端创建一个独立的任务，并加入调度
        scheduler.add_task(handle_client(client_sock))


def client(id, port):
    """模拟一个客户端的任务"""
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.setblocking(False)  # 设置为非阻塞

    try:
        # 非阻塞连接会立刻返回，并可能抛出 BlockingIOError
        client_sock.connect(('', port))
    except BlockingIOError:
        pass  # 这是正常的

    # 暂停，并告诉调度器：当连接完成时（socket 变为可写），请唤醒我
    yield 'write', client_sock

    print(f"[客户端 {id}] 连接成功！")

    for i in range(3):
        message = f"Hello from client {id}, message {i + 1}".encode()
        yield 'write', client_sock
        client_sock.send(message)
        print(f"[客户端 {id}] 发送: {message.decode()}")

        yield 'read', client_sock
        response = client_sock.recv(1024)
        print(f"[客户端 {id}] 收到: {response.decode()}")
        time.sleep(1)  # 纯粹为了演示方便，模拟客户端思考

    client_sock.close()


# ======================================================================
# 启动
# ======================================================================
if __name__ == "__main__":
    scheduler = Scheduler()
    PORT = 18877

    # 启动服务器任务
    scheduler.add_task(server(PORT))

    # 启动两个客户端任务来连接服务器
    scheduler.add_task(client(1, PORT))
    scheduler.add_task(client(2, PORT))

    # 运行事件循环！
    scheduler.run()
