import threading
import time, datetime
import urllib
import hashlib
import re
import os
import json

from settings import *


    # Loading classes

class Loading(threading.Thread):
    def __init__(self, desc = ""):
        super(Loading, self).__init__()
        self.stop = False
        self.desc = "| " + desc + "\r"

    def run(self):
        while not self.stop:
            count = abs(int(time.clock() * 10.0) % 40 - 20)
            start = max(count - 3, 0)
            end = min(count + 3, 20)
            print "|" + (" " * start) + ("-" * (end - start)) + (" " * (20 - end)) + self.desc,
            time.sleep(0.1)

class Progress():
    def __init__(self, total, desc = ""):
        self.total = max(total, 1)
        self.progress = -1
        self.progress_bars = -1
        self.desc = "| " + desc + "\r"
        self.increment()

    def increment(self):
        self.progress+= 1
        temp = 20.0 * self.progress / self.total - 0.5
        if temp > self.progress_bars:
            while temp > self.progress_bars: self.progress_bars+= 1
            print "|" + ("-" * self.progress_bars) + (" " * (20 - self.progress_bars)) + self.desc,

    def done(self):
        print "|        done        |\r",

    def clear(self):
        print (" " * (21 + len(self.desc))) + "\r",


    # Calculations

#turns a string into json string
def stringify(string):
    return '"' + string.replace('\\', '\\\\').replace('"', '\\"') + '"'

def importance_value(value, highest, important):
    return (float(value) / max(float(highest), 1.0)) ** 2.0 if important else 0.0


    # Text transforms

def file_to_queue(user):
    prefix = '-' if user[0] == '-' else ''
    u = user[1:] if user[0] == '-' else user
    if   u[0] == 'q': return prefix + "profiles/7656119" + u[1:].strip()
    elif u[0] == 'p': return prefix + "profiles/" + u[1:].strip()
    elif u[0] == 'r': return prefix + "7656119" + u[1:].strip()
    elif u[0] == 'i': return prefix + "id/" + u[1:].strip()
    else: return user.strip()

def queue_to_file(user):
    if len(user) >= 7 and user[:7] == "7656119": return "r" + user[7:]
    return user\
        .replace("profiles/7656119", "q", 1)\
        .replace("profiles/", "p", 1)\
        .replace("id/", "i", 1)

def trim_bgurl(url):
    return "/".join(url.split("/")[-2:])

def untrim_bgurl(url):
    return "http://cdn.akamai.steamstatic.com/steamcommunity/public/images/items/" + url

def file_to_bgurl(url):
    return url.strip()

def bgurl_to_file(url):
    return url

def bgurl_to_game(url):
    return url.split("/")[-2]

def user_url_to_user(user_url):
    return user_url.split("/")[1]

#queue id to search id
def queueid_to_sid(user):
    return int(user_url_to_user(user)) if user[0] == 'p' else user_url_to_user(user).lower()

#user id from file to search id
def file_userid_to_sid(user):
    return user_url_to_user(file_to_queue(user)).lower()

#steam id from file to search id
def file_steamid_to_sid(user):
    return int(file_to_queue(user))


    # File system

def file_exists(filename):
    return os.path.exists(filename)

def remove_file(filename):
    os.remove(filename)

def create_dirs(path):
    if not file_exists(path):
        os.makedirs(path)

def get_folder_content(folder):
    return tuple(f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) )


    # Load and save

def load_queue(filename, default, func = float):
    if not file_exists(filename): return default
    else:
        queue_file = open(filename, "rb")
        queue = queue_file.readlines()
        queue_file.close()
        return [func(i) for i in queue]

def save_queue(queue, filename, func = str):
    queue_copy = [func(i) for i in queue]
    queue_file = open(filename, "wb")
    queue_file.write('\n'.join(queue_copy))
    queue_file.close()

def load_dict(filename, default):
    if not file_exists(filename): return default
    else:
        new_dict = dict()
        dict_file = open(filename, "rb")
        for i in dict_file:
            values = i.split(":", 1)
            new_dict[values[0]] = values[1].strip()
        dict_file.close()
        return new_dict

def save_dict(queue, filename):
    queue_copy = [(i + ":" + queue[i]) for i in queue]
    dict_file = open(filename, "wb")
    dict_file.write('\n'.join(queue_copy))
    dict_file.close()


    # Web

def calc_hash(realtime):
    return hashlib.sha512(str(realtime)).hexdigest()

def get_json(keys, values):
    data = ""
    for i in range(len(keys)): data+= ',"' + keys[i] + '":' + str(values[i])
    return '{' + data[1:] + '}'

def get_post_values(_hash, realtime, _type, data, init = 0):
    return urllib.urlencode( { "hash" : _hash,
                               "time" : realtime,
                               "type" : _type,
                               "data" : data,
                               "init" : init } )


    # Performance

def get_time_string(starttime, midtimes = None):
    if midtimes:
        result = "("
        times = [starttime] + midtimes + [time.clock()]
        for i in range(1, len(times)):
            result+= str(round(times[i] - times[i - 1], 1)) + " "
        result = result[:-1] + ") ("
    else:
        result = "("
        times = (starttime, time.clock())
    return result + str(round(times[-1] - times[0], 2)) + " sec)"


    # Find

#used to find stuff from html using reg
def find_item(reg, html, error, name, index = 1):
    match = re.search(reg, html)
    if not match:
        print "No " + error + " for " + name
        return None
    else: return match.group(index)


    # Parse aliases

#used by a regex in parse_aliases
def zeropadder(matchobj):
    return matchobj.group(0)[0] + "0" + matchobj.group(0)[1:]

#used in parse_aliases
def parse_time(timestring, timeformat):
    return time.mktime(datetime.datetime.strptime(timestring, timeformat).timetuple())

def parse_aliases(data, error):
    #parse json
    try:
        data = json.loads(data)
    except ValueError:
        print "Invalid json for " + error
        return 1
    #go through time strings
    current_time = time.time()
    smallest = current_time + 1
    if len(data):
        zeropad = re.compile(r'[^\d]\d[^\d]')
        year = ", " + str(datetime.date.today().year)
        for i in data:
            #edit time string
            timestring = i['timechanged']
            timestring = zeropad.sub(zeropadder, ' ' + timestring[:-2] + timestring[-2:].upper())
            #try to parse time string
            new_time = smallest
            # accepted example:  18 Feb, 2012 @ 08:20AM
            try: new_time = parse_time(timestring, " %d %b, %Y @ %I:%M%p")
            except ValueError:
                #sometimes the month and day are swapped
                # accepted example:  Feb 18, 2012 @ 08:20AM
                try: new_time = parse_time(timestring, " %b %d, %Y @ %I:%M%p")
                except ValueError:
                    #add current year if the year is missing
                    timestring2 = timestring[:7] + year + timestring[7:]
                    # accepted example:  18 Feb @ 08:20AM
                    try: new_time = parse_time(timestring2, " %d %b, %Y @ %I:%M%p")
                    except ValueError:
                        # accepted example:  Feb 18 @ 08:20AM
                        try: new_time = parse_time(timestring2, " %b %d, %Y @ %I:%M%p")
                        except ValueError:
                            print "Couldn't parse" + timestring + " for " + error
            if new_time < smallest: smallest = new_time
    #analyze data
    if smallest < current_time:
        #per ALIAS_DAYS days
        return int(round(86400.0 * ALIAS_DAYS / (current_time - smallest) * len(data)))
    return 1
