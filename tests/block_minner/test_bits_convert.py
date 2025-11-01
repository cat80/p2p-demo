import datetime
import math
#bits
import hashlib
import random



if __name__ == "__main__":
    bits = bytes.fromhex("000000a8")
    start_time = datetime.datetime.now()
    find_time_list =[]

    for i in range(1,1000000000):
        i_hash = hashlib.sha256(str(i).encode()).digest()
        if i_hash < bits:
            now =   datetime.datetime.now()
            find_time_list.append((now-start_time).total_seconds())
            print(now , i,i_hash)
            start_time = datetime.datetime.now()
            print(sum(find_time_list) / len(find_time_list))
    print(find_time_list)
    print(sum(  find_time_list) /len(find_time_list))