import socket
import threading
import datetime
from protocol import protocol
HOST = "127.0.0.1"
PORT = 12345
clients = {}
current_online_user_dict = {}
peername_username_dict ={}
client_lock = threading.Lock()
RUNNING_SERVER = True
def safe_print(msg,showdatetime = False):
    if showdatetime :
        msg = f'[{datetime.datetime.now()}]-{msg}'
    print(msg)
broadcast_list = []

stop_event = threading.Event() #程序结果结束标记
def print_server_man_info(cmd):
    """
        显示服务端的帮助信息
    :param cmd:
    :return:
    """
    if cmd == "/help":
        helpinfo = """
    当前可用命令：
        /broadcast [message] - 群发消息
        /send [username] message - 单发消息
        /block [username] - 踢用户下线
        /userlist - 查看当前在线列表
        /quit - 退出程序
        /help - 获取帮助
        /version - 查看版本信息
"""
        safe_print(helpinfo)
    elif cmd == '/version':
        safe_print('当前 p2sp 服务端版本 v0.0.1 © 2025')
    else:
        safe_print(f'不支持的命令{cmd},输入/help查看可用命令')



def broadcast_sys_info_handler(msg):
    """
        广播消息，即批量发送消息
    :param msg:
    :return:
    """
    fail_user_list = []
    with client_lock:
        try:
            for key,conn in current_online_user_dict.items():
                # 发送消息
                conn.sendall(protocol.create_sys_notify(msg))
        except Exception as ex:
            safe_print(f'给{key}发送消息失败,失败原因:{ex}')
            fail_user_list.append(key)
    # 清空用户列表
    for fail_user in fail_user_list:
        remove_username_from_dict(fail_user)


def broadcast_bytes(bytes):
    """
        广播消息，指发
    :param msg:
    :return:
    """
    fail_user_list = []
    with client_lock:
        try:
            for key,conn in current_online_user_dict.items():
                # 发送消息
                conn.sendall(bytes)
        except Exception as ex:
            safe_print(f'给{key}发送消息失败,失败原因:{ex}')
            fail_user_list.append(key)
    # 清空用户列表
    for fail_user in fail_user_list:
        remove_username_from_dict(fail_user)

def send_message_to_user_handler(cmd):
    """
        服务端，给单个用户发送信息
    :param cmd:
    :return:
    """
    cmd_arr = cmd.split(' ')
    if len(cmd_arr) <3:
        safe_print(f'{cmd}执行失败，至少三有个参数')
        return
    username,message = cmd_arr[1],' '.join(  cmd_arr[2:])
    if username not in current_online_user_dict:
        safe_print(f'用户{username}不存在，请检查')
        return
    # 服务商直接发系统通知
    send_msg_by_usename(username,protocol.create_sys_notify(message))

def  block_user_handler(cmd):
    cmd_arrs = cmd.split(' ')
    if not len(current_online_user_dict):
        safe_print('当前在线用户列表空')
        return
    if  len(cmd_arrs) <2:
        safe_print(f'命令{cmd}执行失败，需要用户名')
        return
    username = cmd_arrs[1]
    if username not in current_online_user_dict:
        safe_print(f'用户{username}不存在')
        return
    remove_username_from_dict(username)

def user_list_handler():
    if len(current_online_user_dict) == 0:
        safe_print('当前无在线用户，请稍后再试')
        return
    for username,conn in current_online_user_dict.items():
        safe_print(f'{username}-{conn.getpeername()}')

def safe_quit_handler():
    stop_event.set()

def server_console():
    """
        服务器控制台
    :return:
    """

    while not stop_event.is_set():
        user_input = input().strip()
        if user_input.startswith('/'):
            user_input_arr = user_input.strip().split(' ')
            cmd = user_input_arr[0]
            if cmd == '/broadcast':
                broadcast_sys_info_handler(' '.join(user_input_arr[1:]))
                safe_print('消息广播完成')
            elif cmd == '/send':
                send_message_to_user_handler(user_input)
            elif cmd == '/block':
                block_user_handler(user_input)
            elif cmd == '/userlist':
                user_list_handler()
            elif cmd == '/quit':
                safe_quit_handler()
            else:
                print_server_man_info(cmd)
        else:
            broadcast_sys_info_handler(user_input)
            safe_print('消息广播完成',showdatetime=True)

