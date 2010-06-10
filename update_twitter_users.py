#!/usr/bin/python

# routine of update twitter users with followings and followers
# just create the records
# fetch the detail user info with other routines

from __future__ import with_statement

import os, md5, re, uuid, sys, pickle, memcache, time, rfc822, \
    logging, logging.config
import tweepy

from optparse import OptionParser
from datetime import timedelta, datetime
from config import Config

from lts.models import TwitterUser, TwitterUserExt

def fetchUsers(func,updateFunc):
    next_cursor = -1
    while next_cursor != 0:
        try:
            fs = func(cursor=next_cursor)
        except tweepy.error.TweepError:
            logger.warn("Failed to get user list.")
            return

        logger.debug("Got user with cursor: %d %d", fs[1][0], fs[1][1])
        next_cursor = fs[1][1]
        
        for f in fs[0]:
            updateFunc(f)

def updateUser(f):
    # Update TwitterUser
    logger.debug("Update user: %d %s", f.id, f.screen_name)
    u = TwitterUser(id=f.id,
                    name=f.name,
                    screen_name=f.screen_name,
                    location=f.location,
                    description=f.description,
                    profile_image_url=f.profile_image_url,
                    protected=f.protected,
                    utc_offset=f.utc_offset,
                    time_zone=f.time_zone,
                    followers_count=f.followers_count,
                    friends_count=f.friends_count,
                    statuses_count=f.statuses_count,
                    favourites_count=f.favourites_count,
                    url=f.url)
    u.save()
    return u

def updateFollower(f):
    logger.debug("Update follower: %d %s", f.id, f.screen_name)
    u = updateUser(f)
    try:
        ue = TwitterUserExt.objects.get(twitteruser = u)
        ue.following_me = True
    except TwitterUserExt.DoesNotExist:
        ue = TwitterUserExt(twitteruser = u,
                            following_me = True)
    ue.save()

def updateFriend(f):
    logger.debug("Update friend: %d %s", f.id, f.screen_name)
    u = updateUser(f)
    try:
        ue = TwitterUserExt.objects.get(twitteruser = u)
        ue.followed_by_me = True
    except TwitterUserExt.DoesNotExist:
        ue = TwitterUserExt(twitteruser = u,
                            followed_by_me = True)
    ue.save()

def updateTwitterUsers():
    auth = None
    if 'consumer_key' in cfg.common.keys() and \
            'consumer_secret' in cfg.common.keys():
        auth = tweepy.OAuthHandler(cfg.common.consumer_key,
                                   cfg.common.consumer_secret)
    elif 'username' in cfg.common.keys() and \
            'proxy_password' in cfg.common.keys():
        auth = tweepy.BasicAuthHandler(cfg.common.username,
                                       cfg.common.proxy_password)
    elif 'username' in cfg.common.keys() and \
            'password' in cfg.common.keys():
        auth = tweepy.BasicAuthHandler(cfg.common.username, cfg.common.password)

    api = tweepy.API(auth_handler=auth,
                     host=cfg.common.api_host,
                     search_host=cfg.common.search_host,
                     api_root=cfg.common.api_root,
                     search_root=cfg.common.search_root,
                     secure=cfg.common.secure_api)

    logger.info("Update followers...")
    fetchUsers(api.followers, updateFollower)
    logger.info("Update friends...")
    fetchUsers(api.friends, updateFriend)

if __name__ == '__main__':
    description = '''Update basic Twitter users' information.'''
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

    cfg.addNamespace(options, 'cmdline')

    reload(sys)
    sys.setdefaultencoding('utf-8')

    logging.config.fileConfig(cfg.common.log_config)
    logger = logging.getLogger("update_twitter_users")

    updateTwitterUsers()
