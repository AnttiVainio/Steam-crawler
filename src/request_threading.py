import threading
import time

from settings import *
from request import request_html

class Request_sender(threading.Thread):
    def __init__(self, handler):
        super(Request_sender, self).__init__()
        self.handler = handler
        self.stop = False

    def run(self):
        while not self.stop:
            with self.handler.queue_lock:
                if len(self.handler.queue) == 0:
                    current_user = None
                else:
                    current_user = self.handler.queue.pop(0)
            if not current_user:
                time.sleep(1)
            else:
                if current_user[0] == '-':
                    current_user = current_user[1:]
                    check_existence = True
                else: check_existence = False
                current_url = "https://steamcommunity.com/" + current_user

                    #html request
                html = (current_user,
                        check_existence,
                        request_html(current_user, current_url),
                        request_html(current_user + "/ajaxaliases", current_url + "/ajaxaliases"),
                        )
                with self.handler.html_lock:
                    self.handler.htmls.append(html)

class Request_handler():
    def __init__(self, queue):
        self.queue = queue
        self.threads = []
        self.htmls = []
        self.queue_lock = threading.Lock()
        self.html_lock = threading.Lock()

    def start(self):
        for i in range(REQUEST_THREADS):
            self.threads.append(Request_sender(self))
            self.threads[-1].start()

    def stop(self):
        for i in self.threads:
            i.stop = True
        for i in self.threads:
            i.join()
        self.threads = []

    def get_html(self):
        with self.html_lock:
            if len(self.htmls) == 0: return -1
            return self.htmls.pop(0)

    def done(self):
        with self.html_lock:
            return len(self.htmls) == 0 and len(self.threads) == 0
