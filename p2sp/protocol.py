import struct
import io
import json
from operator import index

MAGIC_HEADER = b'\xab\xcd\xef\x88'
# 定义进制的头 MAGIC +PAYLOADLEN+CHECKSUM+PAYLOAD
# 头部有14个 len(MAGI4C_HEADER)  + 4 + 4
HEADER_FORMAT = '<4s4sI'
HEADER_LEN = struct.calcsize(HEADER_FORMAT)

print(HEADER_LEN)
class protocol():

    @staticmethod
    def serialize_message(msgtype,payload=None):
        data = {
            "msg":msgtype,
            "payload": payload or {}
        }
        payload_bytes = json.dumps(data).encode('utf8')
        message_header = struct.pack(HEADER_FORMAT,MAGIC_HEADER,b'\x00\x00\x00\x00',len(payload_bytes))
        return message_header+payload_bytes

    @staticmethod
    def deserialize_stream(io_stream:io.BytesIO,buffer=b''):
        while True:
            idx = buffer.find(MAGIC_HEADER)
            if idx != -1:
                buffer = buffer[idx:]
            if len(buffer) > HEADER_LEN:
                break
            chuck = io_stream.read(2048)
            if not chuck:
                raise  Exception('获取数据失败')
            buffer += chuck
        _,check_sum,payload_len = struct.unpack(HEADER_FORMAT,buffer[:HEADER_LEN])
        buffer = buffer[HEADER_LEN:]
        while len(buffer) < payload_len:
            chuck = io_stream.read(payload_len-len(buffer))
            if not chuck:
                raise Exception('连接失败未获取到数据')
            buffer += chuck
        payload =  (buffer[:payload_len]).decode('utf8')
        remaing_data = buffer[payload_len:]
        return json.loads(payload),remaing_data
    @staticmethod
    def create_ping():
        return protocol.serialize_message('ping')

    @staticmethod
    def create_pong():
        return protocol.serialize_message('ping')

    @staticmethod
    def create_message(msgtype,payload=None):
        return protocol.serialize_message(msgtype,payload)