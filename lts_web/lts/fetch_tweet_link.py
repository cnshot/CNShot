#!/usr/bin/python

from __future__ import with_statement

import os, md5, re, uuid, sys, pickle, memcache, time, rfc822, \
    logging, logging.config, twitter_utils, threading, traceback
# import twitter
import tweepy

from optparse import OptionParser
from stompy.simple import Client
from datetime import timedelta, datetime
from chinese_detecting import isChinesePhase
from config import Config, ConfigMerger, ConfigList

#os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from lts.models import Link, Tweet, TwitterAccount

class TweetLinkFetcher:
    def __init__(self):
        self.mc = memcache.Client(['127.0.0.1:11211'], debug=0)
        self.stomp = Client()
        self.stomp.connect()

    def fetchFriendsTimeline(self, api, count=20, since_id=None, page_size=20,
                             calls_count=1):
        if count<=0 or page_size<=0:
            return []

        statuses = []
        left = count
        last_fetch_count = page_size
        max_id = None
        calls_left = calls_count
        while left > 0 and last_fetch_count > 0 and calls_left > 0:
            logger.debug("Calls left: %d", calls_left)
            n = page_size
            if n>left:
                n=left

            if since_id is None:
                if max_id is None:
                    logger.debug("Fetch status without max or since.")
                    ss = api.friends_timeline(count=page_size,
                                              include_rts=1,
                                              include_entities=1)
                else:
                    logger.debug("Fetch status: max=%d", max_id)
                    ss = api.friends_timeline(count=page_size,
                                              max_id=max_id,
                                              include_rts=1,
                                              include_entities=1)
            else:
                if max_id is None:
                    logger.debug("Fetch status: since=%d", since_id)
                    ss = api.friends_timeline(count=page_size,
                                              since_id=since_id,
                                              include_rts=1,
                                              include_entities=1)
                else:
                    logger.debug("Fetch status: since_id=%d, max_id=%d",
                                 since_id, max_id)
                    ss = api.friends_timeline(count=page_size,
                                              max_id=max_id,
                                              since_id=since_id,
                                              include_rts=1,
                                              include_entities=1)
            calls_left -= 1

            last_fetch_count = len(ss)
            left -= last_fetch_count
            if(last_fetch_count > 0):
                logger.debug("Fetched status: %d - %d", ss[-1].id, ss[0].id)
                max_id = ss[-1].id - 1
                statuses += ss

        return statuses

    def processStatus(self, s, screen_names=[]):
        # mc = memcache.Client(['127.0.0.1:11211'], debug=0)
        # stomp = Client()
        # stomp.connect()

        url_pattern = re.compile('((http|ftp|https):\/\/[\w\-_]+(\.[\w\-_]+)+([\w\-\.,@?^=%&amp;:/~\+#]*[\w\-\@?^=%&amp;/~\+#])?)')
        if s.user.screen_name in screen_names :
            # don't RT myself
            return
        if not isChinesePhase(s.text.encode("utf-8", "ignore")):
            # Chinese tweet only
            # print "Skip none Chinese tweet: %s" % s.text
            return

        if s.retweet_count is not None:
            logger.debug("Tweet with retweet count: %d %s %s %d %s",
                         s.id, s.user.screen_name, str(s.created_at),
                         s.retweet_count, s.text.encode('utf-8'))

        # update Tweet
        t = Tweet(id = s.id,
                  text = s.text,
                  #                      created_at = datetime.fromtimestamp(time.mktime(rfc822.parsedate(s.created_at))),
                  created_at = s.created_at,
                  user_screenname = s.user.screen_name)
        t.save()

        matches = re.findall(url_pattern,s.text)
        if matches:
            logger.debug("Tweet with link(s): %d %s %s %s",
                         s.id, s.user.screen_name,
                         str(s.created_at), s.text.encode('utf-8'))

            ls = []

            for m in matches:
                task_id = str(uuid.uuid1())
                self.mc.set(task_id, s, time=cfg.fetch_tweet_link.status_timeout)

                # update Tweet and Link
                try:
                    l = Link.objects.get(url__exact=m[0])
                except Link.DoesNotExist:
                    l = Link(url=m[0])
                    l.save()

                # NOTICE: l record may be updated by url_processor after stomp.put
                ls.append(l)

                self.stomp.put(pickle.dumps({'id':task_id,
                                        'url':m[0],
                                        'filename':None}),
                          destination=cfg.queues.fetched)

            # # update Tweet
            # t = Tweet(id = s.id,
            #           text = s.text,
            #           #                      created_at = datetime.fromtimestamp(time.mktime(rfc822.parsedate(s.created_at))),
            #           created_at = s.created_at,
            #           user_screenname = s.user.screen_name)
            # t.save()
            t.links = map(lambda x: x.id, ls)
            t.save()

    def fetchTweetLinkAll(self):
        active_accounts = TwitterAccount.active_accounts()

        logger.debug("Got %d active accounts", len(active_accounts))

        account_screen_names = []
        for account in active_accounts:
            account_screen_names.append(account.screen_name)

        for account in active_accounts:
            logger.debug("Fetching tweet links of account: %s", account.screen_name)
            api = twitter_utils.createApi(account=account)

            if account.since is None or account.since == '':
                statuses = self.fetchFriendsTimeline(api,
                                                count=cfg.fetch_tweet_link.count,
                                                page_size=cfg.fetch_tweet_link.page_size,
                                                calls_count=cfg.fetch_tweet_link.calls_count)
            else:
                statuses = self.fetchFriendsTimeline(api,
                                                count=cfg.fetch_tweet_link.count,
                                                page_size=cfg.fetch_tweet_link.page_size,
                                                since_id=int(account.since),
                                                calls_count=cfg.fetch_tweet_link.calls_count)

            for s in statuses:
                try:
                    self.processStatus(s, account_screen_names)
                except:
                    logger.error("Failed to process status: %s", sys.exc_info()[0])
                    logger.error('-'*60)
                    logger.error("%s", traceback.format_exc())
                    logger.error('-'*60)
                    continue

            if statuses and len(statuses)>0:
                account.since=str(statuses[0].id)
                logger.debug("Update since of account %s: %s",
                             account.screen_name, account.since)
                account.save()

