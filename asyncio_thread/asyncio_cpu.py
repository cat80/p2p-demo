import hashlib
import logging
import asyncio
import random
import multiprocessing
from config import setup_logging
setup_logging()

log = logging.getLogger(__name__)
bits = 4 # 这里的难度代码要运算的次数，即hash前面0的个数.比如4代表可能运算
class Block:
    prev_hash:bytes
    nonce:int
    bits:int
    block_hash:bytes

class BlockChain:
    blocks:[Block]
    def __init__(self):
        self.blocks = []
    def add_block(self,block:Block):
        pass

class AsyncioCpuThread:


    async def task1(self,taskname='task1'):
        for _ in range(4):
            await asyncio.sleep(random.uniform(1,3))
            log.debug(f'{taskname} run in :{_}')
        return f"done_{taskname}"
    async def testSleepTask(self):
        log.debug('开始运行主任务')
        task1 = asyncio.create_task(self.task1('task1'))
        task2 = asyncio.create_task(self.task1('task2'))
        task3 = asyncio.create_task(self.task1('task3'))
        log.debug('开始主任务...')

        for _ in range(1, 10):
            await asyncio.sleep(1)
            log.debug(f'主任务处理,{_}')
        log.debug('主任务工作完成，等待其它任务完成')
        resut1, resut2, resut3 = await asyncio.gather(task1, task2, task3)
        log.debug(f'子任务完成返回值：{resut1},{resut2},{resut3}')

    async def testCpuThread(self):
        # cpu密码任务
        prev_block_hash = hashlib.sha256("789".encode('utf-8')).hexdigest()

        nonce = 0
        for i in range(0,10000):
            int_bytes = i.to_bytes(4,byteorder='little')

        log.debug(fr"prev hashid:{prev_block_hash}")
    async def run(self):
        log.debug('开始运行主任务')
        await self.testCpuThread()
        log.debug('主任退出')
if __name__ == "__main__":
    cpuThread = AsyncioCpuThread()
    asyncio.run(cpuThread.run())