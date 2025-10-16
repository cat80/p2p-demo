# -*- coding: utf-8 -*-
"""
P2P Peer Node for the Chat Network.

This program represents a single node in the P2P network. It has several concurrent tasks:
1.  Run a server to listen for incoming connections from other peers.
2.  Connect to the seed server to discover other peers.
3.  Establish connections to the peers it discovers.
4.  Handle user input from the console to send messages.
5.  Listen for and display messages received from connected peers.
"""
import asyncio
import json
import logging
import argparse

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

# 全局字典，用于存储活动的对等节点连接
# 键: "ip:port" 字符串, 值: (asyncio.StreamReader, asyncio.StreamWriter) 元组
peers = {}
# 节点自己的监听地址
my_address = None


async def handle_incoming_peer(reader, writer):
    """
    处理来自另一个对等节点的传入连接。
    """
    peer_addr_tuple = writer.get_extra_info('peername')
    peer_addr_str = f"{peer_addr_tuple[0]}:{peer_addr_tuple[1]}"
    logging.info(f"接受了来自 {peer_addr_str} 的传入连接")

    # 将新的连接存储到peers字典中
    peers[peer_addr_str] = (reader, writer)

    # 为这个新的连接创建一个持续监听消息的任务
    await listen_to_peer(reader, writer)


async def listen_to_peer(reader, writer):
    """
    在一个循环中持续监听来自某个已连接对等节点的消息。
    """
    peer_addr_tuple = writer.get_extra_info('peername')
    # 注意：这个地址是连接地址，不一定是对方的监听地址
    peer_addr_str = f"{peer_addr_tuple[0]}:{peer_addr_tuple[1]}"

    try:
        while True:
            # 使用readline来确保我们能处理以换行符分隔的消息
            data = await reader.readline()
            if not data:
                # 如果接收到空数据，意味着连接已关闭
                break

            message = data.decode().strip()

            # 打印收到的消息，并重新打印输入提示符，以保持界面整洁
            print(f"\n<-- [消息] {message}")
            print(">> 请输入命令 (broadcast, send, peers, quit): ", end="", flush=True)

    except asyncio.IncompleteReadError:
        logging.warning(f"与 {peer_addr_str} 的连接意外断开。")
    except Exception as e:
        logging.error(f"监听 {peer_addr_str} 时出错: {e}")
    finally:
        logging.info(f"与 {peer_addr_str} 的连接已关闭。")
        # 从peers字典中移除断开连接的节点
        if peer_addr_str in peers:
            del peers[peer_addr_str]
        writer.close()


async def connect_to_seed(seed_host, seed_port, my_listen_port):
    """
    连接到种子服务器以获取对等节点列表。
    """
    try:
        logging.info(f"正在连接到种子服务器 {seed_host}:{seed_port}")
        reader, writer = await asyncio.open_connection(seed_host, seed_port)

        # 1. 向种子服务器注册自己
        register_msg = f"REGISTER {my_listen_port}\n"
        writer.write(register_msg.encode())
        await writer.drain()
        logging.info("已向种子服务器发送注册信息。")

        # 2. 接收对等节点列表
        data = await reader.read(4096)
        peer_list_json = data.decode()
        initial_peers = json.loads(peer_list_json)
        logging.info(f"从种子服务器收到对等节点列表: {initial_peers}")

        writer.close()
        await writer.wait_closed()

        return initial_peers

    except ConnectionRefusedError:
        logging.error("无法连接到种子服务器。请确认服务已启动。")
        return []
    except Exception as e:
        logging.error(f"连接种子服务器失败: {e}")
        return []


async def connect_to_peer(host, port):
    """
    与另一个对等节点建立出站连接。
    """
    peer_addr_str = f"{host}:{port}"
    # 防止连接到自己或已经连接的节点
    if peer_addr_str in peers or peer_addr_str == my_address:
        return

    try:
        logging.info(f"尝试连接到对等节点 {peer_addr_str}")
        reader, writer = await asyncio.open_connection(host, port)

        peers[peer_addr_str] = (reader, writer)
        logging.info(f"成功连接到对等节点 {peer_addr_str}")

        # 为这个出站连接创建一个监听任务
        asyncio.create_task(listen_to_peer(reader, writer))

    except ConnectionRefusedError:
        logging.warning(f"对等节点 {peer_addr_str} 拒绝连接。")
    except Exception as e:
        logging.error(f"连接对等节点 {peer_addr_str} 失败: {e}")


