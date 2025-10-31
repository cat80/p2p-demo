import hashlib
import io
import logging
import time
import base64
import threading
import asyncio
import queue
from config import setup_logging
setup_logging()
log = logging.getLogger(__name__)

def get_hash(obj):
    if not isinstance(obj,(bytes,bytearray)):
        obj=str(obj).encode('utf8')
    return hashlib.sha256(obj).digest()
class BlockChain:
    def __init__(self):
        self.blocks =[]

    def init_block(self):
        if not self.blocks:
            self.blocks.append([get_hash('778899'), 0])
    def add_block(self,block):
        self.blocks.append(block)
        return True
    def get_best_tip(self):
        if self.blocks:
            return self.blocks[-1]
        return None
    def reset_chian(self):
        self.blocks = []
        self.init_block()

def do_minner_blocking_loop(prev_hash:bytes,stop_event:threading.Event):
    """
        把挖矿需要顾不得计算的独立出来
    """
    nonce = 0
    while True:
        if nonce % 10000 == 0:
            if stop_event.is_set():
                log.debug(f'recv quit event signal,quit mining...')
                return None
        n_bytes = nonce.to_bytes(4, byteorder="little")
        new_hash = get_hash(prev_hash + n_bytes)
        if new_hash.startswith(b'\x00\x00\x00'):
            log.debug(f'[mining thread]find block nonce:{nonce},hash:{new_hash.hex()},prev:{prev_hash.hex()}')
            #直接返回交给eventloop处理
            return [new_hash, nonce]
        nonce += 1

class Minner:
    def __init__(self,block_chain:BlockChain):
        """
            写一个简单的挖矿程序的实现
        """
        self.stop_mining_event = threading.Event()
        self.chian = block_chain
        self.queue = queue.Queue()
        self.check_queue_thread =None
        self.minner_task =None
        self.input_task = None
        # self.minner_task =None
        pass

    async def start(self):
        """
            开始任务
        :return:
        """

        # self.check_queue_thread = threading.Thread(target=self.check_queue)
        # self.check_queue_thread.start()
        self.input_task =  asyncio.create_task(self.handler_input())
        await  self.restart_minner()
        await self.input_task
    def check_queue(self):
        """
            查询队列状态
        :return:
        """
        while True:
            try:
                new_block  = self.queue.get(timeout=5)
                log.debug(f'find new block,block hash {new_block[0].hex()},nonce:{new_block[1]}')
                if self.chian.add_block(block=new_block):
                    log.debug('block add success')
                log.debug(f'chian len:{len(self.chian.blocks)}')
            except queue.Empty as empty:
                log.debug(f'current queue empty.chian len:{len(self.chian.blocks)}')
            except Exception as e:
                log.exception('exception occur')
                time.sleep(5)

    async  def handler_input(self):
        while True:
            # 异步等等
            cmd = await asyncio.to_thread(  input,'>')
            if cmd ==  'restart':
                log.debug('restart ming while empty chian blocks...')
                self.chian.reset_chian()
                await self.restart_minner()
            elif cmd == 'add':
                # 增加一个假的 fake
                current_time =  int(time.time())
                fake_hash = get_hash(current_time)
                self.chian.blocks.append([fake_hash,current_time])
                log.debug(f'add fake block.restart mining...')
                await self.restart_minner()
            else:
                log.debug(f'invalid cmd:{cmd}')


    async def restart_minner(self):
        # 这里需要重新启动挖矿线程，让之前的消息退出
        self.stop_mining_event.set()
        while self.minner_task and not self.minner_task.done():
            log.debug(f'waiting mining task quit....')
            log.debug(f'waiting mining task quit....')

        self.stop_mining_event.clear()  # 清除消息量
        self.minner_task = asyncio.create_task(self.do_minner())

    async def do_minner(self):
        # 新区块挖矿
        log.debug('start mining....')
        while True:
            prev_hash = self.chian.get_best_tip()[0]
            new_block = await asyncio.to_thread(do_minner_blocking_loop,prev_hash,self.stop_mining_event)
            if new_block:
                log.debug(f'find new block,block hash {new_block[0].hex()},nonce:{new_block[1]}')
                if self.chian.add_block(block=new_block):
                    log.debug('new block add success')
                else:
                    log.debug('new block add fail.')
                log.debug(f'chian len:{len(self.chian.blocks)}')
            else:
                # 直接结束
                break
        log.debug('mining quit....')
def check():
    prev_hash = bytes.fromhex('000044a79098092823b04575672fd8d9c29e6d44d6d61daf4edeb6d5ba6eab25')

    nonce = 26363
    print(get_hash(prev_hash +     nonce.to_bytes(4,byteorder='little') ))
def run_main1():
    log.debug('开始执行')
    chian = BlockChain()
    chian.init_block()
    event = threading.Event()

    minner = Minner(chian)
    block_hash = b'\xab\xcd\xef\00'
    print(minner.chian.get_best_tip()[0].hex())
    block1 = minner.do_minner()
    chian.add_block(block1)
    block2=  minner.do_minner()
    chian.add_block(block2)
    for block  in chian.blocks:
        print(block[0].hex(),block[1])
    # print(chian.mainChian)
async def run_main():
    log.debug('开始执行')
    chian = BlockChain()
    chian.init_block()
    minner = Minner(chian)
    await minner.start()
if __name__ == "__main__":
    asyncio.run(run_main())