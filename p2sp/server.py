import socket
import threading
from protocol import protocol
HOST = "127.0.0.1"
PORT = 12345
clients = {}
client_lock = threading.Lock()

def server_console():
    """
        服务器控制台
    :return:
    """
    print('-----[欢迎使用服务端控制台]----')
    while True:
        txt = input("当前可用命令(broadcast,block,send,userlist)")
        print(f'执行命名:{txt}')
def handler_client(conn:socket.socket,addr):
    print(f'client conn success ,client addr:{addr}')

    conn.send(protocol.create_ping())
    clientmsg = conn.recv(1024)
    clientmsg,raming = protocol.deserialize_stream(conn.makefile('rb'),clientmsg)
    print(f'client messsage:{clientmsg}')


def main_server():
    server_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)

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