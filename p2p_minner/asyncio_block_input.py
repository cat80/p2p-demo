import asyncio
import hashlib
import time
import sys
import threading

from pandas.core.computation.expressions import where

event = threading.Event()

# --- 1. 阻塞的同步函数 ---
def blocking_input(prompt: str) -> str:
    """
    这是一个同步函数，内部使用了阻塞的 input()。
    它将在一个单独的线程中运行，以避免阻塞事件循环。
    """
    # 打印提示，并将输出强制刷新到控制台，确保用户能看到
    print(prompt, end="", flush=True)
    return sys.stdin.readline().strip()

def blocking_cpu_calc(prev_hash):

    nonce = 1
    while True:
        hash_value = prev_hash + nonce.to_bytes(4,byteorder='little')
        hash_value = hashlib.sha256(hash_value).digest()
        if hash_value.startswith(b'x\00\00'):
            return prev_hash,nonce,hash_value
        nonce += 1
# --- 2. 异步后台任务 ---
async def background_task():
    """
    这是一个异步协程，模拟一个需要持续运行的后台任务。
    它会每秒打印一次日志，证明事件循环在正常工作。
    """
    counter = 0
    print("📢 后台任务已启动...")
    try:
        while True:
            await asyncio.sleep(1)  # 非阻塞休眠
            print(f"⚙️ 后台任务运行中... 耗时: {counter} 秒")
            counter += 1
    except asyncio.CancelledError:
        # 当主任务取消它时，它会捕获这个异常并退出
        print("✅ 后台任务被取消并安全退出。")
        raise  # 重新抛出，让调用者知道它被取消了

# --- 3. 主协调协程 ---
async def main():
    """
    主协程，负责启动后台任务和阻塞输入任务。
    """

    # 启动后台任务，并将其包装成一个 Task
    background_task_handle = asyncio.create_task(background_task())

    # 使用 to_thread 运行阻塞的 input() 函数
    print("\n⏳ 正在等待您的输入...")

    while True:
        # 这一行会 'await'，但它是在一个单独的线程中等待用户输入
        # 主事件循环会在这期间继续运行 background_task
        user_data = await asyncio.to_thread(
            blocking_input,
            "❓ 请输入您的消息（按 Enter 键提交）: "
        )

        # 用户输入完成后，执行下面的代码
        print(f"\n🎉 收到输入！您输入的是: '{user_data}'")
        #
        # # 准备结束后台任务
        # background_task_handle.cancel()


    # 确保在程序退出前，所有任务都已完成（包括被取消的任务）
    await asyncio.gather(background_task_handle, return_exceptions=True)
    print("程序主流程结束。")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # 处理用户按下 Ctrl+C 强制退出的情况
        print("\n程序被用户中断退出。")