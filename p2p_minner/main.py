
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
    async def handler_msg_notify_new_node(self,payload):
        #处理通知新用户
        log.debug(f'开始处理消息notify_new_node')
        try:
            remote_peer_host = payload.get('ip')
            remote_peer_ip = payload.get('port')
            peer_node_id = payload.get('node_id')
            if not remote_peer_ip or not remote_peer_host or not peer_node_id:
                log.debug('节点信息不完整')
            # 这里应该去连接，因为有可能原来的节点下线。
            if peer_node_id in self.node.peers:
                log.debug(f'peer:{payload} 已经在连接池中不再尝试连接')
                return
            log.debug(f'开始连接新节点')
            remote_peer = await self.node.outgoing_connection(remote_peer_host,remote_peer_ip)
            if remote_peer:
                log.debug(f'remote peer:{remote_peer}')
                # 握手成功广播消息
                log.debug(f'新节点连接成功,广播给自己的邻近节点')
                await  self.node.broadcast("notify_new_node",payload,remote_peer)
            else:
                log.debug(f'新节点连接失败:{payload}')

        except Exception as e:
            log.debug('节点处理失败',exc_info=True)

    async def handler_msg_ping(self, payload):
        try:
            self.writer.write(Protocol.serialize_message("pong",{}))
            await self.writer.drain()
        except Exception as e:
            log.debug("节点keepalive回复失败")
    async def handler_msg_unkown(self,payload):
        log.debug(f'未实现的消息处理，payload:{payload}')
    async def on_recv_message_loop(self):
        log.debug(f'开始循环处理接收节点{self.node_id}消息')
        buffer = b''
        try:
            while True:
                message,buffer = await Protocol.deserialize_stream(self.reader, buffer)
                # 接收到了消息
                if message is None:
                    log.debug(f'节点通信失败:{self.node_id},{self.connect_info}')
                    break
                log.debug(f"接收到{self.node_id}消息:{message}")
                # 这里处理节点消息，现在都写在一起
                msg_type = message.get("type")
                invoke_handler = getattr(self,f"handler_msg_{msg_type}",self.handler_msg_unkown)
                await invoke_handler(message.get('payload'))
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
                await self.writer.wait_closed()
            except Exception as e:
                log.debug(f"节点关闭失败:{self.node_id}",exc_info=True)
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
        # keep alive
        asyncio.create_task(self.keep_alive())
        log.debug(f'本地服务启动成功，监听端口：{port}')
        async with self.server:
            await self.server.serve_forever()
    async def keep_alive(self):
        while True:
            try:
                await asyncio.sleep(90)
                #
                log.debug('开始广播keep-alive')
                await self.broadcast("ping",{})
                log.debug('广播keep-alive结束')
            except Exception as e :
                log.debug("keepalive 广播失败",exc_info=True)

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
            return False
        try:
            log.debug(f'开始连接节点,{host}:{port}')
            reader ,writer =await asyncio.open_connection(host,port)
            #连接成功
            peer_info = writer.get_extra_info('peername')
            log.debug(f'node {peer_info} 连接成功.')
            return await self.start_node_handshake(reader,writer,1)

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
            log.info(f'开始处理握手，remote peer:{writer.get_extra_info("peername")},是否主动连接:{is_initiative}')
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
                    raise Exception(f"主动连接时,本地id {self.node_id} 必须小于远程节点id {remote_node_id}")
                elif not is_initiative and self.node_id < remote_node_id:
                    raise Exception(f"被动(accept)连接时,本地id{self.node_id} 必须大于remote节点{remote_node_id} ")
                else:
                    log.debug('使用新连接代替旧的node连接')
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
            return peer
        except Exception as e:
            log.exception('握手失败') #连接
            if not writer.is_closing():
                writer.close()
                await writer.wait_closed() # 关闭连接
async def run_input_task(node:P2PNode):
    while True:
        try:
            input_txt = await  asyncio.to_thread(input,">")

            cmd = input_txt.split(' ')[0]
            if cmd == "bc":
                msg =  input_txt.split(' ')[-1]
                log.debug(f"广播{msg}消息")
                await node.broadcast("ping",{"msg":msg})
            elif cmd == "stat":
                # 显示当前节点信息
                for item in node.peers.values():
                    log.debug(item.connect_info)
                log.debug(f"维护节点数：{len(node.peers)}")
            else:
                log.debug(f'不支持的命令:{cmd}')
        except (Exception):
            log.exception("处理出错")
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
    asyncio.create_task(run_input_task(node))
    await node.start(host,listen_port)

if __name__ == "__main__":
    asyncio.run(run_main())