import random
import datetime
import  time
# 这里使用同步阻塞的方法，可以看到这里面执行的效果,可以和asyncio来对比

def print_with_date(msg):
    print(f'[{datetime.datetime.now()}]:{msg}')
def read_data_from_db(init):
    rand = random.uniform(1.0, 3.0)
    print_with_date(f'read_data:wait...{rand}')
    time.sleep(rand)
    print_with_date(f'read_data:get...{rand}.ok')
    return [init, rand]


def read_data_from_rpc(init):
    rand = random.uniform(1.0, 3.0)
    print_with_date(f'rpc:wait...{rand}')
    time.sleep(rand)
    print_with_date(f'rpc:get...{rand}.ok')
    return [init, rand]

def run_accept():
    while True:
        rand = random.uniform(1.0,10.0)
        print_with_date(f'accept:wait {rand} ...')
        time.sleep(rand)
        print_with_date(f'accept:get {rand} ok!!!')

def run_recv():
    while True:
        rand = random.uniform(1.0, 3.0)
        print_with_date(f'recv:wait {rand} ...')
        time.sleep(rand)
        print_with_date('need get db data,start query db.')
        # 不好的写法
        # db_result = await read_data_from_db(rand)
        # prc_result = await read_data_from_db(rand)
        db_result = read_data_from_db(rand)
        rpc_result = read_data_from_rpc(rand)
        print_with_date(f"db result:{db_result}")
        print_with_date(f"prc result:{rpc_result}")
        print_with_date(f'recv:get {rand} ok!!!')

def run_main():
    # 因为第一个有whiel True第三个永远不会执行,要想启动第三个只能新开一个线程来解决
    import threading
    acceept_theard = threading.Thread(target=run_accept)
    acceept_theard.start()
    run_recv()
if __name__ == "__main__":
    run_main()