def run(_cfg, _logger):
    global cfg, logger
    cfg = _cfg
    logger = _logger

    fetcher = TweetLinkFetcher()
    fetcher.fetchTweetLinkAll()    

if __name__ == '__main__':
    description = '''Fetch Twitter timeline and enqueue links.'''
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1, Copyright (c) 2010 Chinese Shot",
                          description=description)

    parser.add_option("-s", "--since", dest="since", type="int",
                      help="Fetch updates after tweet id. Default for last 20 tweets.",
                      metavar="SINCE")

    parser.add_option("-c", "--config",
                      dest="config",
                      default="lts.cfg",
                      type="string",
                      help="Config file [default %default].",
                      metavar="CONFIG")

    (options,args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments") 

    cfg=Config(file(filter(lambda x: os.path.isfile(x),
                           [options.config,
                            os.path.expanduser('~/.lts.cfg'),
                            '/etc/lts.cfg'])[0]))

    # cmd_cfg=Config(file('lts_cmd.cfg'))
    cfg.addNamespace(options, 'cmdline')

    # walk around encoding issue
    reload(sys)
    sys.setdefaultencoding('utf-8') 
    # locale.setlocale(locale.LC_ALL, 'C')

    logging.config.fileConfig(cfg.common.log_config)
    logger = logging.getLogger("fetch_tweet_link")

    if(cfg.fetch_tweet_link.lifetime):
        threading.Timer(cfg.fetch_tweet_link.lifetime, os._exit, [1]).start()

    fetcher = TweetLinkFetcher()
    fetcher.fetchTweetLinkAll()
    os._exit(0)
