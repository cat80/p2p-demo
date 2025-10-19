import asyncio
import random
import datetime
def print_with_date(msg):
    print(f'[{datetime.datetime.now()}]:{msg}')
async def read_data_from_db(init):
    rand = random.uniform(1.0, 3.0)
    print_with_date(f'read_data:wait...{rand}')
    await asyncio.sleep(rand)
    print_with_date(f'read_data:get...{rand}.ok')
    return [init, rand]


async def read_data_from_rpc(init):
    rand = random.uniform(1.0, 3.0)
    print_with_date(f'rpc:wait...{rand}')
    await asyncio.sleep(rand)
    print_with_date(f'rpc:get...{rand}.ok')
    return [init, rand]

async def run_accept():
    while True:
        rand = random.uniform(1.0,10.0)
        print_with_date(f'accept:wait {rand} ...')
        await asyncio.sleep(rand)
        print_with_date(f'accept:get {rand} ok!!!')

async def run_recv():
    while True:
        rand = random.uniform(1.0, 3.0)
        print_with_date(f'recv:wait {rand} ...')
        await asyncio.sleep(rand)
        print_with_date('need get db data,start query db.')
        # 不好的写法
        # db_result = await read_data_from_db(rand)
        # prc_result = await read_data_from_db(rand)
        task_db = read_data_from_db(rand)
        task_rpc = read_data_from_rpc(rand)
        db_result,rpc_result = await asyncio.gather(task_db,task_rpc)
        print_with_date(f"db result:{db_result}")
        print_with_date(f"prc result:{rpc_result}")
        print_with_date(f'recv:get {rand} ok!!!')

async def run_main():
    task1 = asyncio.create_task(run_accept())
    task2 = asyncio.create_task(run_recv())
    await asyncio.gather(task1,task2)

if __name__ == "__main__":
    asyncio.run(run_main())