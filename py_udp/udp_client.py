import json
import socket
import threading
import time

SERVER_ADDR  = ("127.0.0.1",24567)
SOCKET_MAX_BUFFER = 4096
from py_udp import PROMPT,controlled_print

class UdpClient():

    def __init__(self,server_addr,is_debug=True):
        self.is_debug = is_debug
        self.server_addr = server_addr
        self.is_running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    def send_data_to_server(self, data):
        # 往服务发送数据
        controlled_print(f'send data:{data}',self.is_debug)
        try:
            self.socket.sendto(json.dumps(data).encode('utf8'), self.server_addr)
        except OSError as ex:
            controlled_print(f'send fail:{data}')

    def send_message_server(self, msg, msg_type='normal'):
        payload = {
            'type':msg_type,
            "msg":msg
        }
        self.send_data_to_server(payload)

    def run(self):
        controlled_print(f'客户端启用成功，通信服务器：{self.server_addr}')
        recv_thread = threading.Thread(target=self.recv_handler, daemon=False)
        input_thread = threading.Thread(target=self.input_handler, daemon=False)
        self.send_message_server('',msg_type='ping')
        recv_thread.start()
        input_thread.start()
        self.is_running = True
        try:
            while self.is_running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.is_running = False
        finally:
            controlled_print('程序正在关闭退出....')
            time.sleep(1)
            self.socket.close()
            controlled_print('程序成功退出....')


    def recv_handler(self):
        controlled_print('开始接服务端数据...')
        data, addr= None,None
        while True:
            try:
                data,addr  = self.socket.recvfrom(SOCKET_MAX_BUFFER)
                data = data.decode('utf8')
                data=  json.loads(data)
                if data.get('msg'):
                    controlled_print(data.get('msg'))
                controlled_print(f'收到:{addr},数据:{data}',self.is_debug)
                # print(f'收到:{addr},数据:{data}')
            except Exception as e :
                controlled_print(e,self.is_debug)
                controlled_print(f'处理消息失败:{data},{addr}',self.is_debug)

    def console_handler_send(self,cmd:str):
        # 格式是 send ip:port msg
        cmd_arr = cmd.strip().split(' ')
        if len(cmd_arr) < 3 or ":" not in cmd_arr[1] :
            controlled_print(f'{cmd} 格式错误')
            return
        addr = cmd_arr[1].split(':')
        to_user =(addr[0],int(addr[1]))
        msg = " ".join(cmd_arr[2:]) #还原消息
        data = {
            'type':'send',
            'to_user':to_user,
            'msg':msg
        }
        self.send_data_to_server(data)

    def console_handler_userlist(self, cmd):
        data = {
            'type': 'userlist'
        }
        self.send_data_to_server(data)

    def console_handler_bc(self, cmd:str):
        cmd_arr = cmd.strip().split(' ')
        msg = cmd
        if cmd_arr[0] == 'bc' and len(cmd_arr)>0:
            msg = ' '.join(cmd_arr[1:])
        data = {
            'type': 'bc',
            'msg':msg
        }
        self.send_data_to_server(data)

    def input_handler(self):
        while True:
            cmd = input(PROMPT)
            cmd_arr = cmd.strip().split(' ')
            cmd_type = cmd_arr[0]
            invoke_method = getattr(self,f'console_handler_{cmd_type}',self.console_handler_bc)
            invoke_method(cmd)
if __name__ =="__main__":
    is_debug = False
    server = UdpClient(SERVER_ADDR,is_debug)
    server.run()