import selectors
import time
import heapq
from collections import deque


# ======================================================================
# 1. Future 对象：异步操作的最终结果 (无变化)
# ======================================================================
class Future:
    """
    代表一个尚未完成的异步操作的结果。
    Task 在等待另一个 Future 完成时, 会被暂时挂起。
    """

    def __init__(self):
        self.result = None
        self._done = False
        self._waiting_tasks = []

    def done(self):
        return self._done

    def set_result(self, result):
        """当异步操作完成时，设置结果并唤醒所有等待它的任务。"""
        self.result = result
        self._done = True
        for task in self._waiting_tasks:
            EVENT_LOOP.schedule(task)

    def add_waiting_task(self, task):
        """添加一个正在等待此 Future 结果的任务。"""
        self._waiting_tasks.append(task)

    def __await__(self):
        if not self._done:
            yield self
        return self.result


# ======================================================================
# 2. Task 对象：协程的执行单元 (无变化)
# ======================================================================
class Task:
    """
    包装一个协程，管理其执行状态。
    """

    def __init__(self, coro):
        self.coro = coro
        self.future = Future()

    def run(self):
        """
        执行或恢复协程，直到下一个 yield 点。
        """
        try:
            yielded_value = self.coro.send(None)
            if isinstance(yielded_value, Future):
                yielded_value.add_waiting_task(self)
            else:
                EVENT_LOOP.schedule(self)
        except StopIteration as e:
            self.future.set_result(e.value)


# ======================================================================
# 3. EventLoop：事件调度核心 (有修改)
# ======================================================================
class EventLoop:
    """
    事件循环，负责调度和执行所有的 Task。
    """

    def __init__(self):
        self.selector = selectors.DefaultSelector()
        self.ready_queue = deque()
        # 【修改点 1】: sleeping 队列现在存放 (唤醒时间, 回调函数)
        self.sleeping = []
        self.is_running = False

    def schedule(self, task):
        """将一个任务放入就绪队列。"""
        self.ready_queue.append(task)

    def create_task(self, coro):
        """创建一个 Task 并将其加入调度队列。"""
        task = Task(coro)
        self.schedule(task)
        return task

    # 【修改点 2】: sleep 方法现在接受一个 callback 回调函数
    def call_later(self, delay, callback):
        """安排一个回调函数在未来的某个时间点执行。"""
        wakeup_time = time.time() + delay
        heapq.heappush(self.sleeping, (wakeup_time, callback))

    def run(self, main_coro):
        """运行事件循环，直到主协程结束。"""
        main_task = self.create_task(main_coro)
        self.is_running = True

        while self.is_running:
            # 1. 优先处理所有已就绪的任务
            while self.ready_queue:
                task = self.ready_queue.popleft()
                task.run()
                if main_task.future.done():
                    self.is_running = False

            if not self.is_running:
                break

            # 2. 检查是否有到期的休眠任务/回调
            if self.sleeping:
                wakeup_time, callback = self.sleeping[0]
                now = time.time()
                if now >= wakeup_time:
                    _, callback = heapq.heappop(self.sleeping)
                    # 【修改点 3】: 直接执行回调函数，而不是 schedule 一个 Task
                    callback()
                    continue

                    # 3. 计算超时
            timeout = self.sleeping[0][0] - time.time() if self.sleeping else None

            # 4. 阻塞等待
            self.selector.select(timeout)


# ======================================================================
# 4. 对外暴露的 API (有修改)
# ======================================================================
EVENT_LOOP = EventLoop()


# 【修改点 4】: sleep 函数现在使用了新的、更清晰的 call_later 方法
async def sleep(delay):
    """
    一个模拟 asyncio.sleep 的协程。
    """
    # 1. 创建一个 Future，代表“睡眠结束”这个事件
    future = Future()
    # 2. 告诉事件循环：“请在 delay 秒后，调用这个函数: `future.set_result(None)`”
    #    我们使用 lambda 来创建一个简单的匿名函数。
    EVENT_LOOP.call_later(delay, lambda: future.set_result(None))
    # 3. 等待这个 Future 完成。当上面的回调被执行时，这一行就会结束等待。
    await future


# gather 函数无变化
async def gather(*coros):
    """
    一个模拟 asyncio.gather 的协程，支持并行等待。
    """
    tasks = [EVENT_LOOP.create_task(coro) for coro in coros]
    results = []
    for task in tasks:
        results.append(await task.future)
    return results


# ======================================================================
# 5. 示例代码 (无变化，但现在运行在更健壮的循环上)
# ======================================================================
async def countdown(name, count):
    for i in range(count, 0, -1):
        print(f"[{time.strftime('%X')}] {name}: T-minus {i}")
        await sleep(1)
    return f"{name} finished!"


async def main():
    print(f"[{time.strftime('%X')}] --- 主程序开始 ---")
    results = await gather(countdown("任务A", 3), countdown("任务B", 4))
    print(f"[{time.strftime('%X')}] Gather 完成，结果: {results}")
    task_c = EVENT_LOOP.create_task(countdown("任务C", 2))
    print(f"[{time.strftime('%X')}] 任务C已在后台运行，主程序先休眠0.5秒...")
    await sleep(0.5)
    print(f"[{time.strftime('%X')}] 主程序休眠结束，现在等待任务C完成。")
    result_c = await task_c.future
    print(f"[{time.strftime('%X')}] 任务C完成，结果: {result_c}")
    print(f"\n[{time.strftime('%X')}] --- 主程序结束 ---")


if __name__ == "__main__":
    EVENT_LOOP.run(main())

