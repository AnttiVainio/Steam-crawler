import bz2
import time

from settings import *
from util import *

def get_next_backup_time():
    files = get_folder_content("mem/backup")
    if not len(files): return 0
    newest = int(files[0].split("_")[0])
    for i in files:
        file_time = int(i.split("_")[0])
        if file_time > newest: newest = file_time
    return newest + BACKUP_INTERVAL

def get_backup_name(current_time, name):
    return "mem/backup/" + str(current_time) + "_" + name + ".bz2"

def create_backup(current_time, name):
    with open("mem/" + name, "rb") as data_file:
        with bz2.BZ2File(get_backup_name(current_time, name), "wb") as output_file:
            output_file.write(data_file.read())
            output_file.close()
        data_file.close()

def backup_files():
    starttime = time.clock()
    print "\n    Creating backup"
    loading = Loading()
    loading.start()

    backedup_files = ("backgrounds", "data", "stats")
    files = get_folder_content("mem/backup")
    current_time = int(time.time())

    if len(files) >= BACKUP_AMOUNT * len(backedup_files):
        oldest = int(files[0].split("_")[0])
        for i in files:
            file_time = int(i.split("_")[0])
            if file_time < oldest: oldest = file_time
        for i in backedup_files: remove_file(get_backup_name(oldest, i))
        print "Removed " + str(round((current_time - oldest) / 86400.0, 1)) + " days old backup"
    if file_exists("mem/data"):
        for i in backedup_files: create_backup(current_time, i)

    loading.stop = True
    loading.join()

    print "Backup created",
    print get_time_string(starttime) + "\n"
    return current_time + BACKUP_INTERVAL
