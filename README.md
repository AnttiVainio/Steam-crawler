# Steam crawler

First, do consider that you should not run your own instance of the Steam crawler because there is already one being run and it doesn't give any benefit to run more instances. This code is here only for people to learn stuff.

Steam crawler is a web crawler with a goal to crawl Steam users' profiles in the Steam community and gather some data from them. This data is then analyzed and shown on the website of the one and only [Steam crawler](http://www.anttivainio.net/steambot). Visiting that website is also a good way of learning what kind of data the Steam crawler is collecting.

Steam crawler works just like any other web crawler like Google Bot or Bing Bot because it essentially is one. Steam crawler acquires its data by sending http-requests and analyzing the received html-data. Because of this, Steam crawler can only see exactly what every other crawler or human browsing the Steam community can see while not logged into Steam.

The crawler itself is a Python program but it also expects a web server to exist to which it sends the collected and analyzed data using http post-requests.

If you still feel the strongest desire to run Steam crawler even though you shouldn't, at least edit the settings and create some web sever to receive the data sent by the crawler.
