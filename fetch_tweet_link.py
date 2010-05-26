#!/usr/bin/python

from __future__ import with_statement

import os, md5, re, uuid, sys, pickle, memcache, time, rfc822, \
    logging, logging.config
# import twitter
import tweepy

from optparse import OptionParser
from stompy.simple import Client
from datetime import timedelta, datetime
from chinese_detecting import isChinesePhase
from config import Config, ConfigMerger, ConfigList

#os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from lts.models import Link, Tweet

def fetchFriendsTimeline(api, count=20, since_id=None, page_size=20):
    if count<=0 or page_size<=0:
        return []

    statuses = []
    left = count
    last_fetch_count = page_size
    max_id = None
    while left > 0 and last_fetch_count > 0:
        n = page_size
        if n>left:
            n=left

        if since_id is None:
            if max_id is None:
                logger.debug("Fetch status without max or since.")
                ss = api.friends_timeline(count=page_size)
            else:
                logger.debug("Fetch status: max=%d", max_id)
                ss = api.friends_timeline(count=page_size, max_id=max_id)
        else:
            if max_id is None:
                logger.debug("Fetch status: since=%d", since_id)
                ss = api.friends_timeline(count=page_size, since_id=since_id)
            else:
                logger.debug("Fetch status: since_id=%d, max_id=%d",
                             since_id, max_id)
                ss = api.friends_timeline(count=page_size,
                                          max_id=max_id,
                                          since_id=since_id)
        last_fetch_count = len(ss)
        left -= last_fetch_count
        if(last_fetch_count > 0):
            logger.debug("Fetched status: %d - %d", ss[-1].id, ss[0].id)
            max_id = ss[-1].id - 1
            statuses += ss

    return statuses

def fetchTweetLink():
    url_pattern = re.compile('((http|ftp|https):\/\/[\w\-_]+(\.[\w\-_]+)+([\w\-\.,@?^=%&amp;:/~\+#]*[\w\-\@?^=%&amp;/~\+#])?)')
    stomp = Client()
    stomp.connect()
    mc = memcache.Client(['127.0.0.1:11211'], debug=0)

    try:
        cfg.fetch_tweet_link.since
    except AttributeError:
        cfg.fetch_tweet_link.since = None

    if cfg.fetch_tweet_link.since_file and ( not cfg.fetch_tweet_link.since ):
        try:
            with open(cfg.fetch_tweet_link.since_file, 'r') as f:
                try:
                    cfg.fetch_tweet_link.since=int(f.read())
                except:
                    cfg.fetch_tweet_link.since=None
        except:
            pass

    # api = twitter.Api(username=cfg.common.username,
    #                   password=cfg.common.password)
    auth = tweepy.BasicAuthHandler(cfg.common.username, cfg.common.password)
    api = tweepy.API(auth,
                     host=cfg.common.api_host,
                     search_host=cfg.common.search_host,
                     api_root=cfg.common.api_root,
                     search_root=cfg.common.search_root)

    if cfg.fetch_tweet_link.since:
        logger.info("Since: %d", cfg.fetch_tweet_link.since)
        # statuses = api.GetFriendsTimeline(cfg.common.username,
        #                                   count=cfg.fetch_tweet_link.count,
        #                                   since_id=cfg.fetch_tweet_link.since)
        statuses = fetchFriendsTimeline(api,
                                        count=cfg.fetch_tweet_link.count,
                                        page_size=cfg.fetch_tweet_link.page_size,
                                        since_id=cfg.fetch_tweet_link.since)
    else:
        statuses = fetchFriendsTimeline(api,
                                        count=cfg.fetch_tweet_link.count,
                                        page_size=cfg.fetch_tweet_link.page_size)

    for s in statuses:
        if s.user.screen_name == cfg.common.username :
            # don't RT myself
            continue
        if not isChinesePhase(s.text.encode("utf-8", "ignore")):
            # Chinese tweet only
            # print "Skip none Chinese tweet: %s" % s.text
            continue
        matches = re.findall(url_pattern,s.text)
        if matches:
            logger.debug("Tweet with link(s): %d %s %s %s",
                         s.id, s.user.screen_name,
                         str(s.created_at), s.text.encode('utf-8'))

            ls = []

            for m in matches:
                task_id = str(uuid.uuid1())
                mc.set(task_id, s, time=cfg.fetch_tweet_link.status_timeout)

                # update Tweet and Link
                try:
                    l = Link.objects.get(url__exact=m[0])
                except Link.DoesNotExist:
                    l = Link(url=m[0])
                    l.save()

                # NOTICE: l record may be updated by url_processor after stomp.put
                ls.append(l)
                
                stomp.put(pickle.dumps({'id':task_id,
                                        'url':m[0],
                                        'filename':None}),
                          destination=cfg.queues.fetched)

            # update Tweet
            t = Tweet(id = s.id,
                      text = s.text,
#                      created_at = datetime.fromtimestamp(time.mktime(rfc822.parsedate(s.created_at))),
                      created_at = s.created_at,
                      user_screenname = s.user.screen_name)
            t.save()
            t.links = map(lambda x: x.id, ls)
            t.save()
                
    if statuses:
        logger.info("Latest status ID: %d", statuses[0].id)
        if cfg.fetch_tweet_link.since_file:
            try:
                with open(cfg.fetch_tweet_link.since_file, 'w') as f:
                    f.write(str(statuses[0].id))
            except:
                pass    

if __name__ == '__main__':
    description = '''Fetch Twitter timeline and enqueue links.'''
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1, Copyright (c) 2010 Chinese Shot",
                          description=description)

    parser.add_option("-s", "--since", dest="since", type="int",
                      help="Fetch updates after tweet id. Default for last 20 tweets.",
                      metavar="SINCE")

    # parser.add_option("-d", "--dest-queue", 
    #                   dest="dest_queue", default="/queue/url_processor",
    #                   type="string",
    #                   help="Dest message queue path [default: %default].",
    #                   metavar="DEST_QUEUE")

    # parser.add_option("-c", "--count", dest="count", type="int", default=20,
    #                   help="Fetch at most COUNT tweets [default: %default].",
    #                   metavar="COUNT")

    # parser.add_option("-f", "--since-file", dest="since_file", type="string",
    #                   default="/var/run/fetch_tweet_link.since",
    #                   help="Status ID file to read/write [default: %default].",
    #                   metavar="SINCE_FILE")

    # parser.add_option("-u", "--username", dest="username", type="string",
#                      default="username",
                      # help="Twitter username [default: %default].",
                      # metavar="USERNAME")

    # parser.add_option("-p", "--password", dest="password", type="string",
#                      default="password",
    #                   help="Twitter password [default: %default].",
    #                   metavar="PASSWORD")

    # parser.add_option("-l", "--log-config",
                      # dest="log_config", 
#                      default="/etc/link_shot_tweet_log.conf",
                      # type="string",
                      # help="Logging config file [default: %default].",
                      # metavar="LOG_CONFIG")

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

    # print(cfg)
    # print(cmd_cfg)
    # print(options)

    # walk around encoding issue
    reload(sys)
    sys.setdefaultencoding('utf-8') 
    # locale.setlocale(locale.LC_ALL, 'C')

    logging.config.fileConfig(cfg.common.log_config)
    logger = logging.getLogger("fetch_tweet_link")

    fetchTweetLink()
