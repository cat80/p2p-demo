"""
    先写用生成器（yield)，实现一个并行的任务处理。这是理解异步的一个大前提。
"""
import random
import time
from collections import deque
import datetime
import heapq
import selectors


def print_with_date(txt):
    return print(f"[{datetime.datetime.now()}]-{txt}")


def task_a():
    print_with_date('start task-a')

    for i in range(5):
        print_with_date(f'task-a:({i+1}/5)')
        # yield random.uniform(1, 2)
        yield 1.2
    print_with_date('end task-a')

def task_b():
    print_with_date('start task-b')
    for i in range(3):
        print_with_date(f'task-b:({i+1}/3)')
        yield 2
        # yield random.uniform(1,2)
    print_with_date('end task-b')

class Scheduler():

    ready_queue:deque
    def __init__(self):
        self.ready_queue= deque()
        self.sleepings = []
        self.selector = selectors.DefaultSelector()

    def add_task(self,task_generator):
        # 把生成器增加到任务队列
        self.ready_queue.append(task_generator)
    def run(self):
        while self.ready_queue or self.sleepings:
            while self.ready_queue:
                task = self.ready_queue.popleft()
                try:
                    delay = next(task)
                    #     这里如果返回一个当前任务的中断时间，则这里面需要先去执行其它任务，然后再等待执行
                    #     如果能获取到生成器，则说明任务可继续
                    wakeup_time = time.time() + delay
                    # 使用heapq 把需要唤醒的任务加到sleepings,以确保heapq总是能heappop最快的元素
                    heapq.heappush(self.sleepings,(wakeup_time,task))
                except StopIteration:
                    print_with_date(f'调度器任务:{task}完成成了')
            if not self.ready_queue:
                """
                  如果所有的队列都执行完成了
                """
                timeout = 0
                if self.sleepings:
                    # 有唤醒时间
                    wakeup_time,_ = self.sleepings[0]
                    timeout = wakeup_time - time.time()
                else:
                    print('无需要唤醒任务，eventloop结束')
                    break
                print_with_date(f"无就绪任务, selector 将等待 {max(0, timeout):.2f} 秒...")
                # 这里我理解了，sleep异步的实现，其实主要靠维护要等待sleep的任务列表来维护这些任务。然后，所有的任务都执行完后，等待最先执行完成的等等的那个。
                # 这里如果是管理异步的网络套接字会是怎么处理，如果有个代码中断等等网络IO，如何同时等待多个网络IO，以及保证第一个网络完成的会立刻通知我处理。

                self.selector.select(max(0, timeout))
            now = time.time()
            while self.sleepings and self.sleepings[0][0] < now:
                # 把第一个超时的任务重新放回ready queue执行
                _,task  =heapq.heappop(self.sleepings)
                self.ready_queue.append(task)


if __name__ == "__main__":
    scheduler  = Scheduler()
    scheduler.add_task(task_a())
    scheduler.add_task(task_b())

    scheduler.run()
