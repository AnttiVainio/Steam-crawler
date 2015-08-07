import sys
import time
import shutil
from math import log

from crawl import crawl
from util import file_exists, create_dirs

class Logger():
    def __init__(self):
        if file_exists("temp/logfile.txt"):
            shutil.copyfile("temp/logfile.txt", "temp/logfile_old.txt")
        self.terminal = sys.stdout
        self.log = open("temp/logfile.txt", "w")
    def write(self, message):
        self.terminal.write(message)
        if not "\r" in message:
            self.log.write(message)
            self.log.flush()

if __name__ == '__main__':
    if file_exists("mem/data_temp"):
        print("Danger: corrupted data file!")
    else:
        #Create directories
        create_dirs("mem/backup/")
        create_dirs("mem/important/")
        create_dirs("temp/")
        #Logging
        sys.stdout = Logger()
        #Check Python version
        print("Using Python version " +\
              str(sys.version_info.major) + "." +\
              str(sys.version_info.minor) + "." +\
              str(sys.version_info.micro) + " " +\
              sys.version_info.releaselevel + " " +\
              str(int(round(log(sys.maxint * 2 + 2, 2)))) + "bit")
        if sys.version_info.major != 2:
            print("Not supported; use Python 2")
        elif 0:
            print("")
            #start
            crawler = crawl()
            crawler.start()
            try:
                while(True): time.sleep(2)
            except KeyboardInterrupt:
                try:
                    print("    -> Closing program")
                    time.sleep(5)
                    print("    -> Analyzing")
                except KeyboardInterrupt:
                    print("    -> Skipping analysis")
                    crawler.quit_analyze = False
                crawler.quit = True
                crawler.join()
        print("I don't think there is a need to run another Steam crawler")
    raw_input("Finished")