async def handle_user_input(args):
    """
    处理来自控制台的用户输入，用于发送消息。
    这是一个核心的异步任务。
    """
    loop = asyncio.get_running_loop()
    while True:
        try:
            # 标准的input()是阻塞函数，会卡住整个asyncio事件循环。
            # 我们使用 loop.run_in_executor 将其放入一个单独的线程中运行，从而避免阻塞。
            message = await loop.run_in_executor(
                None, lambda: input(">> 请输入命令 (broadcast, send, peers, peerlist, renewpeers, quit): ")
            )

            message = message.strip()
            if not message:
                continue

            parts = message.split(maxsplit=2)
            command = parts[0].lower()

            if command == "quit":
                logging.info("正在关闭节点...")
                for _, writer in peers.values():
                    writer.close()
                # 取消所有其他任务并停止事件循环
                for task in asyncio.all_tasks():
                    if task is not asyncio.current_task():
                        task.cancel()
                loop.stop()
                break

            elif command == "broadcast":
                if len(parts) < 2:
                    print("用法: broadcast <你的消息>")
                    continue

                # 构造广播消息，并附上自己的地址
                broadcast_msg = f"[{my_address}]: {parts[1]}"
                logging.info(f"正在广播: '{broadcast_msg}'")
                for peer_addr, (_, writer) in peers.items():
                    try:
                        writer.write((broadcast_msg + '\n').encode())
                        await writer.drain()
                    except ConnectionError:
                        logging.warning(f"无法发送到 {peer_addr}, 连接可能已断开。")

            elif command == "send":
                if len(parts) < 3:
                    print("用法: send <ip:port> <你的消息>")
                    continue

                target_peer = parts[1]
                direct_msg = f"[{my_address} -> direct]: {parts[2]}"

                if target_peer in peers:
                    _, writer = peers[target_peer]
                    logging.info(f"正在发送私信给 {target_peer}: '{direct_msg}'")
                    try:
                        writer.write((direct_msg + '\n').encode())
                        await writer.drain()
                    except ConnectionError:
                        logging.warning(f"无法发送到 {target_peer}, 连接可能已断开。")
                else:
                    print(f"错误: 未连接到 {target_peer}。使用 'peers' 查看当前连接。")

            elif command == "peers":
                if not peers:
                    print("当前未连接到任何对等节点。")
                else:
                    print("已连接的对等节点:")
                    for peer_addr in peers.keys():
                        print(f"- {peer_addr}")

            elif command == "peerlist":
                print("正在从种子服务器获取最新的节点列表...")
                new_peers = await connect_to_seed(args.seed_host, args.seed_port, args.port)
                if new_peers:
                    print("获取到以下节点:")
                    for peer in new_peers:
                        print(f"- {peer}")
                else:
                    print("未获取到任何其他节点。")

            elif command == "renewpeers":
                print("正在重新从种子服务器获取节点并尝试连接...")
                new_peers = await connect_to_seed(args.seed_host, args.seed_port, args.port)
                if new_peers:
                    print(f"获取到 {len(new_peers)} 个节点，正在尝试连接...")
                    for peer_str in new_peers:
                        try:
                            peer_host, peer_port_str = peer_str.split(':')
                            peer_port = int(peer_port_str)
                            # connect_to_peer 会检查是否已连接或连接自己
                            asyncio.create_task(connect_to_peer(peer_host, int(peer_port)))
                        except ValueError:
                            logging.warning(f"从种子服务器收到无效的地址格式: {peer_str}")
                else:
                    print("未获取到任何其他节点。")

            else:
                print(f"未知命令: '{command}'")

        except (EOFError, KeyboardInterrupt):
            # 优雅地处理 Ctrl+D 或 Ctrl+C
            print("\n检测到退出信号。")
            # 模拟执行 'quit' 命令
            parts = "quit".split()
            command = parts[0].lower()
            if command == "quit":
                logging.info("正在关闭节点...")
                for _, writer in peers.values():
                    writer.close()
                # 取消所有其他任务并停止事件循环
                for task in asyncio.all_tasks():
                    if task is not asyncio.current_task():
                        task.cancel()
                loop.stop()
            break


async def main():
    """
    P2P节点的主函数。
    """
    global my_address

    # 使用 argparse 解析命令行参数
    parser = argparse.ArgumentParser(description="Asyncio P2P聊天节点")
    parser.add_argument('--host', type=str, default='0.0.0.0', help="节点监听的主机地址。")
    parser.add_argument('--port', type=int, required=True, help="节点监听的端口。")
    parser.add_argument('--seed-host', type=str, default="127.0.0.1", help="种子服务器的主机地址。")
    parser.add_argument('--seed-port', type=int, default=9999, help="种子服务器的端口。")

    args = parser.parse_args()

    my_address = f"{args.host}:{args.port}"
    # 如果监听在0.0.0.0，需要换成一个具体的IP地址（如127.0.0.1）告诉其他节点，
    # 因为0.0.0.0是无法被其他节点连接的。
    # 在真实世界应用中，这需要更复杂的NAT穿透技术。对于本地测试，127.0.0.1足够。
    if args.host == '0.0.0.0':
        my_address = f"127.0.0.1:{args.port}"

    # 1. 启动一个服务器，用于监听其他对等节点的传入连接
    server = await asyncio.start_server(
        handle_incoming_peer, args.host, args.port)

    logging.info(f"本节点正在 {args.host}:{args.port} 上监听...")

    # 将服务器的运行作为一个后台任务
    asyncio.create_task(server.serve_forever())

    # 2. 连接到种子服务器获取初始的对等节点列表
    initial_peers = await connect_to_seed(args.seed_host, args.seed_port, args.port)

    # 3. 为列表中的每个对等节点创建一个连接任务
    for peer_str in initial_peers:
        try:
            peer_host, peer_port = peer_str.split(':')
            asyncio.create_task(connect_to_peer(peer_host, int(peer_port)))
        except ValueError:
            logging.warning(f"从种子服务器收到无效的地址格式: {peer_str}")

    # 4. 启动用户输入处理任务，这是程序的主交互循环
    await handle_user_input(args)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
        # 捕获取消异常，以实现安静退出
        pass
    finally:
        logging.info("节点已关闭。")

