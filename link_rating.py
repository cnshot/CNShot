#!/usr/bin/python

import stompy, sys, traceback, logging, logging.config, os, time, rfc822
import twitter

from Queue import Queue
from threading import Thread
from datetime import timedelta, datetime
from optparse import OptionParser

# hacks for loading Django models
#d=os.path.dirname(__file__)
#sys.path.append('lts_web' if d == '' else (d+"/lts_web"))
#os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from lts.models import Link, Tweet, LinkShot, LinkRate, ShotPublish

class LinkRatingThread(Thread):
    def __init__(self, id, input_queue):
        Thread.__init__(self)
        self.id = id
#        self.options = options
        self.input_queue = input_queue
#        self.logger = logger

    def run(self):
        logger.info("Link rating thread %s started.", str(self.id))

        while not self.input_queue.empty():
            try:
                task = self.input_queue.get(block=False)
            except Thread.Empty:
                break

            # rate task['links']
            rate_sum = 0
            for l in task['links']:
                # save time before the HTTP request
                now = datetime.now()
            
                r = self.rate_link(l, now)
                # update output
                try:
                    lr = LinkRate.objects.get(link=l)
                    logger.debug("Got existing LinkRate: %s", lr)
                except LinkRate.DoesNotExist:
                    lr = LinkRate(link=l)
                    logger.debug("Created LinkRate: %s", lr)

                lr.rate = r
                lr.rating_time = now

                lr.save()

                rate_sum += r

    def rate_link(self, url, now):
        api = twitter.Api(username=options.username,
                          password=options.password)
#        api = twitter.Api()
        s = api.GetSearch(url, lang='', per_page=options.max_ranking_tweets)
        
        tt = now - timedelta(seconds = options.ranking_time)
        filted_s = filter(lambda x: True if (datetime.fromtimestamp(time.mktime(rfc822.parsedate(x.created_at))) > tt) else False, s)

#        for i in range(len(s)):
#            logger.debug("%s", s[i].created_at)
#            t = datetime.fromtimestamp(time.mktime(rfc822.parsedate(s[i].created_at)))
#            if t < tt:
#                break

#        i+=1
        i = len(filted_s)
        if i < len(s) or len(s) < options.max_ranking_tweets:
            return i

        t = datetime.fromtimestamp(time.mktime(rfc822.parsedate(s[-1].created_at)))
        td = options.ranking_time - (t-tt).seconds
        return float(options.max_ranking_tweets) / td * options.ranking_time
        
class TaskProcessor:
    @classmethod
    def loadTasks(cls, queue):
        # get links shotted in last 2 hours
        lss = LinkShot.objects.filter(shot_time__gte=datetime.now()-timedelta(hours=2))

        for ls in lss:
            # if it's published, not more rate
            published = ShotPublish.objects.filter(link = ls.link)
            if len(published) > 0:
                logger.debug("Skip published link: %s", link.url)
                continue

            # get existing rate
            lrs = LinkRate.objects.filter(link = ls.link)

            # get link and link alias
            links=ls.link.getRoot().getAliases()

            # get tweets related to the links
            latest_tweet_time = datetime.fromtimestamp(0)
            for l in links:
                logger.debug("Get tweets of link: %s", l)
                try:
                    latest_tweet = Tweet.objects.filter(links = ls.link).order_by('-created_at')[0]
                    if latest_tweet.created_at > latest_tweet_time:
                        latest_tweet_time = latest_tweet.created_at
                except IndexError:
                    continue

            # if there's a new tweet after last rating, rate it
            if len(lrs)>0 and latest_tweet_time < lrs[0].rating_time:
                logger.debug("Original rating is functional. Skip rating: %s",
                             ls.link.url)
                continue

            # enqueue for ratings
            queue.put({'linkshot':ls, 'links':links})

if __name__ == '__main__':
    description = '''Link rating processor.'''
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1, Copyright (c) 2010 Chinese Shot",
                          description=description)

#    parser.add_option("-s", "--source-queue",
#                      dest="source_queue", default="/queue/url_processor",
#                      type="string",
#                      help="Source message queue path [default: %default].",
#                      metavar="SOURCE_QUEUE")

#    parser.add_option("-d", "--dest-queue", 
#                      dest="dest_queue", default="/queue/shot_dest",
#                      type="string",
#                      help="Dest message queue path [default: %default].",
#                      metavar="DEST_QUEUE")

    parser.add_option("-t", "--timeout", 
                      dest="timeout", default=20, type="int",
                      help="Timeout of HTTP request in second [default: %default].",
                      metavar="TIMEOUT")

    parser.add_option("-n", "--workers", 
                      dest="workers", default=8, type="int",
                      help="Number or worker threads [default: %default].",
                      metavar="WORKERS")

    parser.add_option("-l", "--log-config",
                      dest="log_config", 
                      default="/etc/link_shot_tweet_log.conf",
                      type="string",
                      help="Logging config file [default: %default].",
                      metavar="LOG_CONFIG")

    parser.add_option("-r", "--ranking-time",
                      dest="ranking_time", default="7200", type="int",
                      help="Time perioud of link ranking in second [default: %default].",
                      metavar="RANKING_TIME")

    parser.add_option("-m", "--max-ranking-tweets",
                      dest="max_ranking_tweets", default="100", type="int",
                      help="Max tweet numbers to search for every link [default: %default].",
                      metavar="MAX_RANKING_TWEETS")

    parser.add_option("-u", "--username", dest="username", type="string",
                      default="username",
                      help="Twitter username [default: %default].",
                      metavar="USERNAME")

    parser.add_option("-p", "--password", dest="password", type="string",
                      default="password",
                      help="Twitter password [default: %default].",
                      metavar="PASSWORD")

    (options,args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments") 

    logging.config.fileConfig(options.log_config)
    logger = logging.getLogger("link_rating")
                      
    q=Queue()

    # read recent tweet links from DB
    #   filter out: a) tweeted links, b) links rated in last x mins
    TaskProcessor.loadTasks(q)

    # feed links to input queue
    # start rating threads
    # wait for rating threads exit
    workers = []
    for i in range(options.workers):
        w = LinkRatingThread(i, q)
        w.start()
        workers.append(w)

    for i in range(options.workers):
        workers[i].join()
