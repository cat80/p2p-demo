
"""
    程序运行的主方法和入口
"""
import asyncio
import logging
import sys
from protocol import Protocol

from config import setup_logging

setup_logging()
log = logging.getLogger(__name__)

class Peer:
    def __init__(self,reader,writer,node_id,node):
        self.reader = reader
        self.writer = writer
        self.node_id = node_id
        self.node = node
        self.connect_info = None # 当前的连接信息
        self.recv_message_loop_task = asyncio.create_task(self.on_recv_message_loop())
    async def send_message(self,msgtype,payload=None):
        # 给某个节点发送消息
        try:
            log.debug(f'给节点发送消息:{msgtype},{payload}')
            msg_bytes = Protocol.serialize_message(msgtype=msgtype,payload=payload)
            self.writer.write(msg_bytes)
            await self.writer.drain()
        except Exception as e :
            log.exception(f"消息发送失败:{self.node_id}")
            await self.node.remove_node(self)
    async def on_recv_message_loop(self):
        log.debug(f'开始循环处理接收节点{self.node_id}消息')
        buffer = b''
        try:
            while True:
                message,buffer = await Protocol.deserialize_stream(self.reader, buffer)
                # 接收到了消息
                if message is None:
                    log.debug(f'连接节点失败:{self.node_id},{self.connect_info}')
                    break
                log.debug(f"接收到{self.node_id}消息:{message}")
        except Exception as e:
            log.exception(f"节点{self.node_id}消息接收失败")
        finally:
            await self.node.remove_node(self)


    async def close(self):
        if not self.recv_message_loop_task.done():
            self.recv_message_loop_task.cancel()
        if not self.writer.is_closing():
            try:
                self.writer.close()
                await self.writer.waite_closed()
            except Exception as e:
                log.exception(f"节点连接关闭失败:{self.node_id}")
    def set_connect_info(self,connect_info):
        self.connect_info = connect_info

class P2PNode:
    def __init__(self):
        self.server= None
        # 在本机测试node id 就是监听端口
        self.node_id = 0
        #所有的节点
        self.peers = {}
    async def start(self,host,port):
        """
            运行主程序
        :return:
        """
        self.server = await asyncio.start_server(
            self.handler_coming_client,host,port
        )

        log.debug(f'本地服务启动成功，监听端口：{port}')
        async with self.server:
            await self.server.serve_forever()

    async def handler_coming_client(self,reader,writer):
        """
            处理接入连接
        :param reader:
        :param writer:
        :return:
        """
        log.debug(f'accept 节点:{writer.get_extra_info("peername")}')
        await self.start_node_handshake(reader,writer,0)
    async def outgoing_connection(self,host,port):
        """
            主动连接其它的节点
        """
        if port == self.node_id:
            log.debug(f'连接的为本机监听端口，终止连接.port:{port}')
            return
        try:
            reader ,writer =await asyncio.open_connection(host,port)
            #连接成功
            peer_info = writer.get_extra_info('peername')
            log.debug(f'node {peer_info} 连接成功.')
            await self.start_node_handshake(reader,writer,1)
        except Exception as e:
            log.exception("连接出错")
            log.debug(f'连接节点[{host}:{port}]失败')
    async def broadcast(self,message_type,payload, exclude=None):
        #给所有用户广播消息
        tasks = [
            peer.send_message(message_type,payload)
            for peer in self.peers.values() if not exclude or peer.node_id != exclude.node_id
        ]
        await asyncio.gather(*tasks)

    async def remove_node(self,peer:Peer):
        ready_close_node = self.peers.pop(peer.node_id,None)
        if ready_close_node:
            await peer.close()
    async  def start_node_handshake(self,reader,writer,is_initiative):
        # 处理握手，交易通信协议处理重复连接问题。
        # is_initiative 是否为主动连接，为false则为accept
        try:
            log.info(f'开始处理握手，remote peer:{writer.get_extra_info("peerinfo")},是否主动连接:{is_initiative}')
            frist_message = {
                "type":"hello",
                'node_id':self.node_id,
                "listen_port":self.node_id
            }
            # 主动发送消息
            writer.write(Protocol.serialize_message("hello",frist_message))
            await writer.drain()

            remote_message,_ = await Protocol.deserialize_stream(reader,b'')
            # 从远程节点收到协议数据
            log.debug(f'成功从节点收到数据...{remote_message}')
            #连接后收到的第一个消息应为hello
            if remote_message.get('type') != 'hello':
                raise Exception('第一个消息应该为hello')
            remote_payload = remote_message.get('payload') # 获payload
            remote_node_id = remote_payload.get("node_id")
            remote_listen_port = remote_payload.get("listen_port")
            if remote_node_id != remote_listen_port:
                raise Exception('节点id必须和监听端口一致')
            if remote_node_id in self.peers:
                # 处理重复连接问题。这个对等网络很常见
                # 规定只能id小的连id大的的。
                if is_initiative and self.node_id > remote_node_id:
                    raise Exception("主动连接时,本地node id 必须大于当前节点id,")
                elif not is_initiative and self.node_id < remote_node_id:
                    raise Exception("被动(accept)连接时,remote_id 必须小与当前节点id ")
                else:
                    # 当现在存在的连接关闭掉，使用最新的连接
                    await self.peers[remote_node_id].close()
            log.debug('连接成功...')
            peer = Peer(reader,writer,remote_node_id,self)
            connect_info = {
                'ip':writer.get_extra_info('peername')[0],
                'port':remote_listen_port,
                'node_id':remote_node_id
            }
            peer.set_connect_info(connect_info)
            self.peers[remote_node_id] = peer
            # 开始通知其它节点有新的节点到了
            await self.broadcast("notify_new_node", peer.connect_info,  exclude=peer)
        except Exception as e:
            log.exception('层手失败') #连接
            if not writer.is_closing():
                await writer.close() # 关闭连接
async  def run_main():
    # 运行主方法
    args = sys.argv
    host= '127.0.0.1'
    listen_port = 17890
    default_peers = [["127.0.0.1",17890]]
    if len(args) > 1:
        listen_port = int(args[-1])
    node = P2PNode()
    node.node_id = listen_port
    for peer_addr in default_peers:
        log.debug(f'尝试连接到节点:{peer_addr}')
        asyncio.create_task(node.outgoing_connection(peer_addr[0],peer_addr[1]))

    await node.start(host,listen_port)

if __name__ == "__main__":
    asyncio.run(run_main())