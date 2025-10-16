# -*- coding: utf-8 -*-
"""
Seed Discovery Service for the P2P Network.

This server acts as a bootstrap node (tracker). Its main responsibilities are:
1.  Listen for connections from new P2P nodes.
2.  Register the IP address and listening port of each new node, keeping them in a persistent list.
3.  When a new node connects, send it a list of other already-known nodes.
4.  Handle unregister requests to remove nodes that gracefully shut down.
"""
import asyncio
import json
import logging

# 配置日志记录，方便调试
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 使用集合(set)来存储已知对等节点的地址，格式为 (ip, port)
# 集合可以自动处理重复的地址，确保唯一性
known_peers = set()


async def handle_client(reader, writer):
    """
    当有新的节点连接到种子服务器时，此函数负责处理。
    它现在可以处理 REGISTER 和 UNREGISTER 命令。
    """
    # 获取连接过来的节点的地址信息
    peer_addr = writer.get_extra_info('peername')
    logging.info(f"接收到来自 {peer_addr} 的连接")

    try:
        # 协议规定，消息以换行符结束
        data = await reader.read(1024)
        message = data.decode().strip()

        if message.startswith("REGISTER"):
            parts = message.split()
            if len(parts) == 2 and parts[1].isdigit():
                # 从消息中解析出节点的监听端口
                port = int(parts[1])
                # IP地址直接从连接信息中获取
                ip = peer_addr[0]
                node_address = (ip, port)

                logging.info(f"正在注册节点: {node_address}")

                # 2. 将当前已知的对等节点列表发送给新节点
                # 我们发送一个JSON编码的字符串列表，格式为 "ip:port"
                # 注意：发送给新节点的列表不应包含它自己
                peer_list_to_send = [f"{p[0]}:{p[1]}" for p in known_peers if p != node_address]
                response_data = json.dumps(peer_list_to_send).encode()

                writer.write(response_data + b'\n')
                await writer.drain()
                logging.info(f"已将对等节点列表发送至 {node_address}: {peer_list_to_send}")

                # 3. 将新节点添加到我们的持久化已知节点列表中
                known_peers.add(node_address)
                logging.info(f"当前已知的所有节点: {known_peers}")

            else:
                logging.warning(f"来自 {peer_addr} 的REGISTER消息格式无效: {message}")

        elif message.startswith("UNREGISTER"):
            parts = message.split()
            if len(parts) == 2:
                ip_port_str = parts[1]
                try:
                    ip, port_str = ip_port_str.split(':')
                    port = int(port_str)
                    node_to_unregister = (ip, int(port))
                    if node_to_unregister in known_peers:
                        known_peers.remove(node_to_unregister)
                        logging.info(f"节点 {node_to_unregister} 已成功注销。")
                        logging.info(f"当前已知的所有节点: {known_peers}")
                    else:
                        logging.warning(f"请求注销一个未知的节点: {node_to_unregister}")
                except ValueError:
                    logging.warning(f"来自 {peer_addr} 的UNREGISTER消息格式无效: {message}")
            else:
                logging.warning(f"来自 {peer_addr} 的UNREGISTER消息格式无效: {message}")

        else:
            logging.warning(f"收到来自 {peer_addr} 的非REGISTER/UNREGISTER消息: {message}")

    except asyncio.IncompleteReadError:
        logging.warning(f"客户端 {peer_addr} 在发送完整消息前断开连接")
    except Exception as e:
        logging.error(f"处理 {peer_addr} 时发生错误: {e}")
    finally:
        # 连接是事务性的。关闭连接不代表节点下线。
        # 节点的移除现在通过 UNREGISTER 命令显式处理。
        logging.info(f"正在关闭与 {peer_addr} 的连接")
        writer.close()
        await writer.wait_closed()


async def main():
    """
    主函数，用于启动种子服务器。
    """
    host = '0.0.0.0'  # 监听所有网络接口
    port = 9999  # 定义一个固定的种子服务器端口

    # 使用 asyncio.start_server 创建一个TCP服务器
    server = await asyncio.start_server(
        handle_client, host, port)

    addr = server.sockets[0].getsockname()
    logging.info(f"种子发现服务正在监听: {addr}")

    # 启动服务器并让它永久运行
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("种子服务器正在关闭。")

