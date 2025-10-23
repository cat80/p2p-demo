import datetime
import json
import socket
import threading
import time
from py_udp import PROMPT,controlled_print

SOCKET_MAX_BUFFER = 4096

class UdpServer():
    server_socket :socket.socket
    clients= set()

    def __init__(self,bind_port,is_debug=True):

        self.bind_port = bind_port
        self.is_debug = True

    def run(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind(('127.0.0.1', self.bind_port))

        controlled_print(f'服务启动成功，已经成功绑定到端口:{self.bind_port}')
        self.server_socket = server_socket
        recv_thread = threading.Thread(target=self.recv_handler, daemon=True)
        input_thread = threading.Thread(target=self.input_handler, daemon=True)

        recv_thread.start()
        input_thread.start()

        try:
            while True:
                time.sleep(1)
        except Exception as e:
            controlled_print(e,self.is_debug)
        finally:
            controlled_print('程序正在关闭退出....')
            time.sleep(1)
            self.server_socket.close()
            controlled_print('程序成功退出....')

    def send_data_to_client(self,data,addr):
        if isinstance(data,dict) and 'msg' in data:
            if not data['msg'].endswith(')'):
                data['msg'] = f'{data["msg"]}({datetime.datetime.now().strftime("%M:%H")})'
        controlled_print(f'send to:{addr},data:{data}',self.is_debug)
        self.server_socket.sendto(json.dumps(data).encode('utf8'),addr)
    def send_message_to_client(self,msg,addr,msg_type="msg"):
        if not msg_type :
            msg_type = 'msg'
        data  = {
            'type':msg_type,
            'msg':msg
        }
        self.send_data_to_client(data,addr)
    def get_curent_time_HM(self):
        return datetime.datetime.now().strftime('(%H:%M)')
    def handler_send(self,from_addr,payload):
         #处理消息发送
        touser_addr = tuple(  payload.get('to_user'))
        msg = payload.get('msg')
        if touser_addr not in self.clients:
            self.send_data_to_client(f'[系统通知]消息发送失败,{touser_addr}不存在，请使用userlist查看在线用户列表',from_addr)
            return
        from_addr_msg = f'我悄悄对{touser_addr}说:{msg}'
        to_addr_msg=  f'{from_addr}悄悄对我说:{msg}'
        self.send_message_to_client(from_addr_msg,from_addr)
        self.send_message_to_client(to_addr_msg,touser_addr)
    def handler_bc(self,from_addr,payload):
        # 广播消息
        data = {
            'type':'msg',
            'msg': f"{from_addr}:"+payload.get('msg')
        }
        for item in self.clients:
            self.send_data_to_client(data,item)
    def handler_userlist(self,from_addr,payload):
        msg = "\n".join([f"{item}" for item in  self.clients])
        self.send_message_to_client(f'共{len(self.clients)}在线:{msg}',from_addr)

    def handler_ping(self,from_addr,payload):
        self.send_message_to_client('',from_addr,'pong')
    def handler_unknown_cmd(self,from_addr,payload):
        self.send_message_to_client('[系统通知]:不支持的消息类型', from_addr,)
    def recv_handler(self):
        controlled_print('开始接收客户端数据...')
        while True:
            data,addr  = self.server_socket.recvfrom(SOCKET_MAX_BUFFER)
            self.clients.add(addr) # 加入到列表
            data=  json.loads(data.decode("utf8"))
            controlled_print(f'收到:{addr},数据:{data}')
            msg_type = data.get('type')
            handler_method = getattr(self,f"handler_{msg_type}",self.handler_unknown_cmd)
            handler_method(addr,data)
            # self.send_message_to_client('',addr,'pong')
    def input_handler(self):
        while True:
            cmd = input(PROMPT)
            cmd_arr = cmd.strip().split(' ')
            cmd_type = cmd_arr[0]
            if cmd_type == 'bc':
                if len(cmd_arr) <2:
                    # 直接等等
                    continue
                frined_msg = f'[系统通知]:{cmd_arr[1]}{self.get_curent_time_HM()}'
                for item in self.clients:
                    # 系统通知广播，这里可能会阻塞
                    self.send_message_to_client(msg=frined_msg,addr=item,msg_type='msg')

if __name__ =="__main__":
    bind_port = 24567
    is_debug = False
    server = UdpServer(bind_port,is_debug)
    server.run()