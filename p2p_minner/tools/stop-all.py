import psutil

prefix = "python.exe"
script_filename = 'p2p_minner/main.py'
killed_count = 0

for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        # print(proc)
        # print(proc.info)
        if not proc.info['cmdline']:
            continue
        cmd_line_str = " ".join(proc.info['cmdline'])

        # 我们这里假设 'P2P Node X' 是作为参数传给了脚本
        # 比如 python test_app.py "P2P Node 1"
        if script_filename in cmd_line_str and prefix in cmd_line_str:
            print(f"  找到匹配进程 (PID: {proc.info['pid']}): {cmd_line_str}")

            p = psutil.Process(proc.info['pid'])
            p.terminate()
            killed_count += 1

    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

print(f"psutil 清理完成，共终止了 {killed_count} 个进程。")