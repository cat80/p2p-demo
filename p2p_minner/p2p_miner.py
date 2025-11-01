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

for i in range(1,50000):

    index_hash = hashlib.sha256(i.to_bytes(length=4,byteorder='little')).digest()

    if index_hash[0:2] == b'\x00\x00':
        print(i,index_hash.hex())
# print(b'\x00\x00\x00\x00\\x00\xef'>b'\x00\x00\x00\x00\xaf')

