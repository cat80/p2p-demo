# 启动所有的节点
import random
import subprocess
import sys
import time


def start_all():
    port = 17890
    for index in range(0,5):

        node_id = port+index
        print(f'启动节点:{node_id}')
        #  cmd = [sys.executable,r'D:\prj\python\p2p-demo\block_minner\tools\test_app.py ' ,str(index)]
        script_path = r'D:/prj/python/p2p-demo/block_minner/main.py'
        cmd_string = f'start "P2P Node {node_id}" cmd /k {sys.executable} {script_path} {node_id}'

        print(f"正在执行: {cmd_string}")
        subprocess.Popen(cmd_string, shell=True)

        if index == 0:
            print('第一个节点启动后暂时3秒等待')
            time.sleep(3)
        else:
            #
            pass
        # 1. 必须使用 shell=True 才能识别 'start' 命令
        # 2. 我们不需要保存 'p' 对象，因为新窗口独立于本脚本运行

if __name__ == "__main__":
    start_all()