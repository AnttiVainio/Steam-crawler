# Steam crawler

Steam crawler is a web crawler with a goal to crawl Steam users' profiles in the Steam community and gather some data from them. This data is then analyzed and shown on the [Steam crawler website](https://www.anttivainio.net/steambot). However, the project is no longer active and the original crawler is not being run to gather new data anymore.

Steam crawler works just like any other web crawler like Google Bot or Bing Bot because it essentially is one. Steam crawler acquires its data by sending HTTPS-requests and analyzing the received HTML-data. Because of this, Steam crawler can only see exactly what every other crawler or human browsing the Steam community can see while not logged into Steam.

The crawler itself is a Python program but it also expects an existing web server, to which it sends the collected and analyzed data using HTTPS POST-requests. It is still possible to run the Steam crawler without a web server but then the crawler will occasionally print some HTTP-errors and you won't get the analyzed data. The raw unanalyzed data is also saved into files.
