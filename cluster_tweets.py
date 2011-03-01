#!/usr/bin/python

import sys, logging, logging.config, os, scipy, tweepy
import word_freq, twitter_utils

from optparse import OptionParser
from config import Config, ConfigMerger
from datetime import timedelta, datetime
from lts.models import Tweet, RTPublish, TweetFreqHashCache

def cluster_tweets():
    tt = datetime.utcnow() - timedelta(seconds = cfg.cluster_tweets.time_limit)
    
    logger.debug("Clutering tweets after: %s", tt)

    tweets = Tweet.objects.filter(created_at__gt=tt)
    
    logger.debug("Got %d tweets to cluster.", tweets.count())

    word_freq.logger = logger

    ts = []
    rs = []
    
    for t in tweets:
        ts.insert(0, t)
        rs.insert(0, word_freq.str2freqhash(t.text.encode('utf8')))

    clusters = word_freq.vcluster_with_sample(rs,
                                              cluster_sim_threshold=cfg.cluster_tweets.similarity_threshold,
                                              vcluster_cmd=cfg.cluster_tweets.vcluster_cmd)

    for (s, c, r) in clusters:
        logger.debug("")
        logger.debug("%s %s", s, str(r))
        logger.debug("%s [%s] %s",
                      ts[c].user_screenname,
                      str(ts[c].created_at),
                      ts[c].text)
        logger.debug('----')
        for i in r:
            logger.debug("%s [%s] %s",
                          ts[i].user_screenname,
                          str(ts[i].created_at),
                          ts[i].text)

    if len(clusters) <= 0:
        logger.warn("No valid cluster found.")
        sys.exit(0)

    tt = datetime.utcnow() - timedelta(seconds = cfg.cluster_tweets.duplicated_check_time)
    logger.debug("Getting RTs after: %s", tt)
    rts = RTPublish.objects.filter(created_at__gt=tt)
    logger.debug("Got %d RTs.", rts.count())

    rt_ts = []
    rt_rs = []
    for rt in rts:
        rt_ts.append(rt)
        rt_rs.append(word_freq.str2freqhash(rt.text.encode('utf8')))

    ratings = map(lambda x: len(x[2]), clusters)
    cluster_rs = map(lambda x: rs[x[1]], clusters)

    if len(cluster_rs) and len(rt_rs) > 0:
        logger.debug("%s", cluster_rs)
        logger.debug("%s", rt_rs)
        similarity_matrix = word_freq.hash_filter_knowns(scipy.array(cluster_rs),
                                                         scipy.array(rt_rs),
                                                         similarity_threshold=cfg.cluster_tweets.similarity_threshold)

        logger.debug("%s", str(similarity_matrix))

        for i in range(len(ratings)):
            if similarity_matrix[i]:
                ratings[i] = 0

        logger.debug("%s", str(ratings))

    # logger.debug("%s", str(clusters))
    i = scipy.array(ratings).argmax()
    logger.debug("%d", i)
    if ratings[i] == 0:
        logging.warn("No tweet to RT.")
    else:
        # logger.debug("%s", i)
        t = ts[clusters[i][1]]
        logger.debug("Tweet to RT: %s [%s] %s",
                     t.user_screenname,
                     str(t.created_at),
                     t.text)

        try:
            api = twitter_utils.createCfgApi(cfg.cluster_tweets)

            rts = api.retweet(id = t.id)
            
            logger.info("New tweet: %d %s %s", 
                        rts.id, rts.created_at,
                        rts.text)
 
            if hasattr(rts, 'error'):
                logger.warn("Failed to update status: %s", rts.error)
                sys.exit(1)

            rt = RTPublish(status_id = rts.id,
                           text = rts.text,
                           in_reply_to_status_id=t.id,
                           created_at = datetime.utcnow())
            rt.save()
        except tweepy.error.TweepError, e:
            logger.warn("Failed to tweet: %s", e)
            sys.exit(1)
        except AttributeError:
            logger.info("AttributeError of status: %s %s", rts.error, dir(rts))

