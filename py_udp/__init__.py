

import sys
import threading
import time

# --- 【关键修正】定义一个全局的、共享的锁实例 ---
# 它是所有线程在访问 sys.stdout 时的“通行证”
STDOUT_LOCK = threading.Lock()

PROMPT = "> "

def controlled_print(message,is_debug=True):
    """
    使用共享的锁实例STDOUT_LOCK来保护标准输出。
    """
    if not is_debug: # 如果为调戏模块，返回不执行
        return
    # 1. 尝试获取锁：如果其他线程正在 with 块内，本线程会阻塞等待。
    with STDOUT_LOCK:
        # 2. 打印回车符 (\r) 将光标移到行首
        sys.stdout.write('\r')
        # 3. 清空当前行
        sys.stdout.write(' ' * (len(PROMPT) + 50))
        sys.stdout.write('\r')

        # 4. 打印真正的消息
        sys.stdout.write(f"{message}\n")

        # 5. 重新打印输入提示符
        sys.stdout.write(PROMPT)
        sys.stdout.flush()
    # 6. 退出 with 块，释放锁。
# ... 其他代码保持不变，它们都调用这个使用 STDOUT_LOCK 的函数 ...