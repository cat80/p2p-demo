import socket
import threading
import datetime
#
# from prompt_toolkit import PromptSession
# from prompt_toolkit.shortcuts import print_formatted_text

stop_event = threading.Event()
from protocol import protocol

def safe_print(msg,showdate=False):
    if showdate:
        msg = f'[{datetime.datetime.now()}]-{msg}'
    print(msg)

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 12345
client_socket : socket.socket = None
is_register = False
def client_recvie_message(conn:socket.socket):

    safe_print(f'客户端开始接收消息')
    remaining_data = b''
    while not stop_event.is_set():
        # servermsg = conn.recv(1024)
        servermsg ,remaining_data = protocol.deserialize_stream(conn.makefile('rb'),remaining_data)
        # 直接打印服务输出，暂时不做额外处理
        safe_print(protocol.show_user_msg(servermsg))

def print_man_info(msg:str):
    msg = msg.strip().lower()
    if msg == '/help':
        print(f"""
当前可用命令:
    /reg [username] - 注册
    /send [username] [message] - 给单个用户发送消息
    /broadcast [message] - 群发消息非命令开始也是广播
    /userlist - 当有在线用户列表
    /quit - 退出当前程序
    /help - 查看命令帮助
    /ver - 查看软件版本
""")
    elif msg =='/ver':
        print(f'当前客户端版本:v0.0.1 © 20025')



def client_console(conn:socket.socket):
    while not stop_event.is_set():
        msg = input('')
        msg= msg.strip()
        if msg.startswith('/'):
            print_man_info(msg)
            cmd_arr = msg.split(' ')
            cmd = cmd_arr[0].lower()
            if cmd == '/reg':
                if len(cmd_arr) == 1:
                    print('请输入注册用户名...')
                    continue
                conn.sendall(protocol.create_reg_message(cmd_arr[1]))
            elif cmd == '/send':
                if len(cmd_arr) < 3:
                    print('请输入用户名和消息...')
                    continue
                conn.sendall(protocol.create_user_send_message(cmd_arr[1].strip(), cmd_arr[2]))
            elif cmd == '/broadcast':
                if len(cmd_arr) == 1:
                    print('请输入要广播的内容...')
                    continue
                safe_print(f'客户端发送消息:{msg}')
                conn.send(protocol.create_broadcast_message(cmd_arr[1]))
            elif cmd == '/quit':
                stop_event.set()
            elif cmd == '/userlist':
                conn.send(protocol.create_payload('userlist', {}))
            else:
                print(f'暂时不支持的命令:{cmd}.输入/help查看所有数据')
        else:
            conn.send(protocol.create_broadcast_message(msg))
        # 这里处理信息非常多

    pass
def main_client():

    while not stop_event.is_set():
        safe_print(f'客户端启动成功，尝试连接服务器({SERVER_HOST}:{SERVER_PORT})',showdate=True)
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((SERVER_HOST,SERVER_PORT))
            safe_print(f'服务器连接成功....',showdate=True)
            safe_print(f'使用/help 查看命令.',showdate=True)
            # client_socket.send(protocol.create_message('reg',{'uesername':'alex'}))
            # client_socket.send('我是客户端'.encode('utf8'))
            recv_thread = threading.Thread(target=client_recvie_message,args=(client_socket,))
            recv_thread.start()
            # 控制台处理主线程
            client_console(client_socket)
            recv_thread.join()
        except Exception  as e:
            print(f'服务连接连接失败，失败原因：{e}')
            # stop_event.set()
        finally:
            print('退出程序')
            stop_event.set()
            # 释放资源
            # input('服务器连接出错，按任意建新连接')




if __name__ == "__main__":
    main_client()

