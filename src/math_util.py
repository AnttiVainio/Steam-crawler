import math
from operator import itemgetter

#self.median and self.mean will corrupt if add is called after calling get_median or get_mean
#as a result get_mean_deviation and get_relative_deviation will give wrong answers
class countmean:
    def __init__(self):
        self.n = {}
        self.sum = 0
        self.count = 0
        self.median = None
        self.mean = None

    def add(self, num):
        try: self.n[num]+= 1
        except KeyError: self.n[num] = 1
        self.sum+= num
        self.count+= 1

    #returns the high median
    def get_median(self):
        s = sorted(self.n.items(), key = itemgetter(0))
        start = 0
        startamount = s[start][1]
        end = len(s) - 1
        endamount = s[end][1]
        while start < end:
            amount = min(startamount, endamount)
            startamount-= amount
            endamount-= amount
            if(startamount == 0):
                start+= 1
                startamount = s[start][1]
            if(endamount == 0):
                end-= 1
                endamount = s[end][1]
        self.median = s[start][0]
        return self.median

    def get_mean(self):
        self.mean = float(self.sum) / float(self.count)
        return self.mean

    #returns the mean deviation about median
    def get_mean_deviation(self):
        if self.median == None: get_median()
        return float(sum(abs(i - self.median) * self.n[i] for i in self.n)) / float(self.count)

    #returns the relative standard deviation
    def get_relative_deviation(self):
        if self.mean == None: get_mean()
        return 100.0 * math.sqrt(float(sum((i - self.mean) ** 2 * self.n[i] for i in self.n)) / float(self.count)) / self.mean
