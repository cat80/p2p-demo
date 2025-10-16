import threading
import time
import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import print_formatted_text

# 创建一个全局的输入会话
session = PromptSession('> ')


def receive_and_print_message(message):
    """
    接收线程收到消息后，调用此函数打印。
    它会安全地打印消息，并重新显示输入提示符。
    """
    # 使用 print_formatted_text 来确保消息在提示符上方安全打印
    print_formatted_text(f"\n[新消息] {message}", file=sys.stderr)
    # prompt_toolkit 自动处理重绘提示符


def input_thread():
    """专门负责用户输入的线程"""
    while True:
        try:
            # 使用 session.prompt() 代替 input()
            user_input = session.prompt()
            if user_input.lower() == 'exit':
                break
            # 模拟发送消息
            print_formatted_text(f"[我] {user_input}")

        except EOFError:
            break


def receive_thread(sock):
    """模拟接收 socket 消息的线程"""
    # 假设这是你的 socket 接收循环
    while True:
        # data = sock.recv(1024) # 实际的 socket 接收
        # 模拟接收到消息
        time.sleep(5)
        receive_and_print_message(f"来自 Alice 的秘密消息 @ {time.time()}")


# 启动线程
t_input = threading.Thread(target=input_thread)
t_receive = threading.Thread(target=receive_thread, args=(None,))  # 传入你的 socket 对象

t_receive.start()
t_input.start()