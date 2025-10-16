import socket
import threading
import sys


from protocol import protocol

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 12345
client_socket : socket.socket = None

def client_recvie_message():
    if not client_socket:
        print('客户端未连接')
        return

def main_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((SERVER_HOST,SERVER_PORT))


    client_socket.send(protocol.create_message('reg',{'uesername':'alex'}))

    client_socket.send('我是客户端'.encode('utf8'))
    sermsg = client_socket.recv(1024)
    sermsg ,remaing = protocol.deserialize_stream(client_socket,sermsg)
    print(f'收到服务端信息:{sermsg}')
if __name__ == "__main__":
    main_client()

