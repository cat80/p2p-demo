import asyncio
from typing import Dict, Tuple
from protocol import AsyncProtocol
# --- 全局状态 ---
# 使用一个字典来存储所有连接的客户端
# 键是 (ip, port) 元组，值是 (StreamReader, StreamWriter) 元组
clients: Dict[Tuple[str, int], Tuple[asyncio.StreamReader, asyncio.StreamWriter]] = {}


async def broadcast(message: str, sender_addr: Tuple[str, int] = None):
    """
    向所有客户端广播消息。
    :param message: 要发送的消息字符串。
    :param sender_addr: 发送者的地址，广播时会排除此地址。如果为 None，则发给所有人（系统消息）。
    """
    # 编码消息
    encoded_message = message.encode('utf8')

    # 为了防止在迭代过程中字典大小改变，我们遍历其副本
    for addr, (reader, writer) in list(clients.items()):
        if addr == sender_addr:
            continue
        try:
            writer.write(encoded_message)
            await writer.drain()
        except (ConnectionResetError, BrokenPipeError):
            print(f"广播时发现客户端 {addr} 已断开, 将其移除。")
            # 如果连接已断开，则从字典中移除并关闭连接
            if addr in clients:
                del clients[addr]
            writer.close()
            await writer.wait_closed()
            # 广播该用户已离开
            await broadcast(f"[系统通知] 用户 {addr} 已掉线。\n", None)


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """
    为每个连接的客户端执行此协程。
    """
    addr = writer.get_extra_info('peername')
    print(f"接受来自 {addr} 的新连接。")

    # 将新客户端添加到字典中
    clients[addr] = (reader, writer)

    # 广播新用户加入的消息
    await broadcast(f"[系统通知] 欢迎 {addr} 加入聊天室！\n", addr)
    writer.write(f"您已成功连接! 当前在线 {len(clients)} 人。\n".encode('utf8'))
    await writer.drain()

    buffer_data = b''
    try:
        while True:
            data,buffer_data = await AsyncProtocol.deserialize_stream(reader,buffer_data)
            if not data:
                # 客户端主动断开连接
                break
            # 这里处理消息，需要把writer，传给客户给
            msg_type = data['type']
            message = data.decode('utf8').strip()
            print(f"收到来自 {addr} 的消息: {message}")

            # 准备广播消息，附带发送者信息
            broadcast_message = f"[{addr[0]}:{addr[1]}]> {message}\n"
            await broadcast(broadcast_message, addr)

    except (ConnectionResetError, asyncio.IncompleteReadError):
        print(f"与 {addr} 的连接异常中断。")
    finally:
        print(f"客户端 {addr} 断开连接。")
        # 从字典中移除客户端
        if addr in clients:
            del clients[addr]

        # 关闭连接
        writer.close()
        await writer.wait_closed()

        # 广播用户离开的消息
        await broadcast(f"[系统通知] {addr} 已离开聊天室。\n", None)


async def handle_server_commands():
    """
    一个独立的任务，用于处理在服务器控制台输入的命令。
    """
    print("\n--- 服务端命令已启用 ---")
    print("可用命令:")
    print("  /clientlist          - 查看当前在线用户")
    print("  /bc <message>        - 发布系统广播")
    print("  /block <ip> <port>   - 踢掉指定用户")
    print("-------------------------\n")

    loop = asyncio.get_running_loop()

    while True:
        # 使用 run_in_executor 在一个独立的线程中运行阻塞的 input() 函数
        # 这样就不会阻塞整个事件循环
        command_line = await loop.run_in_executor(None, input)
        parts = command_line.strip().split(' ', 2)
        command = parts[0]

        if command == '/clientlist':
            if not clients:
                print("当前没有在线用户。")
            else:
                print("--- 当前在线用户 ---")
                for i, addr in enumerate(clients.keys()):
                    print(f"  {i + 1}. {addr[0]}:{addr[1]}")
                print("----------------------")

        elif command == '/bc':
            if len(parts) < 2:
                print("用法: /bc <message>")
                continue
            message = parts[1]
            print(f"发布系统广播: {message}")
            await broadcast(f"[系统通知] {message}\n", None)

        elif command == '/block':
            if len(parts) < 3:
                print("用法: /block <ip> <port>")
                continue

            try:
                ip, port = parts[1], int(parts[2])
                addr_to_block = (ip, port)

                if addr_to_block in clients:
                    _, writer_to_block = clients[addr_to_block]
                    writer_to_block.write("[系统通知] 您已被管理员踢出聊天室。\n".encode('utf8'))
                    await writer_to_block.drain()
                    writer_to_block.close()
                    await writer_to_block.wait_closed()

                    # handle_client 的 finally 块会自动处理清理和广播
                    print(f"用户 {addr_to_block} 已被踢下线。")
                else:
                    print(f"错误: 未找到用户 {addr_to_block}。")
            except ValueError:
                print("错误: 端口号必须是数字。")
            except Exception as e:
                print(f"执行踢出操作时发生错误: {e}")
        else:
            print(f"未知命令: {command}")


async def main():
    HOST, PORT = '0.0.0.0', 8877

    # 启动 TCP 服务器
    server = await asyncio.start_server(handle_client, HOST, PORT)

    # 获取服务器正在监听的地址信息
    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'服务器已在 {addrs} 上启动...')

    # 并发运行服务器和服务器命令处理器
    command_task = asyncio.create_task(handle_server_commands())

    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n服务器正在关闭...")
