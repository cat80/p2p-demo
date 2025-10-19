import selectors
import time

# 1. 创建一个与操作系统交互的“联络官”
# 它会自动选择最高效的 I/O 多路复用模型 (epoll, kqueue, select)
selector = selectors.DefaultSelector()

print(f"[{time.strftime('%X')}] 脚本开始。我们将演示 select() 是如何阻塞程序的。")
print("-" * 50)

# 我们模拟一个持续5轮的事件循环
for i in range(1, 6):
    timeout = 2  # 我们设置每次等待的超时时间为 2 秒

    print(f"[{time.strftime('%X')}] [第 {i} 轮] 即将调用 selector.select(timeout={timeout})。")
    print(f"[{time.strftime('%X')}] [第 {i} 輪] 程序將會在這裡被【凍結】 {timeout} 秒...")

    # 2. 调用 select()，程序在这里进入阻塞状态（睡觉）
    # 内核会暂停我们的程序，直到：
    #  - 有我们注册的 I/O 事件发生（本示例中没有注册任何事件）
    #  - 或者，等待时间超过了 timeout 秒
    # 在此期间，这个 Python 脚本完全不消耗 CPU
    events = selector.select(timeout)

    # 3. 当 select() 返回后（睡醒了），代码才会继续往下执行
    if not events:
        # 因为我们没有注册任何事件，所以 select 总是因为超时而返回
        # 返回的 events 列表会是空的
        print(f"[{time.strftime('%X')}] [第 {i} 轮] select() 因超时而返回。程序已解冻！")
    else:
        # 如果有网络事件，这里会处理
        print(f"[{time.strftime('%X')}] [第 {i} 轮] select() 捕获到事件: {events}")

    print("-" * 50)


print(f"[{time.strftime('%X')}] 演示结束。")
"""

### 运行这个示例你会看到什么

当你运行 `selector_demo.py`，你会看到类似下面这样的输出，并且会明显地感觉到**每轮之间有2秒钟的停顿**：

```
[19:30:00] 脚本开始。我们将演示 select() 是如何阻塞程序的。
--------------------------------------------------
[19:30:00] [第 1 轮] 即将调用 selector.select(timeout=2)。
[19:30:00] [第 1 輪] 程序將會在這裡被【凍結】 2 秒...
(等待2秒)
[19:30:02] [第 1 轮] select() 因超时而返回。程序已解冻！
--------------------------------------------------
[19:30:02] [第 2 轮] 即将调用 selector.select(timeout=2)。
[19:30:02] [第 2 輪] 程序將會在這裡被【凍結】 2 秒...
(等待2秒)
[19:30:04] [第 2 轮] select() 因超时而返回。程序已解冻！
"""
