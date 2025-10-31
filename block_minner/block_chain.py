"""
    这里模拟pow进行p2p挖矿。包含简单的节点发现，节点管理。
    简化挖矿逻辑，只对区块的难度做验证，没有考虑重组的问题。
"""
import datetime
import io
import logging
import hashlib
import struct
import time
import base64
from threading import Event
from typing import List

from jsonschema.validators import create

from config import setup_logging

log = logging.getLogger(__name__)

def int_to_bytes(i:int):
    # 统一int为8个字节
    return i.to_bytes(length=4,byteorder="little")

class Block:
    BLOCK_BIN_FORMAT = '<32sIIII'
    DEFAULT_BITS = 3 # 这里的难度代码要运算的次数，即hash前面N的个数.比如4代表前四个字节0x00000000aa才符合要求，要计算255^3才有可能。
    BLOCK_BIN_LEN = 64
    prev_hash:bytes
    bits: int
    timestamp: int
    nonce:int
    height:int # 区块高度

    def __init__(self,prev_hash,nonce,bits,timestamp,height):
        self.prev_hash = prev_hash
        self.nonce= nonce
        self.bits = bits
        self.timestamp  = timestamp
        self.height = height

    def serialize(self):
        # 序列化 高度在真正的项目是不需要序列化的，因为有hash和位置就能算出高度了。
        return struct.pack(Block.BLOCK_BIN_FORMAT,
                           self.prev_hash,
                           self.nonce,
                           self.bits,
                           self.timestamp,
                           self.height
                           )
    @classmethod
    def deserialize(cls,byte_datas):
        prev_hash,nonce,bits,timestamp,height = struct.unpack(Block.BLOCK_BIN_FORMAT,byte_datas)
        return cls(prev_hash,nonce,bits,timestamp,height)
    def to_b64(self):
        return base64.b64encode(self.serialize()).decode('utf8')

    @classmethod
    def from_b64(cls,block_b64):
        return Block.deserialize(base64.b64decode(block_b64))

    def hash(self):
        # 计算区块hash
        return hashlib.sha256(self.serialize()).digest()

    def is_validate(self):
        # 验证是否是有效的区块,这里只验证hash的pow是否合法
        start_bytes = b'\x00' * self.bits
        # 计算pow
        if not self.hash().startswith(start_bytes) :
            # log.debug(f'当前区块POW验证失败.应该为：{Block.DEFAULT_BITS},实际:{self.hash().hex()}')
            return False
        return True

    def __str__(self):
        return f"hash:{self.hash().hex()}, prev:{self.prev_hash.hex()},bits:{self.bits},nonce:{self.nonce},time:{datetime.datetime.fromtimestamp(self.timestamp)},height:{self.height}"

