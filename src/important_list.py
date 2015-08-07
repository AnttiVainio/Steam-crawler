import time

from settings import *
from util import *

# This function also deletes too old lists
def get_newest_list():
    files = sorted(int(i) for i in get_folder_content("mem/important"))
    if not len(files): return tuple()
    #find newest
    newest = files[-1]
    #delete oldest ones
    max_delete = len(files) - IMPRT_LST_MIN_AMOUNT
    if max_delete > 0:
        currenttime = time.time()
        deleted = files[:max_delete]
        delete_amount = 0
        for i in deleted:
            if currenttime - i > IMPRT_LST_TIME_SPAN * 2:
                remove_file("mem/important/" + str(i))
                delete_amount+= 1
        if delete_amount:
            print "deleted " + str(delete_amount) + " important list" + ("" if delete_amount == 1 else "s")
    #return
    return tuple(i.strip() for i in load_queue("mem/important/" + str(newest), [], str))

def get_old_list():
    files = sorted(int(i) for i in get_folder_content("mem/important"))
    target_time = time.time() - IMPRT_LST_TIME_SPAN
    best_time = files[0]
    for i in files:
        if target_time - i >= 0: best_time = i
        elif i - best_time < DATA_DUMP_TIME * 1.5:
            best_time = i
    return tuple(i.strip() for i in load_queue("mem/important/" + str(best_time), [], str)), best_time

# The given data should be twice as long as the required data
def handle_important_list(data):
    newest = get_newest_list()
    save = len(data) != len(newest)
    if not save:
        for i in range(len(data)):
            if data[i] != newest[i]: save = True
    if save:
        save_queue(data, "mem/important/" + str(int(time.time())))
        print "saved new important list"
    old_data, old_time = get_old_list()
    keys = ["chng_time"]
    values = [int(time.time() - old_time)]
    for i in range(len(data) // 2):
        keys.append("chng" + str(i))
        try: values.append(old_data.index(data[i]) - i)
        except ValueError: values.append(-1000)
    return keys, values
