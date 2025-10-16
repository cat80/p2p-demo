import socket
import threading
import sys
import logging
import datetime
#
# from prompt_toolkit import PromptSession
# from prompt_toolkit.shortcuts import print_formatted_text


from protocol import protocol

def safe_print(msg):
    print(f'[{datetime.datetime.now()}]-{msg}')

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 12345
client_socket : socket.socket = None
is_register = False
def client_recvie_message(conn:socket.socket):

    safe_print(f'客户端开始接收消息')
    remaining_data = b''
    while True:
        # servermsg = conn.recv(1024)
        servermsg ,remaining_data = protocol.deserialize_stream(conn.makefile('rb'),remaining_data)
        safe_print(f'收到服务端信息:{servermsg}')

def print_man_info(msg:str):
    msg = msg.strip().lower()
    if msg == '/help':
        print(f"""
当前可用命令:
    reg [username] - 注册
    send [username] [message] - 给单个用户发送消息
    broadcast [message] - 群发消息
    userlist - 当有在线用户列表
    /help - 查看命令帮助
    /ver - 查看软件版本
""")
    elif msg =='/ver':
        print(f'当前客户端版本:0.0.1 © cat80 20025')
    else:
        print(f'未知的帮助命令')


def client_console(conn:socket.socket):
    while True:
        msg = input('请输入命令/help查看所有命令：')
        msg= msg.strip()
        if msg.startswith('/'):
            print_man_info(msg)
            continue
        # 这里处理信息非常多
        cmd_arr =  msg.split(' ')
        cmd = cmd_arr[0].lower()
        if cmd == 'reg':
            if len(cmd_arr) ==1:
                print('请输入注册用户名...')
                continue
            conn.sendall(protocol.create_reg_message(cmd_arr[1]))
        elif cmd == 'send':
            if len(cmd_arr) <3:
                print('请输入用户名和消息...')
                continue
            conn.sendall(protocol.create_signal_message(cmd_arr[1].strip(),cmd_arr[2]))
        elif cmd == 'broadcast':
            if len(cmd_arr) ==1:
                print('请输入要广播的内容...')
                continue
            safe_print(f'客户端发送消息:{msg}')
            conn.send(protocol.create_broadcast_message(cmd_arr[1]))
        else:
            print(f'暂时不支持的命令:{cmd}')
    pass
def main_client():

    while True:
        print(f'客户端启动成功，尝试连接服务器({SERVER_HOST}:{SERVER_PORT})')
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((SERVER_HOST,SERVER_PORT))
            # client_socket.send(protocol.create_message('reg',{'uesername':'alex'}))
            # client_socket.send('我是客户端'.encode('utf8'))
            recv_thread = threading.Thread(target=client_recvie_message,args=(client_socket,))
            recv_thread.start()
            # 控制台处理主线程
            client_console(client_socket)
            recv_thread.join()
        except Exception  as e:
            e.with_traceback()
            print(f'服务连接连接失败，失败原因：{e}')
        finally:
            # 释放资源
            client_socket.close()
            input_txt = input('重新尝试连接输入Y，任意建退出')
            if input_txt.strip().lower() =='y':
                break



if __name__ == "__main__":
    main_client()

