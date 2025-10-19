import  asyncio
import datetime
import random
import time
counter = 0

def print_with_date(msg):
    print(f'[{datetime.datetime.now()}]-{msg}')


async def fun_async1():
    pass
def normal_return_cortinue():
    # 这种写法是否可以
    return fun_async1()


async def fun1(name):
    print(f'start invoke:{name}')
    for _ in range(3):
        # 这里换成blocking 阻塞的sleep，似乎要等task1，执行完后，task2的执行。即使在主方法里面用了asyncio.gather.为什么。
        # time.sleep(random.uniform(0.1,1.0))
        await asyncio.sleep(random.uniform(0.1,2.0))
        print_with_date(f'{name},times:{_}')
    print(f'end invoke:{name}')
    return f'result:{name}'

async def nonasync_invoke():
    # 这里并不会并行执行完，本质上还是顺序同步执行的
    await fun1('task1')
    await fun1('task2')
async def my_gather(*args):
    task_list = [ asyncio.create_task(item)  for item in args ]
    result = []
    for task in task_list:
        result.append(await task)
    return result
async def test_mygahter():
    resutlist = await my_gather(fun1('task1'),fun1('task2'))
    print(resutlist)
async def async_invoke_fun1():
    print_with_date('start async_invoke_fun1')
    # 这里创建任务就执行了。是不是也可以分解成先fun('task1')创建协程
    task1 = asyncio.create_task(fun1('task1'))
    task2 = asyncio.create_task(fun1('task2'))
    await asyncio.sleep(3)
    print_with_date('do other jos finished.wait task1 and task2')
    task1_result =  await task1
    task2_result = await task2
    print_with_date(f'async_invoke_fun1，执行完成\r\n\r\n')
async def async_invoke_fun2():
    # 这里和async_invoke_fun1 这不是完成赞同
    task1_result,task2_result = await asyncio.gather(fun1('task1'),fun1('task2'))
    print_with_date(f'async_invoke_fun2，执行完成\r\n\r\n')

async def vs_task_and_gather():
    task1,task2 = asyncio.create_task(fun1('task1')),asyncio.create_task(fun1('task2'))
    # 1。种方法
    await task1
    await task2
    # 2. 方法
    #或者直接使用,gather差别在哪里？
    await asyncio.gather(task1,task2)
#     3. 方法
    await asyncio.gather(fun1('task1'),fun1('task2'))
#     这三种方法的异步
#     另外就是变量的问题比如下面的代码肯定是有问题的
    global counter
    current = counter
    current = counter + 1
    await fun1('task2')
    # 这里切换counter可能会在其它的地方改变原始的counter
    current += 1
    counter = current
#     但如果使用
    global counter
    counter = counter + 1
    await fun1('task2')
    # 这里切换后，直接使用。gobal 最新的值如
    global counter #或者这种不用
    counter = counter + 1
#     另外对一些线程安全的对象，比如dict['aa'] = 222,或者del ['aa']之类的会不会有问题

async def run_main():

    await async_invoke_fun1()
    await async_invoke_fun2()
    # 这里如何获取到返回值,怎么获取taskgroup和gather本质是什么区别吗？
    async with asyncio.TaskGroup() as tg:
        tg.create_task(fun1('task1'))
        tg.create_task(fun1('task2'))

if __name__ == "__main__":
    asyncio.run(test_mygahter())