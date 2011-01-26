#!/usr/bin/python

import sys, traceback, logging, logging.config, os, traceback

from optparse import OptionParser
from config import Config, ConfigMerger, ConfigList
from datetime import timedelta, datetime
from lts.models import Link, LinkShot, ShotPublish, Tweet, LinkRate, ShotCache

def querySetChunk(qs, limit = 1000):
    n = 0
    while True:
        chunk = qs[n:n+limit]
        n += limit
        if chunk.count() <= 0:
            break    
        yield chunk

class DataArchiver:
    @classmethod
    def deleteExpiredShotCaches(cls, threshold_timestamp):
        # delete shot caches without valid LinkShot
        scs = ShotCache.objects.filter(linkshot=None)
        if scs.count() > 0:
            logger.debug('deleteExpiredShotCaches: deleting %d ShotCaches without valid LinkShot...',
                         scs.count())
        scs.delete()

        # delete shot caches with LinkRate older than threshold_timestamp
        lrs = LinkRate.objects.filter(rating_time__lt=threshold_timestamp)
        if lrs.count() > 0:
            logger.debug('deleteExpiredShotCaches: %d expired LinkRates', lrs.count())
        for lr in lrs:
            l = lr.link.getRoot()
            try:
                ls = LinkShot.objects.filter(link=l)[0]
            except IndexError:
                continue
            if ls.url is not None:
                continue
            scs = ShotCache.objects.filter(linkshot=ls)
            logger.debug('deleteExpiredShotCaches: deleting %d ShotCaches with linkshot %d...', scs.count(), ls.id)
            scs.delete()

        # delete shot caches with LinkShot older than threshold_timestamp
        lss = LinkShot.objects.filter(shot_time__lt=threshold_timestamp)
        logger.debug('deleteExpiredShotCaches: %d expired LinkShots', lss.count())
        for ls in lss:
            scs = ShotCache.objects.filter(linkshot=ls)
            logger.debug('deleteExpiredShotCaches: deleting %d ShotCaches with linkshot %d...', scs.count(), ls.id)
            scs.delete()

    @classmethod
    def deleteExpiredLinkRates(cls, threshold_timestamp):
        # delete linkrate without link
        lrs = LinkRate.objects.filter(link=None)
        if lrs.count() > 0:
            logger.debug('deleteExpiredLinkRates: deleting %d LinkRates without link...', lrs.count())
        lrs.delete()

        # delete linkrate with expired rating_time
        lrs = LinkRate.objects.filter(rating_time__lt=threshold_timestamp)
        if lrs.count() > 0:
            logger.debug('deleteExpiredLinkRates: deleting %d expired LinkRates...', lrs.count())
        lrs.delete()

    @classmethod
    def deleteExpiredLinkShots(cls, threshold_timestamp):
        # delete linkshot without link
        lss = LinkShot.objects.filter(link=None)
        if lss.count() > 0:
            logger.debug('deleteExpiredLinkShots: deleting %d LinkShots without link...', lss.count())
        for ls in lss:
            ls.shotcache_set.clear()
            ls.shotpublish_set.clear()
            ls.shotblogpost_set.clear()

        lss.delete()

        # delete linkshot with expired shot_time
        lss = LinkShot.objects.filter(shot_time__lt=threshold_timestamp)

        for lss_chunk in querySetChunk(lss, cfg.data_archive.query_limit):
            logger.debug('deleteExpiredLinkShots: deleting %d expired LinkShots', lss_chunk.count())
            for ls in lss_chunk:
                logger.debug('Deleting sets of LinkShot: %d %s %s',
                             ls.id, ls.link, ls.url)
                try:
                    ls.shotcache_set.clear()
                    ls.shotpublish_set.clear()
                    ls.shotblogpost_set.clear()
                except:
                    logger.error("Failed to process status: %s", sys.exc_info()[0])
                    logger.error('-'*60)
                    logger.error("%s", traceback.format_exc())
                    logger.error('-'*60)
                    continue

        lss.delete()

    @classmethod
    def deleteExpiredTweets(cls, threshold_timestamp):
        # delete expired tweets
        ts = Tweet.objects.filter(created_at__lt=threshold_timestamp)
        logger.debug("%s", ts.query.as_sql())
        logger.debug('deleteExpiredTweets: deleting %d expired Tweets', ts.count())
        for t in ts:
            t.linkshot_set.clear()

        ts.delete()

if __name__ == '__main__':
    description = '''Data archive.'''
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1, Copyright (c) 2010 Chinese Shot",
                          description=description)

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

    reload(sys)
    sys.setdefaultencoding('utf-8') 

    logging.config.fileConfig(cfg.common.log_config)
    logger = logging.getLogger("data_archive")

    tt = datetime.utcnow() - timedelta(seconds = cfg.data_archive.expire_time)

    logger.debug("Archiving data with time limit: %s", tt)

    DataArchiver.deleteExpiredShotCaches(tt)
    DataArchiver.deleteExpiredLinkRates(tt)
    DataArchiver.deleteExpiredLinkShots(tt)
    DataArchiver.deleteExpiredTweets(tt)
