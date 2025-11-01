import logging
import threading
import asyncio
from p2p_minner.block_chain import BlockChain,Block
log = logging.getLogger(__name__)
class Minner:
    def __init__(self,block_chain:BlockChain,stop_event:threading.Event):
        """
            写一个简单的挖矿程序的实现
        """
        self.stop_mining_event =stop_event
        self.chian = block_chain
        self.minner_task = None
        pass

    @staticmethod
    def do_mining_loop(prev_block:Block,event:threading.Event):
        log.debug(f'[挖矿线程]开始挖矿,prev block{prev_block}')
        nonce = 0
        new_block =  Block(prev_block.hash(),0, prev_block.bits, int(time.time()),height=prev_block.height + 1)
        while True:
            new_block.nonce = nonce
            if nonce % 100000 ==0:
                if event.is_set():
                    log.debug('[挖矿线程]收到中止挖矿通知,退出挖矿...')
                    return None
            if new_block.is_validate():
                log.debug(f'[挖矿线程] 找到新的区块，区块信息:{new_block} ')
                return new_block
            nonce += 1
    async def start(self):
        # 开始挖矿
        await self.restart()
        #这里还有其它操作
    async def restart(self):
        # 重新挖矿
        self.stop_mining_event.set()
        log.debug('重新开始挖矿程序...')
        if self.minner_task and not self.minner_task.done():
            log.debug('等待挖矿任务结束...')
            self.minner_task.cancel()
            try:
                await self.minner_task
            except asyncio.CancelledError :
                log.debug('挖矿任务取消成功...')
            log.debug('挖矿任务结束')
        self.stop_mining_event.clear()
        self.minner_task =asyncio.create_task(self.do_minner())
    async def do_minner(self):
        # 新区块挖矿'
        log.debug('开始挖矿')
        while True:
            prev_block = self.chian.get_best_tip()
            new_block = await asyncio.to_thread(Minner.do_mining_loop,prev_block,self.stop_mining_event)
            if new_block:
                if self.chian.add_block(new_block):
                    log.debug('新区块增加成功...可这可以开始发布消息')
                else:
                    log.debug('新区块增加失败...')
            else:
                log.debug('挖矿结果为空，挖矿终止')
                break
        log.debug('挖矿结束')