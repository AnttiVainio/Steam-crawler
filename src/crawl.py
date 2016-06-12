import time
import threading
import re

from database import Database
from settings import *
from util import *
from request import request_html, get_req_time
from backup import get_next_backup_time, backup_files

# List of games that can't be crawled
UNKNOWN_GAMES = "251290", "324820", "342090", "368020", "364690", "291090", "380180"

class crawl(threading.Thread):

    def __init__(self):
        starttime = time.clock()
        super(crawl, self).__init__()
        print "    Welcome to the crawler version " + VERSION + "\n"
        for i in USER_AGENT.split():
            print i + "\n ",
        print "\nInitializing"

        self.quit = True
        self.quit_analyze = True
        self.request_time = 0

        #alias should be the last one
        #if not, recrawl will no longer work for alias
        self.item_names = ("level",
                           "badge",
                           "game",
                           "screenshot",
                           "video",
                           "workshop",
                           "recommendation",
                           "guide",
                           "image",
                           "greenlight",
                           "item",
                           "group",
                           "friend",
                           "alias")
        self.item_search = (r"badges/",
                            r"games/",
                            r"screenshots/",
                            r"videos/",
                            r"myworkshopfiles/",
                            r"recommended/",
                            r"myworkshopfiles/\?section=guides",
                            r"images/",
                            r"myworkshopfiles/\?section=greenlight",
                            r"inventory/",
                            r"groups/",
                            r"friends/")
        self.item_important = (True,  #level
                               False, #badge
                               True,  #game
                               False, #screenshot
                               False, #video
                               False, #workshop
                               False, #recommendation
                               False, #guide
                               False, #image
                               False, #greenlight
                               False, #item
                               True,  #group
                               True,  #friend
                               False) #alias
        self.item_upload = list(self.item_important)
        self.item_upload[-1] = True #alias
        self.item_upload = tuple(self.item_upload)

        if not file_exists("mem/stats"): print "\nRUNNING THE CRAWLER FOR THE FIRST TIME\n"
        # [start time, crawls, bytes, crawl age, uptime, hi alias]
        self.alltimestats = load_queue("mem/stats", [time.time(), 0.0, 0.0, time.time(), 0.0, 0.0])
        self.queue = load_queue("mem/queue", [FIRST_USER], file_to_queue)
        self.hiscores = load_queue("mem/high", [1] * len(self.item_names), int)
        self.save_times = load_queue("mem/times", [])
        self.save_amounts = load_queue("mem/bytes", [])
        self.bg_images = load_queue("mem/backgrounds", [], file_to_bgurl)
        self.uptime = self.alltimestats[4]
        if file_exists("mem/exists"):
            with open("mem/exists", "rb") as f: self.existlist = f.read()
        else: self.existlist = ""

        self.games = load_dict("mem/games", {})
        self.games_queue = []
        for i in self.bg_images:
            game = bgurl_to_game(i)
            if game not in self.games and game not in self.games_queue: self.games_queue.append(game)

        #regexes and search strings
            #public
        self.re_name = re.compile(r'"personaname":"([^"]*)') # 1
        self.re_steamid = re.compile(r'"steamid":"([^"]*)') # 1
        self.re_customurl = re.compile(r'"url":"([^"]*)') # 1
        self.se_private = "private_profile"
        self.se_noavatar = "fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb_full.jpg"
        self.se_bans = "profile_ban"
            #private
        self.se_background = "has_profile_background"
        self.re_bgimage = re.compile(r"background-image: url\(( ')?([^')]*)") # 2
        self.re_friends      = re.compile(r'steamcommunity\.com/((id|profiles)/[\w-]*)') # 1
        self.re_friend_level = re.compile(r'steamcommunity\.com/((id|profiles)/[\w-]*)[\D]*([\d]*)') # 1 + 3
        self.re_level = re.compile(r'"friendPlayerLevelNum">(\d*)') # 1
            #positions
        self.se_comments = "profile_comment_area"
        self.se_leftcol = "profile_leftcol"
        self.se_rightcol = "profile_rightcol"
        self.se_topfriends = "profile_topfriends"
            #game
        self.re_game = re.compile(r'apphub_AppName[^>]*>([^<]*)') # 1

        #performance stats
        self.crawl_times_sum = 0
        self.crawl_times_amount = 0
        self.crawls_fast = 0
        self.crawls_slow = 0
        self.crawls_error = 0 #errors are not counted to mean sleep

        self.database = Database(self.item_names, self.item_important, self.item_upload)

        self.next_backup = get_next_backup_time()

        print "  " + str(len(self.queue)) + " users in queue"
        print "  " + str(len(self.bg_images)) + " backgrounds found"
        print "  " + str(len(self.games)) + " games crawled"
        print "  " + str(round(self.uptime / 86400.0, 1)) + " days of crawling time"
        print "Next backup in " + str(round((self.next_backup - time.time()) / 3600.0, 1)) + " hours"
        print "Done initializing",
        print get_time_string(starttime)


    def update_uptime(self, current_time):
        self.alltimestats[4] = self.uptime + current_time - self.session_starttime


    #function for finding the amount of certain item
    def find_value(self, index, html, name):
        match = re.search(r'steamcommunity\.com/' + self.current_user + r'/' + self.item_search[index] + r'"([\D]*)([\d,]+)', html, re.I)
        if not match or "steamcommunity.com/" in match.group(1): return 0
        else: return match.group(2).replace(',', '')


    def parse(self, html1, check_existence):
        if html1.find("<title>Steam Community") == -1:
            print "    ALERT: Got wrong language website!"
            return 0

        #user name (must be found)
        name = find_item(self.re_name, html1, "user name", self.current_user)
        if check_existence:
            if len(self.existlist) >= EXIST_LIST_SIZE: self.existlist = self.existlist[1:]
            self.existlist+= "0" if name == None else "1"
        if name == None: return 0

        #steam id (must be found)
        steamid = find_item(self.re_steamid, html1, "Steam id", self.current_user)
        c_user_id = user_url_to_user(self.current_user) if self.current_user[0] == 'p' else None #profiles/...
        if steamid:
            if c_user_id and steamid != c_user_id:
                print "Mismatch: " + self.current_user + " != " + steamid
        else: steamid = c_user_id if c_user_id else None
        if not steamid: return 0

        #custom url (NOTE: current_user should be updated only if really necessary!)
        #basically this is updated always when the current user uses steam id and custom url is available
        if self.current_user[0] == 'p': #profiles/...
            customurl = find_item(self.re_customurl, html1, "Custom URL", self.current_user)
            if customurl and r"\/id\/" in customurl:
                self.current_user = "id/" + customurl.split("\/")[-2]

        private_profile = html1.find(self.se_private) != -1
        has_avatar = html1.find(self.se_noavatar) == -1
        has_bans = html1.find(self.se_bans) != -1

        html2_size = 0
        if not private_profile:
            #parts of the page
                #left and right cols
            leftcol_index = html1.find(self.se_leftcol)
            rightcol_index = html1.find(self.se_rightcol)
                #right col
            html1_right = ""
            if rightcol_index == -1:
                print "Couldn't find right collumn for " + name
            elif leftcol_index < rightcol_index:
                html1_right = html1[rightcol_index:]
            else: html1_right = html1[rightcol_index:leftcol_index]
                #left col
            html1_left = ""
            if leftcol_index == -1:
                print "Couldn't find left collumn for " + name
            elif rightcol_index < leftcol_index:
                html1_left = html1[leftcol_index:]
            else: html1_left = html1[leftcol_index:rightcol_index]
                #comments
            html1_comments = ""
            comments_index = html1_left.find(self.se_comments)
            if comments_index == -1:
                print "Couldn't find comments for " + name
            else: html1_comments = html1_left[comments_index:]
                #top friends
            html1_topfriends = ""
            topfriend_index = html1_right.find(self.se_topfriends)
            if topfriend_index == -1:
                print "Couldn't find top friends for " + name
            else: html1_topfriends = html1_right[topfriend_index:]

            #background
            has_background = html1.find(self.se_background) != -1
            if has_background:
                bg_image = find_item(self.re_bgimage, html1, "background", name, 2)
                if bg_image:
                    bg_image = trim_bgurl(bg_image)
                    if bg_image in self.bg_images:
                        bg_image = self.bg_images.index(bg_image) + 1
                    else:
                        self.bg_images.append(bg_image)
                        game = bgurl_to_game(bg_image)
                        if game not in self.games: self.games_queue.append(game)
                        bg_image = len(self.bg_images)
                else: bg_image = 0
            else: bg_image = 0

            #level
            level = int(find_item(self.re_level, html1, "level", name))
            if level: items = [level]
            else: items = [0]

            #items (these are searched only from the right collumn in the webpage)
            for i in range(len(self.item_search)):
                items.append(int(self.find_value(i, html1_right, name)))

            #aliases
            items.append(0)
            html2 = request_html(self.current_user + "/ajaxaliases", self.current_url + "/ajaxaliases")
            if html2[0]: items[-1] = parse_aliases(html2[2], name)
            if len(html2) > 1: html2_size = html2[1]

            #check hiscores
            for i in range(len(items)):
                if items[i] > self.hiscores[i]:
                    print name + " broke hi-score '" + self.item_names[i] + "' (" + str(self.hiscores[i]) + " -> " + str(items[i]) + ")"
                    self.hiscores[i] = items[i]

            #get friends
            get_friends = len(self.queue) < MAX_QUEUE_SIZE
                #top friends with levels
            friends = re.findall(self.re_friend_level, html1_topfriends)
            if friends:
                for i in friends:
                    friend = i[0]
                    if friend != self.current_user:
                        is_high_leveled = int(i[2]) >= QUICK_CRAWL_LEVEL
                        if is_high_leveled: self.database.add_high_leveled(friend)
                        if not self.database.exists(friend):
                            if is_high_leveled:
                                try: queue_index = self.queue.index(friend)
                                except ValueError: queue_index = None
                                if queue_index == None or queue_index > 10:
                                    if queue_index: del self.queue[queue_index]
                                    self.queue.insert(0, friend)
                                    print "Quick crawling " + friend + " (" + i[2] + ") "
                            elif get_friends and not friend in self.queue:
                                self.queue.append(friend)
                #comments (get these only if there is space in the queue)
            if get_friends:
                friends = re.findall(self.re_friends, html1_comments)
                if friends:
                    for i in friends:
                        friend = i[0]
                        if friend != self.current_user and not friend in self.queue and not self.database.exists(friend):
                            self.queue.append(friend)

        bools = [private_profile, has_avatar, has_bans]
        numbers = None
        if not private_profile:
            bools.append(has_background)
            numbers = [bg_image] + items

        self.database.save_user(self.current_user, steamid, name, bools, numbers)

        return html2_size


    def parse_game(self, html1, game):
        # Special cases that can't be crawled
        if game == "267420": self.games[game] = "Holiday Sale 2013"
        elif game in UNKNOWN_GAMES: self.games[game] = "Unknown"
        else:
            name = find_item(self.re_game, html1, "name", "game " + game)
            if name: self.games[game] = name
            else:
                try:
                    int(game)
                    print "Recrawling later"
                except ValueError:
                    self.games[game] = "Unknown"
                    print "Setting as unknown"


    def run(self):
        print "Really, no need for another Steam crawler"
        health_check = True
        start_time = time.clock()
        queue_time = start_time
        dump_time = start_time - DATA_DUMP_TIME / 2 #first dump faster
        dump_time2 = start_time
        self.session_starttime = start_time
        self.dump_status(1)
        while not self.quit:
            html2_size = 0

            if len(self.games_queue):
                game = self.games_queue.pop()
                print "Crawling game: " + game
                html1 = request_html("game " + game, "http://steamcommunity.com/app/" + game)
                if html1[0]: self.parse_game(html1[2], game)
            else:
                self.current_user = self.queue.pop(0)
                if self.current_user[0] == '-':
                    self.current_user = self.current_user[1:]
                    check_existence = True
                else: check_existence = False
                self.current_url = "http://steamcommunity.com/" + self.current_user

                    #html request
                html1 = request_html(self.current_user, self.current_url)
                if html1[0]: html2_size = self.parse(html1[2], check_existence)

                #stats
            current_time = time.time()
            if len(html1) > 1:
                self.save_times.append(current_time)
                self.save_amounts.append(html1[1] + html2_size)
                self.alltimestats[1]+= 1
                self.alltimestats[2]+= html1[1] + html2_size

                #sleep
            end_time = time.clock()
            elapsed_time = end_time - start_time
            sleep_time = REQUEST_TIME - elapsed_time
            # print time until analysis
            time_until_analysis = DATA_DUMP_TIME - end_time + dump_time
            print "Analyzing in %i:%02i \r" % (time_until_analysis // 60, time_until_analysis % 60),
            # sleep now
            if sleep_time > 0:
                time.sleep(sleep_time)
                start_time = end_time + sleep_time
            else: start_time = end_time

                #performance stats
            if elapsed_time >= ERROR_TIME:
                self.crawls_error+= 1
            else:
                self.crawl_times_sum+= elapsed_time
                self.crawl_times_amount+= 1
                if sleep_time < 0: self.crawls_slow+= 1
                else: self.crawls_fast+= 1

            if health_check:
                print "Crawling succesfully"
                health_check = False

                #data save/dump and backup
            if end_time - dump_time > DATA_DUMP_TIME: #sync
                self.dump_data()
                queue_time = time.clock()
                dump_time = queue_time
                dump_time2 = queue_time
            elif end_time - dump_time2 > STATUS_DUMP_TIME: #status
                self.dump_status()
                dump_time2 = end_time
            elif current_time > self.next_backup: #backup
                self.save_queue()
                self.next_backup = backup_files()
                queue_time = time.clock()
            elif end_time - queue_time > QUEUE_SAVE_TIME: #save
                self.save_queue()
                queue_time = time.clock()

        if self.quit_analyze: self.dump_data()
        else: self.dump_status()
        self.save_queue() #do this last!


    def save_queue(self):
        starttime = time.clock()
        self.update_uptime(starttime)
        save_queue(self.alltimestats, "mem/stats")
        save_queue(self.queue, "mem/queue", queue_to_file)
        save_queue(self.hiscores, "mem/high")
        save_queue(self.save_times, "mem/times")
        save_queue(self.save_amounts, "mem/bytes")
        save_queue(self.bg_images, "mem/backgrounds", bgurl_to_file)
        save_dict(self.games, "mem/games")
        with open("mem/exists", "wb") as f: f.write(self.existlist)
        self.database.save_data()
            #queue size and bg size
        print "  saved (" + str(len(self.bg_images)) + " bg)",
            #http time
        print "(" + str(round(get_req_time() * 2.0, 2)) + " http)",
            #crawling speed
        crawls_sum = self.crawls_fast + self.crawls_slow + self.crawls_error
        print "(" + str(round(self.crawl_times_sum / max(self.crawl_times_amount, 1), 2)) +\
              " " + str(round((starttime - self.session_starttime) / crawls_sum, 2)) +\
              " / " + str(REQUEST_TIME) + ")",
            #fast / slow / error crawls
        crawls_sum/= 100.0
        print "(" + str(int(round(self.crawls_fast / crawls_sum))) + "f",
        print str(int(round(self.crawls_slow / crawls_sum))) + "s",
        print str(int(round(self.crawls_error / crawls_sum))) + "e)",
            #speed of this func
        print get_time_string(starttime)


    def dump_status(self, init = 0):
        starttime = time.clock()
        self.update_uptime(starttime)
            #remove older than hour data
        if len(self.save_times):
            hour_ago = time.time() - 3600
            if self.save_times[-1] < hour_ago:
                self.save_times = []
                self.save_amounts = []
            else:
                i = 0
                while self.save_times[i] < hour_ago: i+= 1
                self.save_times = self.save_times[i:]
                self.save_amounts = self.save_amounts[i:]
            #json data
        keys = ("files", "bytes", "inittime", "total_crawls", "total_bytes", "crawl_age", "uptime")
        values = (len(self.save_times),
                  sum(self.save_amounts),
                  self.alltimestats[0],
                  self.alltimestats[1],
                  self.alltimestats[2],
                  time.time() - self.alltimestats[3],
                  self.alltimestats[4])
        data = get_json(keys, values)
            #rest
        self.request_time = max(int(time.time()), self.request_time + 1)
        _hash = calc_hash(self.request_time)
        print "  " + str(request_html("status dump",
                                      DATA_SAVER,
                                      get_post_values(_hash,
                                                      self.request_time,
                                                      "s",
                                                      data,
                                                      init))[-1]),
        print get_time_string(starttime)


    def dump_data(self):
        self.save_queue()
        #do this first because data dump may take very long time
        #  and the server may start to think that the crawler is not crawling anymore
        self.dump_status()
        #do the analyze and update some values
        self.request_time, recrawl_queue, self.alltimestats[3], new_hiscores, self.alltimestats[5] =\
            self.database.synchronize(self.request_time, self.bg_images, self.games, self.alltimestats[5], self.existlist)
        #hi-score change
        hiscore_changed = False
        for i in range(len(self.hiscores)):
            if self.hiscores[i] != new_hiscores[i]:
                hiscore_changed = True
                print "hi-score '" + self.item_names[i] + "' changed: " +\
                      str(self.hiscores[i]) + " -> " + str(new_hiscores[i])
                self.hiscores[i] = new_hiscores[i]
        if hiscore_changed: print
        #recrawl
        recrawl_len = len(recrawl_queue)
        if recrawl_len:
            if recrawl_len >= len(self.queue): self.queue = recrawl_queue
            else: self.queue = recrawl_queue + self.queue[recrawl_len:]
        print "Length of queue: " + str(len(self.queue)) + "\n"
