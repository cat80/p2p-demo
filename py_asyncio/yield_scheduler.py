"""
    先写用生成器（yield)，实现一个并行的任务处理。这是理解异步的一个大前提。
"""
import random
import time
from collections import deque
import datetime
def print_with_date(txt):
    return print(f"[{datetime.datetime.now()}]-{txt}")

 



def task_a():
    print_with_date('start task-a')

    for i in range(5):
        print_with_date(f'task-a:({i+1}/5)')
        yield random.uniform(1, 2)
    print_with_date('end task-a')

def task_b():
    print_with_date('start task-b')
    for i in range(3):
        print_with_date(f'task-b:({i+1}/3)')
        yield random.uniform(1,2)
    print_with_date('end task-b')

class Scheduler():

    task_deque:deque
    def __init__(self):
        self.task_deque= deque()
        self.sleepings = []
    def add_task(self,task_generator):
        # 把生成器增加到任务队列
        self.task_deque.append(task_generator)
    def run(self):
        main_running = True
        while main_running:
            while self.task_deque:
                task = self.task_deque.popleft()
                try:
                    delay = next(task)
                #     这里如果返回一个当前任务的中断时间，则这里面需要先去执行其它任务，然后再等待执行
                #     如果能获取到生成器，则说明任务可继续
                    if delay and delay > 0: #如果需要等待执行
                        wakeup_time = time.time()+delay
                        self.sleepings.append([wakeup_time,task])
                    else:
                        self.task_deque.append(task)
                except StopIteration:
                    print_with_date(f'调度器任务:{task}完成成了')
            if not self.sleepings:
                # 没有要等待线程了
                main_running = False
            else:
                sleep_task  = self.sleepings[0]
                wakeup_time, task = sleep_task[0], sleep_task[1]
                # 进行休眠，线程等等
                sleep_time = wakeup_time - time.time()
                if sleep_time >= 0:
                    # 直接io阻塞,这里如果是网络io如recv,send,acceptselector.select注册的时候也会阻塞等等吗？如果是的话，如果注册等等多个
                    time.sleep(sleep_time)
                # 结束后把把前任务增加到队列，继续执行
                self.task_deque.append(task)
                self.sleepings = self.sleepings[1:]
            # 如果有需要等等的任务
            # 从性能考虑，应该对等待线程排队


if __name__ == "__main__":
    scheduler  = Scheduler()
    scheduler.add_task(task_a())
    scheduler.add_task(task_b())

    scheduler.run()
