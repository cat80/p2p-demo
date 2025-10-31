
"""
    程序运行的主方法和入口
"""
import asyncio

listen_port = 19980

async def get_input_text(prompt):
    return await asyncio.to_thread(input,prompt)
async def run_main():

    pass

if __name__ == "__main__":
    asyncio.run(run_main())