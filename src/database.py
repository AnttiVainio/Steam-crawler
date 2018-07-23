import time
import math
import shutil
import StringIO
from operator import itemgetter
from random import randint

from database_user import User
from math_util import countmean
from settings import *
from util import *
from request import request_html
from important_list import handle_important_list

IMPRT_TRESHOLD_MULT = 0.9

class Database():

    def __init__(self, item_names, item_important, item_upload):
        db_mem = load_queue("mem/db_mem", [0, 0])
        self.importance_treshold = db_mem[1] * IMPRT_TRESHOLD_MULT #lower the treshold a bit to get new treshold at 1.0

        progress = Progress(int(db_mem[0]))

        self.level_index = item_names.index("level") + 5
        self.badge_index = item_names.index("badge") + 5

        #users are customurl part in lowercase or steam id as int (found_users and new_steamid_s)
        self.found_users = set()
        self.new_users = [] #synced
        self.new_steamid_l = [] #synced
        self.new_steamid_s = set()
        self.high_leveled = set()

        self.users_in_database = 0
        if file_exists("mem/data"):
            with open("mem/data", "rb") as data_file:
                index = 0
                for i in data_file:
                    if index == 0:
                        if i[0] == 'i':
                            self.found_users.add(file_userid_to_sid(i))
                        self.users_in_database+= 1
                        progress.increment()
                    elif index == 1:
                        self.found_users.add(file_steamid_to_sid(i))
                    index = (index + 1) % 5
                data_file.close()

        if file_exists("mem/new_data"):
            with open("mem/new_data", "rb") as data_file:
                index = 0
                user_data = [0] * 5
                for i in data_file:
                    user_data[index] = i
                    index+= 1
                    if index == 5:
                        self.new_users.append(User(data = user_data))
                        if user_data[0][0] == 'i':
                            self.new_steamid_s.add(file_userid_to_sid(user_data[0]))
                        uid = file_steamid_to_sid(user_data[1])
                        self.new_steamid_l.append(uid)
                        self.new_steamid_s.add(uid)
                        index = 0
                data_file.close()

        self.item_names = item_names
        self.item_important = item_important
        self.item_upload = item_upload
        self.items_important_amount = sum(1 if i else 0 for i in self.item_important)

        print "  " + str(self.users_in_database) + " users in database"
        if self.new_steamid_l:
            print "  " + str(len(self.new_steamid_l)) + " users found not yet in database"


    def save_data(self):
        if self.new_steamid_l:
            with open("mem/new_data", "wb") as data_file:
                for i in self.new_users: data_file.write(i.dump)
                data_file.close()


    def exists(self, queue_id):
        #value error can happen on invalid profiles-type id; this can originate from the comment section
        try: uid = queueid_to_sid(queue_id)
        except ValueError: return True
        return uid in self.found_users or uid in self.new_steamid_s


    def add_high_leveled(self, queue_id):
        self.high_leveled.add(queueid_to_sid(queue_id))


    #returns true if this user actually exists
    def save_user(self, queue_id, steamid, name, bools, numbers):
        #no custom url, no name and private
        if queue_id[0] == 'p' and not name and bools[0]:
            print "Nonexisting user: " + queue_id
            return False
        #already crawled
        elif int(steamid) in self.new_steamid_s:
            print "User " + queue_id + " is already crawled"
            return True
        #valid
        else:
            self.new_users.append(User(queue_id, steamid, name, bools, numbers))
            self.new_steamid_s.add(queueid_to_sid(queue_id))
            self.new_steamid_l.append(int(steamid))
            self.new_steamid_s.add(int(steamid))
            return True


    def synchronize(self, request_time, bg_images, game_names, hi_alias, existlist):
        starttime = time.clock()
        new_user_len = len(self.new_steamid_l)
        if not new_user_len:
            print "\n    No new users, aborting analysis"
            return False #this should crash
        print "\n    Analyzing data"
        current_time = time.time()

        #free memory (this will be updated later)
        self.found_users = set()

        steamid_max = SOME_STEAM_ID
        steamid_min = SOME_STEAM_ID
        total_files = 0
        total_crawl_age = 0.0
        general_names = ("public", "urls", "avatars", "bans", "backgrounds")
        general_names_private_index = 4
        general = [0] * len(general_names)
        bg_image = dict()
        items = [] # [ [values], (best value, best id, best name), (second value, second id, second name) ]
        for i in range(len(self.item_names)): items.append( [countmean(), [0], [0]] )
        common_names = ( dict(), dict(), dict() ) #full names, cleaned names, words
        cleaned_names_ws = [] #storage of most common spellings for cleaned names
        for i in range(COMMON_NAME_AMOUNT + 1): cleaned_names_ws.append(dict()) #should be same size as common_names_rec[1]
        words_ws = [] #storage of most common spellings for words
        for i in range(COMMON_NAME_AMOUNT): words_ws.append(dict()) #should be same size as common_names_rec[2]
        imprt_correct = dict() #importance container; sent to web [(id, name, steamid) = value]
        recrawl_queue = [] #used to determine who to recrawl
        #levels and badges
        levels_per_badges = 0
        badges_per_levels = 0
        #recrawl types
        recrawl_hiprivate = 0
        recrawl_important = 0
        recrawl_noname = 0
        recrawl_alias = 0
        recrawl_special = 0
        recrawl_name = 0
        recrawl_clean = 0
        recrawl_clean2 = 0
        recrawl_word = 0
        recrawl_word2 = 0
        recrawl_bg = 0
        #missing something
        without_name = 0
        without_something = 0

        if file_exists("mem/data"):
            shutil.move("mem/data", "mem/data_temp")
            user_data_file = open("mem/data_temp", "rb")
        else: user_data_file = StringIO.StringIO("")
        new_data_file = open("mem/data", "wb")

        progress = Progress(self.users_in_database + len(self.new_steamid_l), "1/3")

            #analyze
        i = 0
        index = 0
        user_data = [0] * 5
        read_new_users = False
        count_updated = 0
        count_new = 0
        while i < new_user_len:
            #construct user and determine if analyzed
            analyze_this = read_new_users
            if read_new_users: #from memory
                if self.new_steamid_l[i]:
                    u = self.new_users[i]
                    count_new+= 1
                    progress.increment()
                else: analyze_this = False #already updated
                i+= 1
            else: #from database file
                line = user_data_file.readline()
                if line:
                    user_data[index] = line
                    index+= 1
                    if index == 5:
                        analyze_this = True
                        u = User(data = user_data)
                        uid = file_steamid_to_sid(user_data[1])
                        if uid in self.new_steamid_s: #updated
                            uindex = self.new_steamid_l.index(uid)
                            u.update(self.new_users[uindex],
                                     self.item_names, self.item_important)
                            self.new_steamid_l[uindex] = None
                            self.new_steamid_s.remove(uid)
                            count_updated+= 1
                            progress.increment()
                        index = 0
                        progress.increment()
                else: read_new_users = True

            #analyze now
            if analyze_this:
                new_data_file.write(u.dump) #write
                total_files+= 1
                total_crawl_age+= u.time
                    #data
                general[1]+= u.custom_url()
                general[2]+= u.data[1]
                general[3]+= u.data[2]
                    #common names
                if u.name:
                        #whole
                    try: common_names[0][u.name]+= 1
                    except KeyError: common_names[0][u.name] = 1
                        #cleaned (lower case no spaces no special)
                    test_name = u.name_cleaned1()
                    if len(test_name) >= MIN_COMMON_NAME:
                        try: common_names[1][test_name]+= 1
                        except KeyError: common_names[1][test_name] = 1
                        #words (lower case)
                    for word in u.words():
                        if len(word) >= MIN_COMMON_WORD:
                            test_word = word.lower()
                            try: common_names[2][test_word]+= 1
                            except KeyError: common_names[2][test_word] = 1
                else: without_name+= 1

                if not u.private:
                        #no items
                    missing_something = 1
                        #general
                    general[0]+= 1
                    general[4]+= u.data[3]
                        #levels and badges
                    u_l_p_b, u_b_p_l = u.levels_n_badges(self.level_index, self.badge_index)
                    if u_l_p_b >= levels_per_badges:
                        if u_l_p_b == levels_per_badges: l_per_b_user = ("", "Multiple users")
                        else:
                            levels_per_badges = u_l_p_b
                            l_per_b_user = (u.user_id_queue, u.name)
                    elif u_b_p_l >= badges_per_levels:
                        if u_b_p_l == badges_per_levels: b_per_l_user = ("", "Multiple users")
                        else:
                            badges_per_levels = u_b_p_l
                            b_per_l_user = (u.user_id_queue, u.name)
                        #bg
                    if u.bg_id():
                        try: bg_image[u.bg_id()]+= 1
                        except KeyError: bg_image[u.bg_id()] = 1
                        #items
                    for j in range(len(self.item_names)):
                        if self.item_upload[j]:
                            if self.item_important[j]: missing_something*= u.data[j + 5]
                            items[j][0].add(u.data[j + 5])
                            if u.data[j + 5] >= items[j][1][0]:
                                items[j][2] = items[j][1]
                                items[j][1] = (u.data[j + 5], u.user_id_queue, u.name)
                            elif u.data[j + 5] >= items[j][2][0]: items[j][2] = (u.data[j + 5], u.user_id_queue, u.name)
                        elif u.data[j + 5] >= items[j][1][0]: items[j][1] = [u.data[j + 5]]
                    if missing_something == 0:
                        without_something+= 1

        #counts
        progress.clear()
        print "\n  " + str(count_updated) + " users updated"
        print "  " + str(count_new) + " new users"

        midtimes = [time.clock()] #part 1->2
        progress = Progress(1, "2/3")

        user_data_file.close()
        new_data_file.close()
        if file_exists("mem/data_temp"): remove_file("mem/data_temp")
        if file_exists("mem/new_data"): remove_file("mem/new_data")

        #reset (and free memory)
        self.new_users = [] #synced
        self.new_steamid_l = [] #synced
        self.new_steamid_s = set()
        self.users_in_database = total_files

            #sort recrawled stuff early
        common_names = (
            sorted(common_names[0].items(), key = itemgetter(1))[-COMMON_NAME_AMOUNT-1:],
            sorted(common_names[1].items(), key = itemgetter(1))[-COMMON_NAME_AMOUNT-1:],
            sorted(common_names[2].items(), key = itemgetter(1))[-COMMON_NAME_AMOUNT:])
        progress.increment()
        bg_image = sorted(bg_image.items(), key = itemgetter(1))[-BACKGROUND_AMOUNT-1:]
            #for recrawl
        common_names_rec = (
            tuple(i[0] for i in common_names[0]),
            tuple(i[0] for i in common_names[1]),
            tuple(i[0] for i in common_names[2]))
            #sets
        common_names_rec_all = set(i.replace(' ', '').lower() for i in common_names_rec[0] + common_names_rec[1] + common_names_rec[2])
        common_names_rec_all_long = set(i for i in common_names_rec_all if len(i) >= NAME_IN_NAME_MIN_LEN)
        bg_image_rec = set(i[0] for i in bg_image)

        user_data_file = open("mem/data", "rb")

        midtimes.append(time.clock()) #part 2->3
        progress = Progress(total_files, "3/3")

        index = 0
        for i in user_data_file:
            #construct user and determine if analyzed
            analyze_this = False
            user_data[index] = i
            index+= 1
            if index == 5:
                analyze_this = True
                u = User(data = user_data, save_dump = False)
                if user_data[0][0] == 'i':
                    self.found_users.add(file_userid_to_sid(user_data[0]))
                self.found_users.add(file_steamid_to_sid(user_data[1]))
                index = 0

            #analyze now
            if analyze_this:
                #steamid
                if len(str(u.steam_id_queue)) == STEAM_ID_LEN:
                    if u.steam_id_queue > steamid_max: steamid_max = u.steam_id_queue
                    elif u.steam_id_queue < steamid_min: steamid_min = u.steam_id_queue

                #importance
                importance = 0
                if not u.private:
                    for j in range(len(self.item_names)):
                        importance+= importance_value(u.data[j + 5], items[j][1][0], self.item_important[j])
                    if importance > self.importance_treshold:
                        imprt_correct[(u.user_id_queue, u.name, u.steam_id_queue)] = importance
                importance = max(importance, MIN_IMPORTANCE)

                #full name
                name_is_common = u.name in common_names_rec[0]

                #cleaned name stuff (get common spelling)
                test_name = u.name_cleaned1()
                if test_name in common_names_rec[1]:
                    clean_name_is_common = True
                    clean_index = common_names_rec[1].index(test_name)
                    try: cleaned_names_ws[clean_index][u.name_cleaned2]+= 1
                    except KeyError: cleaned_names_ws[clean_index][u.name_cleaned2] = 1
                else: clean_name_is_common = False

                #word stuff (get common spelling)
                word_is_common, word_is_common2 = False, False
                for word in u.words():
                    test_word = word.lower()
                    #word
                    if test_word in common_names_rec[2]:
                        word_is_common = True
                        word_index = common_names_rec[2].index(test_word)
                        try: words_ws[word_index][word]+= 1
                        except KeyError: words_ws[word_index][word] = 1
                    #name-word
                    if test_word in common_names_rec_all: word_is_common2 = True
                #for logging purposes, nothing more:
                if name_is_common or clean_name_is_common or word_is_common: word_is_common2 = False

                #some common clean name inside the cleaned name:
                clean_name_is_common2 = False
                if not name_is_common and not clean_name_is_common and not word_is_common:
                    for j in common_names_rec_all_long:
                        if j in test_name: clean_name_is_common2 = True

                #recrawl test
                time_since_crawl = current_time - u.time
                private_hi_level = u.private and (u.steam_id_queue in self.high_leveled or queueid_to_sid(u.user_id_queue) in self.high_leveled) and HILEVEL_TIME < time_since_crawl
                is_important = RECRAWL_TIME / importance < time_since_crawl
                has_no_name = not u.name and NAMELESS_TIME < time_since_crawl
                if u.private: name_change, spec_recrawl, bg_change = False, False, False
                else:
                    name_change = not u.data[-1] or ALIAS_TIME / ((float(u.data[-1]) / ALIAS_DAYS) ** 2) < time_since_crawl
                    spec_recrawl = RECRAWL_TIME_SPEC < time_since_crawl and (u.user_id_queue == l_per_b_user[0] or u.user_id_queue == b_per_l_user[0])
                    bg_change = BG_TIME < time_since_crawl and u.bg_id() in bg_image_rec
                if COMMON_TIME < time_since_crawl:
                    name_recrawl = name_is_common
                    clean_recrawl = clean_name_is_common
                    clean_recrawl2 = clean_name_is_common2
                    word_recrawl = word_is_common
                    word_recrawl2 = word_is_common2
                else: name_recrawl, clean_recrawl, clean_recrawl2, word_recrawl, word_recrawl2 = False, False, False, False, False
                if private_hi_level or is_important or has_no_name or name_change or spec_recrawl or name_recrawl or clean_recrawl or clean_recrawl2 or word_recrawl or word_recrawl2 or bg_change:
                    #crawl importants and special first
                    if is_important or spec_recrawl:
                        recrawl_queue.insert(0, u.get_recrawl_name())
                    else: recrawl_queue.append(u.get_recrawl_name())
                    if private_hi_level: recrawl_hiprivate+= 1
                    if is_important: recrawl_important+= 1
                    if has_no_name: recrawl_noname+= 1
                    if name_change: recrawl_alias+= 1
                    if spec_recrawl: recrawl_special+= 1
                    if name_recrawl: recrawl_name+= 1
                    if clean_recrawl: recrawl_clean+= 1
                    if clean_recrawl2: recrawl_clean2+= 1
                    if word_recrawl: recrawl_word+= 1
                    if word_recrawl2: recrawl_word2+= 1
                    if bg_change: recrawl_bg+= 1

                progress.increment()

        midtimes.append(time.clock()) #part 3->4

        user_data_file.close()

        #reset high leveled
        self.high_leveled = set()

        #steamid range
        steamidrange = (steamid_max - steamid_min + 1) / 1000000.0
        print "Steam id range: " + str(round(steamidrange, 1)) + "mil users"
        existcount = sum(int(i) for i in existlist)
        print "Approx Steam users: " + str(round(steamidrange * existcount / max(len(existlist), 1), 1)) +\
              "mil (" + str(existcount) + "/" + str(len(existlist)) + ")"

        #users without stuff
        print str(without_something) + " users without some item (" +\
              str(round(100.0 * without_something / general[0], 2)) + "%)"
        print str(without_name) + " users with no name (" +\
              str(round(100.0 * without_name / total_files, 2)) + "%)"

        #recrawl
        recrawl_queue_len = len(recrawl_queue)
        if recrawl_queue_len:
            def print_recrawl_amount(amount, desc):
                print "  " + str(amount) + " " + desc + " (" +\
                      str(round(100.0 * amount / recrawl_queue_len, 2)) + "%)"
            print "recrawling " + str(recrawl_queue_len) + " users (" +\
                  str(round(100.0 * recrawl_queue_len / total_files, 2)) + "%)"
            print_recrawl_amount(recrawl_hiprivate, "hi level private")
            print_recrawl_amount(recrawl_important, "important")
            print_recrawl_amount(recrawl_noname, "with no name")
            print_recrawl_amount(recrawl_alias, "for aliases")
            print_recrawl_amount(recrawl_special, "special")
            print_recrawl_amount(recrawl_name, "for name")
            print_recrawl_amount(recrawl_clean, "for clean name")
            print_recrawl_amount(recrawl_clean2, "for clean name 2")
            print_recrawl_amount(recrawl_word, "for words")
            print_recrawl_amount(recrawl_word2, "for name-words")
            print_recrawl_amount(recrawl_bg, "for background")

        #crawl some random steamids
        #these have added - character to indicate that they are random (there is one special procedure for these)
        recrawl_queue = ["-profiles/" + str(randint(steamid_min + 1, steamid_max - 1)) for i in range(RANDOM_CRAWL)] + recrawl_queue

        #sorting
        imprt_correct = sorted(imprt_correct.items(), key = itemgetter(1))

        #important list
        keys, values = handle_important_list(
            tuple(queue_to_file(str(imprt_correct[-i - 1][0][2])) for i in range(IMPORTANT_AMOUNT * 2)))

        keys+= ["total", "l_p_b", "l_p_b_u", "l_p_b_n", "b_p_l", "b_p_l_u", "b_p_l_n"]
        values+= [total_files,
                  float(levels_per_badges),
                  stringify(l_per_b_user[0]),
                  stringify(redact_urls(l_per_b_user[1])),
                  float(badges_per_levels),
                  stringify(b_per_l_user[0]),
                  stringify(redact_urls(b_per_l_user[1]))]
        #general
        for i in range(len(general_names)):
            keys.append(general_names[i])
            values.append(float(general[i]) / float(total_files if i < general_names_private_index else general[0]) * 100.0)
        #backgrounds
        for i in range(BACKGROUND_AMOUNT):
            keys.append("common_bg" + str(i))
            keys.append("common_bg_a" + str(i))
            keys.append("common_bg_n" + str(i))
            bg_url = bg_images[bg_image[-i - 1][0] - 1]
            game = bgurl_to_game(bg_url)
            values.append(stringify(untrim_bgurl(bg_url)))
            values.append(bg_image[-i - 1][1])
            values.append(stringify(game_names[game]) if game in game_names else '"?"')
        #common names
        for i in range(3):
            prefix = ("c_name", "s_name", "c_word")[i]
            for j in range(COMMON_NAME_AMOUNT):
                keys.append(prefix + str(j))
                keys.append(prefix + "_a" + str(j))
                #figure out cleaned name and words
                if i == 1: values.append(stringify(redact_urls(max(cleaned_names_ws[-j - 1].iteritems(), key = itemgetter(1))[0])))
                elif i == 2: values.append(stringify(redact_urls(max(words_ws[-j - 1].iteritems(), key = itemgetter(1))[0])))
                else: values.append(stringify(redact_urls(common_names[i][-j - 1][0])))
                values.append(int(common_names[i][-j - 1][1]))
        #items data
        for i in range(len(self.item_names)):
            if self.item_upload[i]:
                keys.append(self.item_names[i] + "_m0") # mean
                keys.append(self.item_names[i] + "_m1") # median
                keys.append(self.item_names[i] + "_m2") # mean deviation about median
                keys.append(self.item_names[i] + "_m3") # relative standard deviation
                values.append(items[i][0].get_mean())
                values.append(items[i][0].get_median())
                values.append(items[i][0].get_mean_deviation())
                values.append(items[i][0].get_relative_deviation())
                #high alias
                if self.item_names[i] == "alias":
                    hi_alias = (hi_alias * (HI_ALIAS_MULT - 1) + items[i][1][0]) / HI_ALIAS_MULT
                    keys.append("alias_hi")
                    values.append(hi_alias)
                else: #not alias
                    prefix = self.item_names[i] + "_hi"
                    for j in range(2):
                        keys.append(prefix + str(j))
                        keys.append(prefix + "_u" + str(j))
                        keys.append(prefix + "_n" + str(j))
                        values.append(int(items[i][j + 1][0]))
                        values.append(stringify(items[i][j + 1][1]))
                        values.append(stringify(redact_urls(items[i][j + 1][2])))
        #important people
        for i in range(IMPORTANT_AMOUNT):
            keys.append("imprtnt" + str(i))
            keys.append("imprtnt_u" + str(i))
            keys.append("imprtnt_n" + str(i))
            values.append(imprt_correct[-i - 1][1] * 100.0 / self.items_important_amount)
            values.append(stringify(imprt_correct[-i - 1][0][0]))
            values.append(stringify(redact_urls(imprt_correct[-i - 1][0][1])))
        #put data into json
        data = get_json(keys, values)

        #save db memory
        imprt_len = len(imprt_correct)
        self.importance_treshold = imprt_correct[-IMPRT_TRESHOLD_INDEX][1] if imprt_len >= IMPRT_TRESHOLD_INDEX else imprt_correct[0][1]
        save_queue([total_files,
                    self.importance_treshold],
                   "mem/db_mem")
        self.importance_treshold*= IMPRT_TRESHOLD_MULT #lower the treshold a bit to get new treshold at 1.0
        print "important list length: " + str(imprt_len)
        print "new importance treshold: " + str(round(self.importance_treshold * 100.0 / self.items_important_amount, 2))

        request_time = max(int(time.time()), request_time + 1)
        _hash = calc_hash(request_time)
        midtimes.append(time.clock()) #part 4->5

        print "\n  " + str(request_html("data dump",
                                        DATA_SAVER,
                                        get_post_values(_hash,
                                                        request_time,
                                                        "d",
                                                        data))[-1]),
        print get_time_string(starttime, midtimes) + "\n"

        return request_time, recrawl_queue, total_crawl_age / total_files, tuple(i[1][0] for i in items), hi_alias
