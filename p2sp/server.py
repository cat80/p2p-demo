import socket
import threading
import datetime

from protocol import protocol
HOST = "127.0.0.1"
PORT = 12345
clients = {}
client_name_dict = {}
peername_username_dict ={}
client_lock = threading.Lock()
def safe_print(msg):
    print(f'[{datetime.datetime.now()}]-{msg}')
broadcast_list = []
def server_console():
    """
        服务器控制台
    :return:
    """
    print('-----[欢迎使用服务端控制台]----')
    while True:
        txt = input("当前可用命令(broadcast,block,send,userlist)")
        print(f'执行命名:{txt},广播列表：{len(broadcast_list)}')
        for conn in broadcast_list:
            try:
                conn.sendall(protocol.create_payload(txt))
            except Exception as e :
                print(f'出错的:conn')
                print(e)


def broadcast_message(msg):
    """
        广播消息，即批量发送消息
    :param msg:
    :return:
    """
    fail_user_list = []
    with client_lock:
        try:
            for key,conn in client_name_dict.items():
                # 发送消息
                conn.sendall(protocol.create_normal_message(msg))
        except Exception as ex:
            safe_print(f'给{key}发送消息失败,失败原因:{ex}')
            fail_user_list.append(key)
    # 清空用户列表
    for fail_user in fail_user_list:
        remove_username_from_dict(fail_user)

def handler_message(conn:socket.socket,message:dict):
    # 网络协议处理成功后，该方法处理具体协议
    # 目前支付的协议有reg,send,quit,broadcast
    safe_print(f'\n处理消息:{message}\n')
    msg_type = message['type']
    payload = message.get('payload')
    if msg_type =='reg':
        if not message['payload'].get('username'):
            send_msg_to_conn(conn,protocol.create_normal_message(f'请输入有效的注册名称'))
        else:
            username =  message['payload'].get('username').strip()
            reg_result ,errmsg= add_conn_to_dict(conn,username)
            if reg_result:
                send_msg_to_conn(conn, protocol.create_normal_message(f'注册成功,{message}'))
                broadcast_message(f'欢迎[{username}]加入聊天室')
            else:
                send_msg_to_conn(conn, protocol.create_normal_message(f'注册失败,失败原因:{errmsg}'))
    elif msg_type =='send':

        username = payload['username']
        message = payload['message']
        if username not in client_name_dict:
            send_msg_to_conn(conn,protocol.create_normal_message(f'用户{username}不存在或已经下线'))
        else:
            send_msg_by_usename(username,protocol.create_normal_message(message))
    elif msg_type == 'broadcast':
        broadcast_message(payload.get('message'))
    elif msg_type == 'userlist':
        userlist = get_current_user_list()
        send_msg_to_conn(conn, protocol.create_payload(f'ret_userlist',{'userlist':userlist}))
    else:
        send_msg_to_conn(conn, protocol.create_normal_message(f'消息{msg_type}暂时不支付'))
def send_msg_to_conn(conn:socket.socket,bytes_data):
    try:
        # 还是需要建构一个对象
        conn.sendall(bytes_data)
    except Exception as e :
        safe_print(f'发送信息给客户端失败:{conn.getpeername()},移除连接')
        remove_conn_by_peername(conn.getpeername())

def send_msg_by_usename(username,bytes_data):
    if username in client_name_dict:
        send_msg_to_conn(client_name_dict[username],bytes_data)

def add_conn_to_dict(conn:socket.socket,username):
    if username in client_name_dict:
        return False,f'{username},该用户已经注册请换个名吧'

    with client_lock:
        # clients[conn.getpeername()] = conn 只广播特定的
        client_name_dict[username] = conn
        peername_username_dict[conn.getpeername()] = username
    return True,None
    pass

def get_current_user_list():
    """
        获取所有的用户列表
    :return:
    """
    return list(client_name_dict.keys())
def remove_conn_by_peername(peername):
    """
        把连接从列表中移除
    :param conn:
    :return:
    """
    with client_lock:
        if peername in peername_username_dict:
            username = peername_username_dict[peername]
            if username in client_name_dict:
                client_name_dict[username].close()
                del client_name_dict[username]
            del peername_username_dict[peername]

def remove_username_from_dict(username):
    """
        把连接从列表中移除
    :param conn:
    :return:
    """
    if username in client_name_dict:
        conn = client_name_dict[username]
        conn.close()
        with client_lock:
            del client_name_dict[username]
            peername = conn.getpeername()
            if peername in peername_username_dict:
                del peername_username_dict[peername]


def handler_client(conn:socket.socket,addr):
    safe_print(f'client conn success ,client addr:{addr}')
    remaining_data = b''
    try:
        while True:
            # clientmsg = conn.recv(1024)
            clientmsg, remaining_data = protocol.deserialize_stream(conn.makefile('rb'), remaining_data)
            handler_message(conn, message=clientmsg)
    except Exception as e :
        print(e)
    finally:
        remove_conn_by_peername(conn.getpeername())
        print(f'客户端：{conn.getpeername()}退出')


def main_server():
    server_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    # server_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    try:
        server_socket.bind((HOST,PORT))
        server_socket.listen()
        print(f'[服务端监听成功]host:{HOST},port:{PORT}')
        console_thread = threading.Thread(target=server_console, daemon=True)
        console_thread.start()
        while True:
            conn,addr = server_socket.accept()
            client_thread = threading.Thread(target=handler_client, args=(conn,addr))
            client_thread.start()

    except Exception as ex:
        print(ex)

if __name__ == "__main__":
    main_server()