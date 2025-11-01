import sys
import os
import datetime
dir_name = os.path.dirname( os.path.abspath(__file__))

def append_text(txt):
    with open(os.path.join(  dir_name,'log.txt'),encoding='utf8',mode= 'a+') as file:
        prev = f"[{datetime.datetime.now()}] {os.getpid()}-{txt}\n"
        file.write(prev)
append_text(sys.argv)

append_text('开始执行')
print(f'aa:{sys.argv}')
txt= input('please input:')

append_text(txt)
append_text("执行结束")

