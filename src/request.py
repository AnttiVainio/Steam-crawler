import time
import urllib2, httplib, socket

from settings import *
from util import Progress

request_time = 0.0
request_amount = 0.0

def get_req_time():
    return request_time / max(request_amount, 1.0)

def wait_error():
    progress = Progress(20)
    for i in range(21):
        if i: progress.increment()
        time.sleep(ERROR_TIME / 21.0)
    progress.done()

def handle_httperror(error, e, first):
    print "HTTPError for " + error + " (" + str(e.code) + ") (" + ("1st)" if first else "2nd)")
    #print e.read()
    read_len = sum(len(i) for i in e.info().headers)
    e.close()
    wait_error()
    return read_len

def handle_urlerror(error, e, first):
    reason = " " + str(e.reason)
    print "URLError for " + error + " (" + ("1st)" if first else "2nd)")
    print (reason[:76] + "...") if len(reason) > 79 else reason
    if not "timed out" in reason: wait_error()

def handle_badstatusline(error, first):
    print "BadStatusLine for " + error + " (" + ("1st)" if first else "2nd)")
    wait_error()

def handle_timeout(error, first):
    print "Timeout for " + error + " (" + ("1st)" if first else "2nd)")

def request_html(error, address, values = None):
    starttime = time.clock()
    read_len = 0
    try:
        #values not needed after the following line so it is used to determine if time is saved
        request = urllib2.Request(address, values, {"User-Agent":USER_AGENT,"Accept-Language":LANG})
        exception = True
        try:
            website = urllib2.urlopen(request, timeout = TIMEOUT)
            exception = False
        #retry here
        except urllib2.HTTPError as e:
            read_len+= handle_httperror(error, e, True)
        except urllib2.URLError as e:
            handle_urlerror(error, e, True)
        except httplib.BadStatusLine:
            handle_badstatusline(error, True)
        except socket.timeout:
            handle_timeout(error, True)
        if exception:
            website = urllib2.urlopen(request, timeout = TIMEOUT)
            values = True #don't record time
        html = website.read()
        read_len+= len(html) + sum(len(i) for i in website.info().headers)
        website.close()
        if not values:
            global request_time
            global request_amount
            request_amount+= 1.0
            request_time+= time.clock() - starttime
        return (True, read_len, html)
    except urllib2.HTTPError as e:
        read_len+= handle_httperror(error, e, False)
        return (False, read_len)
    except urllib2.URLError as e:
        handle_urlerror(error, e, False)
        return [False]
    except httplib.BadStatusLine:
        handle_badstatusline(error, False)
        return [False]
    except socket.timeout:
        handle_timeout(error, False)
        return [False]
    except Exception as e:
        print "Exception while requesting html for " + error + ":"
        print " " + str(type(e)) + ": " + str(e)
        wait_error()
        return [False]
