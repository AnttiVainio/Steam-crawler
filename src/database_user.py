import time
import re
from fractions import Fraction

from util import *

re_unicode = re.compile(r'\\u[a-f0-9]{4}')
re_htmlentity = re.compile(r'&[^&;]*;')
re_strip = re.compile(r'[^\w ]')

class User():

    def __init__(self,
                 queue_id = None, steamid = None, name = None, bools = None, numbers = None,
                 data = None, save_dump = True):
        if data:
            self.user_id_queue = file_to_queue(data[0])
            self.steam_id_queue = int(file_to_queue(data[1]))
            self.name = data[2].strip()
            self.time = int(data[3])
            self.data = tuple(int(i) for i in data[4].split(':'))
            if save_dump: self.dump = data[0] + data[1] + data[2] + data[3] + data[4]
        else:
            self.user_id_queue = queue_id
            self.steam_id_queue = int(steamid)
            self.name = name.strip()
            self.time = int(time.time())
            self.data = (tuple(1 if i else 0 for i in bools) if bools else tuple()) +\
                        (tuple(int(i) for i in numbers) if numbers else tuple())
            self.calc_dump()
        #simplifications:
        self.calc_simplifications()

    def update(self, new_data, item_names, item_important):
        #custom url
        if self.user_id_queue != new_data.user_id_queue:
            #print "  " + self.user_id_queue + " -> " + new_data.user_id_queue
            self.user_id_queue = new_data.user_id_queue
        #name
        if self.name and not new_data.name: print "Using old name for " + self.name
        else: self.name = new_data.name
        #time
        self.time = new_data.time
        #data
        if self.private or new_data.private:
            self.data = new_data.data
        else:
            old_data = self.data
            self.data = list(new_data.data)
            for i in range(len(item_names)):
                if old_data[i + 5] and not self.data[i + 5]:
                    self.data[i + 5] = old_data[i + 5]
                    if item_important[i]:
                        print "Using old '" + item_names[i] + "' value for " + self.name + " (" + str(self.data[i + 5]) + ")"
        self.calc_simplifications()
        self.calc_dump()

    def calc_simplifications(self):
        self.private = self.data[0]
        self.name_cleaned2 = ' '.join(
                             re_strip.sub(' ',
                             re_htmlentity.sub(' ',
                             re_unicode.sub(' ',
                             self.name.lower()))).replace('_', ' ').split())

    #dump goes directly into file
    def calc_dump(self):
        self.dump = "\n".join(( queue_to_file(self.user_id_queue), queue_to_file(str(self.steam_id_queue)), self.name, str(self.time), ":".join(str(i) for i in self.data) )) + "\n"

    def custom_url(self):
        return 1 if self.user_id_queue[0] == 'i' else 0

    def bg_id(self):
        return self.data[4]

    def words(self):
        return self.name.split()

    def name_cleaned1(self):
        return self.name_cleaned2.replace(' ', '')

    def get_recrawl_name(self):
        return "profiles/" + str(self.steam_id_queue)

    #call this only if not private
    def levels_n_badges(self, level_index, badge_index):
        if self.data[level_index] and self.data[badge_index]:
            if self.data[level_index] % self.data[badge_index] == 0:
                levels_per_badges = self.data[level_index] // self.data[badge_index]
            else: levels_per_badges = Fraction(self.data[level_index], self.data[badge_index])
            if self.data[badge_index] % self.data[level_index] == 0:
                return levels_per_badges, self.data[badge_index] // self.data[level_index]
            else: return levels_per_badges, Fraction(self.data[badge_index], self.data[level_index])
        else: return 0, 0
