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
    def get_best_tip(self):
        if self.blocks:
            return self.blocks[-1]
        return None
    def reset_chian(self):
        self.blocks = []
        self.init_block()

class Minner:
    def __init__(self,block_chain:BlockChain):
        """
            写一个简单的挖矿程序的实现
        """
        self.event = threading.Event()
        self.chian = block_chain
        self.minner_thread = None
        self.queue = queue.Queue()
        self.check_queue_thread =None
        pass

    def start(self):
        """
            开始线程
        :return:
        """
        self.check_queue_thread = threading.Thread(target=self.check_queue)
        self.restart_minner()
        self.check_queue_thread.start()
        self.handler_input()
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
    def handler_input(self):
        while True:
            cmd = input('>')
            if cmd ==  'restart':
                log.debug('restart ming while empty chian blocks...')
                self.chian.reset_chian()
                self.restart_minner()
            elif cmd == 'add':
                # 增加一个假的 fake
                current_time =  int(time.time())
                fake_hash = get_hash(current_time)
                self.chian.blocks.append([fake_hash,current_time])
                log.debug(f'add fake block.restart mining...')
                self.restart_minner()
            else:
                log.debug(f'invalid cmd:{cmd}')


    def restart_minner(self):
        # 这里需要重新启动挖矿线程，让之前的消息退出
        self.event.set()
        while self.minner_thread and  self.minner_thread.is_alive():
            time.sleep(1)
            log.debug(f'waiting mining thread quit....')
        self.event.clear()  # 清除消息量
        self.minner_thread = threading.Thread(target=self.do_minner)
        self.minner_thread.start()

    def do_minner(self):
        # 新区块挖矿
        log.debug('start mining....')
        nonce = 0
        prev_hash = self.chian.get_best_tip()[0]
        while True:
            if nonce % 10000 ==0:
                if self.event.is_set():
                    log.debug(f'recv quit event signal,quit mining...')
                    break
            n_bytes = nonce.to_bytes(4,byteorder="little")
            new_hash = get_hash(prev_hash+n_bytes)
            if new_hash.startswith(b'\x00\x00\x00'):
                log.debug(f'find block nonce:{nonce},hash:{new_hash.hex()},prev:{prev_hash.hex()}')
                self.queue.put([new_hash,nonce])
                prev_hash = new_hash
                nonce = -1
            nonce +=1
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
def run_main():
    log.debug('开始执行')
    chian = BlockChain()
    chian.init_block()
    minner = Minner(chian)
    minner.start()
    log.debug('执行完成')
if __name__ == "__main__":
    run_main()