import asyncio
import sys


async def receive_messages(reader: asyncio.StreamReader):
    """
    持续从服务器接收消息并打印到控制台。
    """
    try:
        while True:
            data = await reader.read(1024)
            if not data:
                print("\n与服务器的连接已断开。")
                break

            message = data.decode('utf8').strip()
            # 打印消息，并重新显示输入提示符
            print(f"\r{message}\n> ", end="")

    except (ConnectionResetError, asyncio.IncompleteReadError):
        print("\n连接异常中断。")
    finally:
        # 通知主程序退出
        loop = asyncio.get_running_loop()
        loop.stop()


async def send_messages(writer: asyncio.StreamWriter):
    """
    等待用户输入，并将消息发送到服务器。
    """
    loop = asyncio.get_running_loop()
    try:
        while True:
            # 打印输入提示符
            print("> ", end="", flush=True)
            # 使用 run_in_executor 在一个独立的线程中运行阻塞的 sys.stdin.readline
            # 这样就不会阻塞事件循环对消息的接收
            message = await loop.run_in_executor(
                None, sys.stdin.readline
            )
            # 如果输入为空（例如Ctrl+D），则退出
            if not message.strip():
                continue

            writer.write(message.encode('utf8'))
            await writer.drain()

    except (ConnectionResetError, BrokenPipeError):
        print("\n无法发送消息，连接已断开。")
    finally:
        # 通知主程序退出
        loop = asyncio.get_running_loop()
        if not loop.is_closed():
            loop.stop()


async def main():
    # 从命令行参数获取地址和端口，或使用默认值
    HOST = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
    PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8877

    try:
        reader, writer = await asyncio.open_connection(HOST, PORT)
    except ConnectionRefusedError:
        print(f"连接失败：无法连接到 {HOST}:{PORT}。请确保服务器正在运行。")
        return
    except Exception as e:
        print(f"连接时发生未知错误: {e}")
        return

    print("--- 已成功连接到聊天服务器 ---")
    print("--- 直接输入内容按回车即可发送 ---")

    # 并发运行消息接收和消息发送任务
    receive_task = asyncio.create_task(receive_messages(reader))
    send_task = asyncio.create_task(send_messages(writer))

    # 等待其中一个任务结束（通常是因为连接断开）
    await asyncio.gather(receive_task, send_task)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n正在断开连接...")
    finally:
        print("客户端已关闭。")
