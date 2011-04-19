#!/usr/bin/python

import logging.config, os, time, rfc822, tweepy, Queue, twitter_utils

from threading import Thread
from datetime import timedelta, datetime
from optparse import OptionParser
from urllib2 import HTTPError
from config import Config
from tweepy.error import TweepError
from httplib import IncompleteRead

from lts.models import Tweet, LinkShot, LinkRate, ShotPublish, TwitterApiSite

class LinkRatingThread(Thread):
    def __init__(self, id, input_queue):
        Thread.__init__(self)
        self.id = id
        self.input_queue = input_queue

    def run(self):
        logger.info("Link rating thread %s started.", str(self.id))

        while not self.input_queue.empty():
            try:
                task = self.input_queue.get(block=False)
            except Queue.Empty:
                break

            # rate task['links']
            rate_sum = 0
            for l in task['links']:
                # save time before the HTTP request
                now = datetime.utcnow()
            
                r = self.rate_link(l, now)
                # update output
                try:
                    lr = LinkRate.objects.get(link=l)
                    logger.debug("Got existing LinkRate: %s", lr)
                except LinkRate.DoesNotExist:
                    lr = LinkRate(link=l)
                    logger.debug("Created LinkRate: %s", lr)
                except LinkRate.MultipleObjectsReturned:
                    logger.debug("Delete duplicated LinkRate: %s", lr)
                    LinkRate.objects.filter(link=l).delete()
                    lr = LinkRate(link=l)
                    logger.debug("Created LinkRate: %s", lr)

                if lr.rate is None or lr.rate < r:
                    lr.rate = r
                    lr.rating_time = now

                    lr.save()
                    logger.debug("Updated LinkRate: %s [%d]", lr, r)

                rate_sum += r

    def rate_link(self, url, now):
        # api = twitter.Api(username=cfg.common.username,
        #                   password=cfg.common.password)
        # api = twitter.Api()
        # auth = tweepy.BasicAuthHandler(cfg.common.username, cfg.common.password)
        auth = None

#        api_site = TwitterApiSite.random()
#        logger.debug("Rate with API site: %s", api_site)
#
#        if api_site is not None:
#            api = tweepy.API(auth_handler=auth,
#                             host=api_site.api_host,
#                             search_host=api_site.search_host,
#                             api_root=api_site.api_root,
#                             search_root=api_site.search_root,
#                             secure=api_site.secure_api)
#        else:
#            api = tweepy.API(auth_handler=auth,
#                             host=cfg.common.api_host,
#                             search_host=cfg.common.search_host,
#                             api_root=cfg.common.api_root,
#                             search_root=cfg.common.search_root,
#                             secure=cfg.common.secure_api)
        api = twitter_utils.createApi()

        try:
            # s = api.GetSearch(url, lang='', per_page=cfg.link_rating.max_ranking_tweets)
            s = api.search(q=url, lang='',rpp=cfg.link_rating.max_ranking_tweets)
        except (HTTPError, ValueError, TweepError, NameError, KeyError, IncompleteRead):
            logger.warn("Failed to call search API: %s", url)
            return 0
        
        tt = now - timedelta(seconds = cfg.link_rating.ranking_time)
        # filted_s = filter(lambda x: True if (datetime.fromtimestamp(time.mktime(rfc822.parsedate(x.created_at))) > tt) else False, s)
        filted_s = filter(lambda x: True if (x.created_at > tt) else False, s)

#        for i in range(len(s)):
#            logger.debug("%s", s[i].created_at)
#            t = datetime.fromtimestamp(time.mktime(rfc822.parsedate(s[i].created_at)))
#            if t < tt:
#                break

#        i+=1
        i = len(filted_s)
        if i < len(s) or len(s) < cfg.link_rating.max_ranking_tweets:
            return i

        try:
            t = datetime.fromtimestamp(time.mktime(rfc822.parsedate(str(s[-1].created_at))))
        except TypeError:
            logger.warn("Failed to get create time of tweet, use thredshold instead: %d",
                        s[-1].id)
            t = tt
            
        logger.debug("Estimating rate: t=%s tt=%s delta=%s",
                     str(t), str(tt), str(t-tt))

        if cfg.link_rating.ranking_time < (t-tt).seconds:
            logger.warn("Ranking time is less than t_delta: %s", str(cfg.link_rating.ranking_time))
            return cfg.link_rating.max_ranking_tweets

        td = cfg.link_rating.ranking_time - (t-tt).seconds
        return float(cfg.link_rating.max_ranking_tweets) / td * cfg.link_rating.ranking_time
        
class TaskProcessor:
    @classmethod
    def loadTasks(cls, queue):
        # get links shotted in last 2 hours
        lss = LinkShot.objects.filter(shot_time__gte=datetime.utcnow()-timedelta(seconds=cfg.link_rating.ranking_time))

        for ls in lss:
            # if it's published, not more rate
            published = ShotPublish.objects.filter(link = ls.link)
            if len(published) > 0:
                logger.debug("Skip published link: %s", ls.link.url)
                continue

            # get existing rate
#            lrs = LinkRate.objects.filter(link = ls.link)

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
#            if len(lrs)>0 and latest_tweet_time < lrs[0].rating_time:
#                logger.debug("Original rating is functional. Skip rating: %s",
#                             ls.link.url)
#                continue

            # enqueue for ratings
            queue.put({'linkshot':ls, 'links':links})

def run_search(_cfg, _logger):
    global cfg, logger
    cfg = _cfg
    logger = _logger

    q=Queue.Queue()

    # read recent tweet links from DB
    #   filter out: a) tweeted links, b) links rated in last x mins
    TaskProcessor.loadTasks(q)

    # feed links to input queue
    # start rating threads
    # wait for rating threads exit
    workers = []
    for i in range(cfg.link_rating.workers):
        w = LinkRatingThread(i, q)
        w.start()
        workers.append(w)

    for i in range(cfg.link_rating.workers):
        workers[i].join()

def run_count(cfg, logger):
    now = datetime.utcnow()
    
    lss = LinkShot.objects.filter(shot_time__gte = now - timedelta(seconds=cfg.link_rating.ranking_time))
    tt = now - timedelta(seconds = cfg.link_rating.ranking_time)
    
    for ls in lss:
        links=ls.link.getRoot().getAliases()

#        first_created_at = datetime.utcnow() 
        for l in links:
            ts = Tweet.objects.filter(links=l).filter(created_at__gt=tt).order_by('created_at')
            r = ts.count()
#            if ts[0].created_at < first_created_at:
#                first_created_at = ts[0].created_at

            if r == 0:
                continue

            try:
                lr = LinkRate.objects.get(link=l)
#                logger.debug("Got existing LinkRate: %s", lr)
            except LinkRate.DoesNotExist:
                lr = LinkRate(link=l)
                logger.debug("Created LinkRate: %s", lr)
            except LinkRate.MultipleObjectsReturned:
                logger.debug("Delete duplicated LinkRate: %s", lr)
                LinkRate.objects.filter(link=l).delete()
                lr = LinkRate(link=l)
                logger.debug("Created LinkRate: %s", lr)                

            if lr.rate is None or lr.rate < r:
                lr.rate = r
                lr.rating_time = now

                lr.save()
                logger.debug("Updated LinkRate: %s [%d]", lr, r)    

def run(_cfg, _logger):
    run_count(_cfg, _logger)