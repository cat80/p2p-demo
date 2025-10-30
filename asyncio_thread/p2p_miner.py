"""
    这里模拟pow进行p2p挖矿。包含简单的节点发现，节点管理。
    简化挖矿逻辑，只对区块的难度做验证，没有考虑重组的问题。
"""
import logging
import hashlib
from config import setup_logging
setup_logging()

log = logging.getLogger(__name__)
bits = 4 # 这里的难度代码要运算的次数，即hash前面N的个数.比如4代表前四个字节0x00000000aa才符合要求，要计算255^4才有可能。

def int_to_bytes(i:int):
    # 统一int为8个字节
    return i.to_bytes(length=8,byteorder="little")
class Block:
    prev_hash:bytes
    nonce:int
    bits:int
    block_hash:bytes
    def __init__(self,prev,nonce,bits):
        self.prev_hash = prev
        self.nonce= nonce
        self.bits = bits
        self.block_hash = self.get_hash()

    def get_hash(self):
        return hashlib.sha256(self.prev_hash+int_to_bytes(self.bits)+ int_to_bytes(self.nonce)).digest()

    def is_validate(self):
        # 验证是否是有效的区块
        except_block_hash = self.get_hash()
        if except_block_hash != self.block_hash:
            log.debug(f'当前区块hash无效，应该为：{except_block_hash},实际:{self.block_hash}')
            return False
        start_bytes = b'\x00' * self.bits
        # 计算pow
        if not self.block_hash.startswith(start_bytes) :
            return False
        return True
    def __str__(self):
        return f"hash:{self.block_hash.hex()}, prev:{self.prev_hash.hex()},bits:{self.bits},nonce:{self.nonce}"

class BlockChain:
    blocks:[Block]
    def __init__(self):
        self.blocks = []
    # 区块增加
    def add_block(self,block:Block):
        pass

for i in range(1,50000):

    index_hash = hashlib.sha256(i.to_bytes(length=4,byteorder='little')).digest()

    if index_hash[0:2] == b'\x00\x00':
        print(i,index_hash.hex())
# print(b'\x00\x00\x00\x00\\x00\xef'>b'\x00\x00\x00\x00\xaf')