class BlockChain:
    blocks:List[Block]
    def __init__(self):
        self.blocks = []
        # 增加创世区块
        self._init_genesis_block()
    def check_chian(self):
        """
            检查整个区块链条否有效
        :return:
        """
        for index, block in enumerate(self.blocks):
            if index == 0 :
                if block.prev_hash != b'\x00' *32:
                    return False
            else: #非创世块
                prev_block = self.blocks[index - 1]
                if block.prev_hash != prev_block.hash() :
                    return False
                if block.bits != prev_block.bits:
                    return False
                if not block.is_validate():
                    return False
        return True
    def _init_genesis_block(self):
        """
            创建一一个创世区块
        :return:
        """
        if not self.blocks:
            genesis_block = Block(b"\x00"*32,bits= Block.DEFAULT_BITS,timestamp=int(time.time()),height=1,nonce=0)
            # 这里只是为了测试
            while not genesis_block.is_validate():
                genesis_block.nonce += 1
            if not self.add_block(genesis_block):
                raise Exception('创始区块创建失败')

    def block_len(self):
        return len(self.blocks)

    def get_best_tip(self):
        if not self.blocks:
            return None
        # 返回最后一个元素
        return self.blocks[-1]
    # 区块增加
    def add_block(self,block:Block):
        # 区块增加，这里简化重组。只要新区块的prev_hash和当前主链tip hash不一致就不能增加成功
        # 在网络层，如果其它网络节点通知的新区块和本地不一致时，先判断高度，你高度低直接忽略。
        # 如果高度比当前的节点更高，那从相关节获取完整的blockchian.这里只是测试p2p挖矿流程，真实的话是不行的。
        if self.block_len() == 0:
            if block.prev_hash != b'\x00' *32:
                log.debug('add block fail,block#0 prev hash must be empty ')
                return False
        else:
            prev_block =  self.blocks[self.block_len() - 1]
            if prev_block.hash() != block.prev_hash:
                log.debug('add block fail,new block prev_hash dont match prev block hash. ')
                return False
            if prev_block.bits != block.bits:
                log.debug(f'add block fail,new block bits dont match prev block bits.best tip bits:{prev_block.bits} ')
                return False
                return False
        # block height不需要验证，只要保证new_block.prevhash 和 best_tip.hash一致就行了。
        # if block.height -1 !=len(self.blocks):
        #     log.debug(f'new block height not match,need block height:{len(self.blocks) + 1}')
        #     return False
        if block.is_validate():
            log.debug(f'new block add success')
            self.blocks.append(block)
            return True
        else:
            log.debug('block add fail,block invali')
            return False
    def reset_chian(self):
        self.blocks = []
        self._init_genesis_block()
    def serialize(self):
        # 序列化 高度在真正的项目是不需要序列化的，因为有hash和位置就能算出高度了。
        bin_data = b''
        for item in self.blocks:
            bin_data += item.serialize()
        return bin_data

    @classmethod
    def deserialize(cls,byte_datas:bytes):
        io_bytes = io.BytesIO(byte_datas)
        bin_data = io_bytes.read(Block.BLOCK_BIN_LEN)
        block_chian = cls()
        while bin_data:
            block = Block.deserialize(bin_data)
            if not block_chian.add_block(block):
                # 只要一节点没办法添加到元素则返回
                return None
            bin_data = io_bytes.read(Block.BLOCK_BIN_LEN)
        return block_chian

    def to_b64(self):
        return base64.b64encode(self.serialize()).decode('utf8')

    @classmethod
    def from_b64(cls,block_b64):
        return Block.deserialize(base64.b64decode(block_b64))

    def hash(self):
        # 计算区块hash
        return hashlib.sha256(self.serialize()).digest()

import threading
import asyncio

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
async def  input_task(minner:Minner):
    while True:
        # 异步等等
        cmd = await asyncio.to_thread(input, '>')
        if cmd == 'restart':
            log.debug('restart ming while empty chian blocks...')
            minner.chian.reset_chian()
            await minner.restart()
        elif cmd == 'add':
            # 增加一个假的 fake
            current_time = int(time.time())
            # 这是假的block
            best_tip = minner.chian.get_best_tip()
            fake_block = Block(b'\x11'*32,nonce=0,bits=best_tip.bits,timestamp=int(time.time()),height=minner.chian.block_len())
            # 这里只是测试
            minner.chian.blocks.append(fake_block)
            log.debug(f'add fake block.restart mining...')
            await minner.restart()
        elif cmd == "status":
            log.debug(f'block:{"-->".join( [str(block) for block in minner.chian.blocks] )}')
            log.debug(minner.chian.to_b64())
            log.debug(f'chian status,len:{minner.chian.block_len()},isvalid:{minner.chian.check_chian()}')
        else:
            log.debug(f'invalid cmd:{cmd}')
async def run_main():
    stop_mining_event = threading.Event()
    chian = BlockChain()

    minner = Minner(block_chain=chian,stop_event=stop_mining_event)

    await asyncio.gather(minner.start(),input_task(minner))
if __name__ == "__main__":
    setup_logging()
    asyncio.run(run_main())