import struct
import io
import json
from operator import index

MAGIC_HEADER = b'\xab\xcd\xef\x88'
# 定义进制的头 MAGIC +PAYLOADLEN+CHECKSUM+PAYLOAD
# 头部有14个 len(MAGI4C_HEADER)  + 4 + 4
HEADER_FORMAT = '<4s4sI'
HEADER_LEN = struct.calcsize(HEADER_FORMAT)

class protocol():

    @staticmethod
    def serialize_message(msgtype,payload=None):
        data = {
            "type":msgtype,
            "payload": payload or {}
        }
        payload_bytes = json.dumps(data).encode('utf8')
        message_header = struct.pack(HEADER_FORMAT,MAGIC_HEADER,b'\x00\x00\x00\x00',len(payload_bytes))
        return message_header+payload_bytes

    @staticmethod
    def deserialize_stream(io_stream:io.BytesIO,buffer=b''):

        # 这里反序列化的核心逻辑。
        # 这里有大坑,当socket通过makeifle("rb")转换为bufferreader后，使用read(N)如果获取不到预期的时候会阻塞。使用read1会达到socket.recv一样的方法。
        while True:
            idx = buffer.find(MAGIC_HEADER)
            if idx != -1:
                buffer = buffer[idx:]
            if len(buffer) > HEADER_LEN:
                break
            chuck = io_stream.read1(1024)
            # print(f'buffer len:{len(buffer)}')
            if not chuck:
                raise  Exception('获取数据失败')
            buffer += chuck
        _,check_sum,payload_len = struct.unpack(HEADER_FORMAT,buffer[:HEADER_LEN])
        buffer = buffer[HEADER_LEN:]
        while len(buffer) < payload_len:
            chuck = io_stream.read1(payload_len-len(buffer))
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
        return protocol.serialize_message('pong')

    @staticmethod
    def create_payload(msgtype, payload=None):
        return protocol.serialize_message(msgtype,payload)

    @staticmethod
    def create_normal_message(message):
        """
            这里创建一个普通的信息，一般直接显示即可
        :param message:
        :return:
        """
        return protocol.serialize_message('normalmsg',{'message':message})

    @staticmethod
    def create_signal_message(username,message):
        """
            创建一个单发的信息
        :param username:
        :param message:
        :return:
        """
        return protocol.serialize_message('send', {"touser":username,'message': message})

    @staticmethod
    def create_broadcast_message( message):
        """
            创建一个广播的信息
        :param username:
        :param message:
        :return:
        """
        return protocol.serialize_message('broadcast', { 'message': message})

    @staticmethod
    def create_reg_message(username):
        """
            创建一个广播的信息
        :param username:
        :param message:
        :return:
        """
        return protocol.serialize_message('reg', {'username': username})