if __name__ == '__main__':
    description = '''Clustering tweets.'''
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1, Copyright (c) 2010 Chinese Shot",
                          description=description)

    parser.add_option("-c", "--config",
                      dest="config",
                      default="lts.cfg",
                      type="string",
                      help="Config file [default %default].",
                      metavar="CONFIG")

    # parser.add_option("-t", "--timelimit",
    #                   dest="timelimit",
    #                   default=3600,
    #                   type="int",
    #                   help="Time limit of tweets [default %default].",
    #                   metavar="TIMELIMIT")

    # parser.add_option("-v", "--vcluster",
    #                   dest="vcluster",
    #                   default='/usr/bin/vcluster',
    #                   type='string',
    #                   help='Path of vcluster command [default %default].',
    #                   metavar="VCLUSTER")

    (options,args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments")

    cfg=Config(file(filter(lambda x: os.path.isfile(x),
                           [options.config,
                            os.path.expanduser('~/.lts.cfg'),
                            '/etc/lts.cfg'])[0]))
    
    # logging.basicConfig(level=logging.DEBUG)
    
    # walk around encoding issue
    reload(sys)
    sys.setdefaultencoding('utf-8') 

    logging.config.fileConfig(cfg.common.log_config)
    logger = logging.getLogger("cluster_tweets.py")

    tt = datetime.utcnow() - timedelta(seconds = cfg.cluster_tweets.time_limit)
    
    logger.debug("Clutering tweets after: %s", tt)

    tweets = Tweet.objects.filter(created_at__gt=tt)
    
    logger.debug("Got %d tweets to cluster.", tweets.count())

    word_freq.logger = logger

    ts = []
    rs = []
    
    for t in tweets:
        ts.insert(0, t)
        rs.insert(0, word_freq.str2freqhash(t.text.encode('utf8')))

    clusters = word_freq.vcluster_with_sample(rs,
                                              cluster_sim_threshold=cfg.cluster_tweets.similarity_threshold,
                                              vcluster_cmd=cfg.cluster_tweets.vcluster_cmd)

    for (s, c, r) in clusters:
        logger.debug("")
        logger.debug("%s %s", s, str(r))
        logger.debug("%s [%s] %s",
                      ts[c].user_screenname,
                      str(ts[c].created_at),
                      ts[c].text)
        logger.debug('----')
        for i in r:
            logger.debug("%s [%s] %s",
                          ts[i].user_screenname,
                          str(ts[i].created_at),
                          ts[i].text)

    if len(clusters) <= 0:
        logger.warn("No valid cluster found.")
        sys.exit(0)

    tt = datetime.utcnow() - timedelta(seconds = cfg.cluster_tweets.duplicated_check_time)
    logger.debug("Getting RTs after: %s", tt)
    rts = RTPublish.objects.filter(created_at__gt=tt)
    logger.debug("Got %d RTs.", rts.count())

    rt_ts = []
    rt_rs = []
    for rt in rts:
        rt_ts.append(rt)
        rt_rs.append(word_freq.str2freqhash(rt.text.encode('utf8')))

    ratings = map(lambda x: len(x[2]), clusters)
    cluster_rs = map(lambda x: rs[x[1]], clusters)

    if len(cluster_rs) and len(rt_rs) > 0:
        logger.debug("%s", cluster_rs)
        logger.debug("%s", rt_rs)
        similarity_matrix = word_freq.hash_filter_knowns(scipy.array(cluster_rs),
                                                         scipy.array(rt_rs),
                                                         similarity_threshold=cfg.cluster_tweets.similarity_threshold)

        logger.debug("%s", str(similarity_matrix))

        for i in range(len(ratings)):
            if similarity_matrix[i]:
                ratings[i] = 0

        logger.debug("%s", str(ratings))

    # logger.debug("%s", str(clusters))
    i = scipy.array(ratings).argmax()
    logger.debug("%d", i)
    if ratings[i] == 0:
        logging.warn("No tweet to RT.")
    else:
        # logger.debug("%s", i)
        t = ts[clusters[i][1]]
        logger.debug("Tweet to RT: %s [%s] %s",
                     t.user_screenname,
                     str(t.created_at),
                     t.text)

        try:
            api = twitter_utils.createCfgApi(cfg.cluster_tweets)

            rts = api.retweet(id = t.id)
            
            logger.info("New tweet: %d %s %s", 
                        rts.id, rts.created_at,
                        rts.text)
 
            if hasattr(rts, 'error'):
                logger.warn("Failed to update status: %s", rts.error)
                sys.exit(1)

            rt = RTPublish(status_id = rts.id,
                           text = rts.text,
                           in_reply_to_status_id=t.id,
                           created_at = datetime.utcnow())
            rt.save()
        except tweepy.error.TweepError, e:
            logger.warn("Failed to tweet: %s", e)
            sys.exit(1)
        except AttributeError:
            logger.info("AttributeError of status: %s %s", rts.error, dir(rts))