class ClientRequestHandler():
    """"
        这里统一处理客户请求
    """
    conn : socket.socket
    payload :dict
    def __init__(self,conn,client_data):
        self.conn =conn
        self.client_data = client_data
        self.msg_type = client_data['type']
        self.payload = client_data['payload']
        self.conn_username = peername_username_dict.get(conn.getpeername())
    def send_sys_notify_to_conn(self,message):
        send_msg_to_conn(self.conn,protocol.create_sys_notify(message))

    def reg(self):

        reg_username =   self.payload.get('username')
        if not reg_username:
            self.send_sys_notify_to_conn(f'请输入有效的注册名称')
        reg_result, errmsg = add_conn_to_dict(self.conn, reg_username)
        if reg_result:
            self.send_sys_notify_to_conn(f'恭喜你：[{reg_username}]，注册成功!你可以使用所有功能了。')
            broadcast_sys_info_handler(f'欢迎[{reg_username}]加入聊天室')
        else:
            self.send_sys_notify_to_conn(f"注册失败,失败原因:{errmsg}")

    def send(self):
        """
            客户端用户，给某个在线用户发信息
        :return:
        """
        username = self.payload['touser']
        message = self.payload['message']
        if username not in current_online_user_dict:
            self.send_sys_notify_to_conn(f'用户{username}不存在或已经下线')
        else:
            send_msg_by_usename(username, protocol.create_client_user_send_message(self.conn_username, message))

    def broadcast(self):
        """
            客户
        :return:
        """
        # create_user_broadcast_message
        bytes_msg = protocol.create_user_broadcast_message(self.conn_username,self.payload['message'])
        broadcast_bytes(bytes_msg) # 群发信息，广播

    def userlist(self):
        userlist = get_current_user_list()
        if not userlist:
            send_message = '当前用户为空'
        else:
            send_message=f"{'\r\n'.join(userlist)}\r\n共{len(userlist)}位在线用户"
        self.send_sys_notify_to_conn(send_message)

    def quit(self):
        """
            离开
        :return:
        """
        broadcast_sys_info_handler('服务端已经离开')
        self.send_sys_notify_to_conn('quit')
    def handler(self):

        msg_type = self.msg_type
        if not auth_check_handler(self.conn) and msg_type != 'reg':
            self.send_sys_notify_to_conn(f'请先使用/reg 进行注册')
            return
        if msg_type == 'reg':
            self.reg()
        elif  msg_type == 'send':
            self.send()
        elif msg_type == 'broadcast':
            self.broadcast()
        elif msg_type == 'userlist':
            self.userlist()
        elif msg_type == 'quit':
            self.quit()
        else:
            self.send_sys_notify_to_conn(f'系统暂不支持消息命令{msg_type}')


def auth_check_handler(conn:socket.socket):
    """
        鉴权管理，现在简单栓塞peername是否存在
    :param conn:
    :param cmd:
    :return:
    """
    return conn.getpeername() in peername_username_dict


def send_msg_to_conn(conn:socket.socket,bytes_data):
    try:
        # 还是需要建构一个对象
        conn.sendall(bytes_data)
    except Exception as e :
        safe_print(f'发送信息给客户端失败:{conn.getpeername()},移除连接')
        remove_conn_by_peername(conn.getpeername())

def send_msg_by_usename(username,bytes_data):
    if username in current_online_user_dict:
        send_msg_to_conn(current_online_user_dict[username], bytes_data)

def add_conn_to_dict(conn:socket.socket,username):
    if username in current_online_user_dict:
        return False,f'{username},该用户已经注册请换个名吧'

    with client_lock:
        # clients[conn.getpeername()] = conn 只广播特定的
        current_online_user_dict[username] = conn
        peername_username_dict[conn.getpeername()] = username
    return True,None


def get_current_user_list():
    """
        获取所有的用户列表
    :return:
    """
    return list(current_online_user_dict.keys())
def remove_conn_by_peername(peername):
    """
        把连接从列表中移除
    :param conn:
    :return:
    """
    with client_lock:
        if peername in peername_username_dict:
            username = peername_username_dict[peername]
            if username in current_online_user_dict:
                current_online_user_dict[username].close()
                del current_online_user_dict[username]
            del peername_username_dict[peername]

def remove_username_from_dict(username):
    """
        把连接从列表中移除
    :param conn:
    :return:
    """
    if username in current_online_user_dict:
        conn = current_online_user_dict[username]
        conn.close()
        with client_lock:
            del current_online_user_dict[username]
            peername = conn.getpeername()
            if peername in peername_username_dict:
                del peername_username_dict[peername]
        broadcast_sys_info_handler(f'"{username}"被管理员移出聊天群')

def handler_client_conn(conn:socket.socket, addr):
    safe_print(f'client conn success ,client addr:{addr}')
    remaining_data = b''
    try:
        while not stop_event.is_set():
            # clientmsg = conn.recv(1024)
            clientmsg, remaining_data = protocol.deserialize_stream(conn.makefile('rb'), remaining_data)
            # 解析到一个有效消息，给交处理器处理
            safe_print(f'处理客户端:{conn.getpeername()},命令:{clientmsg}',showdatetime=True)
            clientRequestHandler = ClientRequestHandler(conn,clientmsg)
            clientRequestHandler.handler()
            # handler_recv_message(conn, message=clientmsg)
    except Exception as e :
        print(e)
        safe_print(f"出错了,{e}")
    finally:
        safe_print(f'客户端：{conn.getpeername()}退出',showdatetime=True)
        remove_conn_by_peername(conn.getpeername())



def main_server():
    safe_print('-----[欢迎使用服务端控制台]----',showdatetime=True)
    safe_print('使用/help 可以查看所有命令',showdatetime=True)
    server_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    server_socket.settimeout(2)
    # server_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    try:
        server_socket.bind((HOST,PORT))
        server_socket.listen()
        print(f'[服务端监听成功]host:{HOST},port:{PORT}')
        console_thread = threading.Thread(target=server_console, daemon=True)
        console_thread.start()
        while not stop_event.is_set():
            try:
                conn,addr = server_socket.accept()
                client_thread = threading.Thread(target=handler_client_conn, args=(conn, addr))
                client_thread.start()
            except socket.timeout:
                continue
        print('服务端已经停止...')

    except Exception as ex:
        stop_event.set()
        print(ex)


if __name__ == "__main__":
    main_server()