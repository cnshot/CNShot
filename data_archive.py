#!/usr/bin/python

import sys, traceback, logging, logging.config, os

from optparse import OptionParser
from config import Config, ConfigMerger, ConfigList
from datetime import timedelta, datetime
from lts.models import Link, LinkShot, ShotPublish, Tweet, LinkRate, ShotCache

class DataArchiver:
    @classmethod
    def deleteExpiredShotCaches(cls, threshold_timestamp):
        # delete shot caches without valid LinkShot
        scs = ShotCache.objects.filter(linkshot=None)
        if len(scs) > 0:
            logger.debug('deleteExpiredShotCaches: deleting %d ShotCaches without valid LinkShot...',
                         len(scs))
        scs.delete()

        # delete shot caches with LinkRate older than threshold_timestamp
        lrs = LinkRate.objects.filter(rating_time__lt=threshold_timestamp)
        if len(lrs) > 0:
            logger.debug('deleteExpiredShotCaches: %d expired LinkRates', len(lrs))
        for lr in lrs:
            l = lr.link.getRoot()
            try:
                ls = LinkShot.objects.filter(link=l)[0]
            except IndexError:
                continue
            if ls.url is not None:
                continue
            scs = ShotCache.objects.filter(linkshot=ls)
            logger.debug('deleteExpiredShotCaches: deleting %d ShotCaches with linkshot %d...', len(scs), ls.id)
            scs.delete()

        # delete shot caches with LinkShot older than threshold_timestamp
        lss = LinkShot.objects.filter(shot_time__lt=threshold_timestamp)
        logger.debug('deleteExpiredShotCaches: %d expired LinkShots', len(lss))
        for ls in lss:
            scs = ShotCache.objects.filter(linkshot=ls)
            logger.debug('deleteExpiredShotCaches: deleting %d ShotCaches with linkshot %d...', len(scs), ls.id)
            scs.delete()

    @classmethod
    def deleteExpiredLinkRates(cls, threshold_timestamp):
        # delete linkrate without link
        lrs = LinkRate.objects.filter(link=None)
        if len(lrs) > 0:
            logger.debug('deleteExpiredLinkRates: deleting %d LinkRates without link...', len(lrs))
        lrs.delete()

        # delete linkrate with expired rating_time
        lrs = LinkRate.objects.filter(rating_time__lt=threshold_timestamp)
        if len(lrs) > 0:
            logger.debug('deleteExpiredLinkRates: deleting %d expired LinkRates...', len(lrs))
        lrs.delete()

    @classmethod
    def deleteExpiredLinkShots(cls, threshold_timestamp):
        # delete linkshot without link
        lss = LinkShot.objects.filter(link=None)
        if len(lss) > 0:
            logger.debug('deleteExpiredLinkShots: deleting %d LinkShots without link...', len(lss))
        for ls in lss:
            ls.shotcache_set.clear()
            ls.shotpublish_set.clear()
            ls.shotblogpost_set.clear()

        lss.delete()

        # delete linkshot with expired shot_time
        lss = LinkShot.objects.filter(shot_time__lt=threshold_timestamp)
        if len(lss) > 0:
            logger.debug('deleteExpiredLinkShots: deleting %d expired LinkShots', len(lss))
        for ls in lss:
            logger.debug('Deleting sets of LinkShot: %d %s %s',
                         ls.id, ls.link, ls.url)
            ls.shotcache_set.clear()
            ls.shotpublish_set.clear()
            ls.shotblogpost_set.clear()

        lss.delete()

    @classmethod
    def deleteExpiredTweets(cls, threshold_timestamp):
        # delete expired tweets
        ts = Tweet.objects.filter(created_at=threshold_timestamp)
        if len(ts) > 0:
            logger.debug('deleteExpiredTweets: deleting %d expired Tweets', len(ts))
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

    DataArchiver.deleteExpiredShotCaches(tt)
    DataArchiver.deleteExpiredLinkRates(tt)
    DataArchiver.deleteExpiredLinkShots(tt)
    DataArchiver.deleteExpiredTweets(tt)
