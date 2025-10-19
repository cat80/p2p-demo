import datetime
import random
import time


def generator_fun(name):
    counter = 1
    for _ in range(5):
        time.sleep(random.uniform(0.1,2))
        # 生成一个对象
        yield [counter,f'{name}-{counter}']
        counter +=1

mygen1 = generator_fun('test')
mygen2 =  generator_fun('test2')
while True:
    gen1_result = next(mygen1)
    print(datetime.datetime.now(),gen1_result)
    gen2_result = next(mygen2)
    print(datetime.datetime.now(),gen2_result)