#!/usr/bin/python

# routine of update twitter users with followings and followers
# just create the records
# fetch the detail user info with other routines

from __future__ import with_statement

import re, twitter_utils
import tweepy
import user_evaluating

from datetime import timedelta, datetime

from lts.models import TwitterUser, TwitterUserExt, TwitterAccount, LinkRate

def fetchUsers(func, updateFunc, account):
    next_cursor = -1

    results = []
    while next_cursor != 0:
        try:
            fs = func(cursor=next_cursor)
        except tweepy.error.TweepError:
            logger.warn("Failed to get user list.")
            return

        logger.debug("Got user with cursor: %d %d", fs[1][0], fs[1][1])
        next_cursor = fs[1][1]
        
        results += fs[0]

    for f in results:
        updateFunc(f, account)

def updateUser(f, account=None):
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

def updateFollower(f, account):
    logger.debug("Update follower: %d %s", f.id, f.screen_name)
    u = updateUser(f)
    try:
        ue = TwitterUserExt.objects.get(twitteruser = u)
        ue.following_account.add(account)
    except TwitterUserExt.DoesNotExist:
        ue = TwitterUserExt(twitteruser = u)
        ue.save()
        ue.following_account=[account]
    try:
        ue.last_status_created_at = f.status.created_at
    except AttributeError:
        logger.warn("User without status: %s", f.screen_name)
    ue.save()

def updateFriend(f, account):
    logger.debug("Update friend: %d %s", f.id, f.screen_name)
    u = updateUser(f)
    try:
        ue = TwitterUserExt.objects.get(twitteruser = u)
        ue.followed_by_account.add(account)
    except TwitterUserExt.DoesNotExist:
        ue = TwitterUserExt(twitteruser = u)
        ue.save()
        ue.followed_by_account=[account]
    try:
        ue.last_status_created_at = f.status.created_at
    except AttributeError:
        logger.warn("User without status: %s", f.screen_name)
    ue.save()
    
def updateTwitterUsers(api=None):
    if api is None:
        # twitter_utils.cfg = cfg
        # twitter_utils.logger = logger
        api = twitter_utils.createApi()

    ues = TwitterUserExt.objects.extra(select={'followed_count':"""
SELECT COUNT(*)
FROM lts_twitteruserext_followed_by_account
WHERE lts_twitteruserext_followed_by_account.twitteruserext_id = lts_twitteruserext.twitteruser_id
"""}).filter(last_update__lte=datetime.now()-timedelta(seconds=cfg.update_twitter_users.update_interval)).order_by('last_update')
    ues = filter(lambda x: x.followed_count == 0, ues)
    c = int(len(ues)*cfg.update_twitter_users.update_rate+1-cfg.update_twitter_users.update_rate)
    if c > cfg.update_twitter_users.update_limit:
        c = cfg.update_twitter_users.update_limit

    user_evaluating.cfg = cfg
    user_evaluating.logger = logger

    ues = ues[:c]
    for ue in ues:
        user_evaluating.evaluate_user(ue.twitteruser, api)


def updateTwitterAccounts():
    # twitter_utils.cfg = cfg
    # twitter_utils.logger = logger

    active_accounts = TwitterAccount.objects.filter(active=True)
    for account in active_accounts:
        api = twitter_utils.createApi(account=account)

        try:
            me = api.me()
        except tweepy.error.TweepError:
            logger.warn("Failed to call api.me(), stop updating current account: %s", account.screen_name)
            continue

        if not me:
            logger.warn("Failed to get account info: %s", account.screen_name)
            continue
        
        account.name = me.name
        account.location = me.location
        account.description = me.description
        account.profile_image_url = me.profile_image_url
        account.protected = me.protected
        account.utc_offset = me.utc_offset
        account.time_zone = me.time_zone
        account.followers_count = me.followers_count
        account.friends_count = me.friends_count
        account.statuses_count = me.statuses_count
        account.favourites_count = me.favourites_count
        account.url = me.url
        
        account.save()

        logger.info("Update followers...")
        map(lambda u: (u.following_account.remove(account), u.save()),
            TwitterUserExt.objects.filter(following_account=account))
        fetchUsers(me.followers, updateFollower, account)
        logger.info("Update friends...")
        map(lambda u: (u.followed_by_account.remove(account), u.save()),
            TwitterUserExt.objects.filter(followed_by_account=account))
        fetchUsers(me.friends, updateFriend, account)

def followUsers():
    active_accounts = TwitterAccount.objects.filter(active=True).\
        order_by("followers_count")
    active_accounts = filter(lambda x: x.friends_count < cfg.update_twitter_users.follow.free_following or x.friends_count < x.followers_count * cfg.update_twitter_users.follow.following_rate_limit, active_accounts) 

    if len(active_accounts)<=0:
        logger.warn("No account available.")
        return

    account=active_accounts[0]
    logger.info("Follow users with account: %s", account.screen_name)

    follow_cfg = cfg.update_twitter_users.follow
    ues = TwitterUserExt.objects.\
        filter(ignored=False).\
        filter(chinese_rate__gte=follow_cfg.chinese_rate_min).\
        filter(chinese_rate__lte=follow_cfg.chinese_rate_max).\
        filter(link_rate__gte=follow_cfg.link_rate_min).\
        filter(link_rate__lte=follow_cfg.link_rate_max).\
        filter(twitteruser__protected=False).\
        filter(twitteruser__statuses_count__gte=follow_cfg.statuses_count_min).\
        filter(twitteruser__followers_count__gte=follow_cfg.followers_count_min).\
        filter(twitteruser__friends_count__gte=follow_cfg.friends_count_min).\
        extra(select={'score':"""
SELECT lts_twitteruser.statuses_count * %s +
    lts_twitteruser.followers_count * %s +
    lts_twitteruser.friends_count * %s
FROM lts_twitteruser
WHERE lts_twitteruser.id = lts_twitteruserext.twitteruser_id
""",
                      'followed_count':"""
SELECT COUNT(*) FROM lts_twitteruserext_followed_by_account
WHERE lts_twitteruserext_followed_by_account.twitteruserext_id = lts_twitteruserext.twitteruser_id
"""},
              select_params=[follow_cfg.weight.statuses_count,
                             follow_cfg.weight.followers_count,
                             follow_cfg.weight.friends_count]
              ).\
         order_by('last_update')

    logger.debug("Query for users to follow: %s", str(ues.query))

    active_accounts = TwitterAccount.objects.filter(active=True)
    account_screen_names = []
    for ac in active_accounts:
        account_screen_names.append(ac.screen_name)

    sorted_ues = sorted(filter(lambda x: x.followed_count == 0 and x.twitteruser.screen_name not in account_screen_names, ues),
                        lambda x,y: 1 if x.score < y.score else -1)[:follow_cfg.limit]

    logger.debug("Got %d users to follow.", len(sorted_ues))

    # twitter_utils.cfg = cfg
    # twitter_utils.logger = logger
    
    api = twitter_utils.createApi(account=account)
    for ue in sorted_ues:
        logger.debug("User %d with score: %f",
                     ue.twitteruser.id,
                     ue.score)
        try:
            logger.debug("Adding friend for %s: %d %s",
                         account.screen_name,
                         ue.twitteruser.id,
                         ue.twitteruser.screen_name)
            api.create_friendship(user_id=ue.twitteruser.id)
            ue.followed_by_account.add(account)
            ue.save()
        except tweepy.error.TweepError:
            logger.warn("Failed to add friend for %s: %d %s",
                        account.screen_name,
                        ue.twitteruser.id,
                        ue.twitteruser.screen_name)

            try:
                u = api.get_user(user_id = ue.twitteruser.id)
                if u.following:
                    logger.info("Update following status: %d %s",
                                ue.twitteruser.id,
                                ue.twitteruser.screen_name)
                    ue.followed_by_account.add(account)
                    ue.save()
                else:
                    # unknown issue, ignore the user for the future
                    logger.warn("Unknown issue of following user, ingore it: %d %s",
                                ue.twitteruser.id,
                                ue.twitteruser.screen_name)
                    ue.ignored = True
                    ue.save()
            except tweepy.error.TweepError:
                logger.warn("Failed to get user, delete it: %d %s",
                        ue.twitteruser.id,
                        ue.twitteruser.screen_name)
                ue.delete()

def updateTweetMentioned():
    user_evaluating.cfg = cfg
    user_evaluating.logger = logger

    tt = datetime.utcnow() - timedelta(seconds = cfg.update_twitter_users.tweet_mentioned.rank_time)
    lrs = LinkRate.objects.extra(select={'shot':"""
SELECT COUNT(*) FROM lts_linkshot 
WHERE lts_linkshot.link_id=lts_linkrate.link_id
"""}).filter(rating_time__gte=tt)
    lrs = sorted(filter(lambda x: x.shot>0, lrs),
                 lambda x,y: y.link.getRateSum()-x.link.getRateSum())[:cfg.update_twitter_users.tweet_mentioned.limit]
    
    p=re.compile('(^|\W)@(\w+)')
    for lr in lrs:
        t = lr.link.getFirstTweet()
        if t is None:
            logger.warn("Failed to get tweet of link: %s", lr.link.url)
            continue

        m=p.findall(t.text)
        for user in map(lambda x:x[1], m):
            # check user info, and add twitter user if necessary
            user_evaluating.evaluate_screen_name(user)

class UpdateTwitterAccounts:
    @classmethod
    def run(cls, _cfg, _logger):
        global cfg, logger
        cfg = _cfg
        logger = _logger
        
        updateTwitterAccounts()

class UpdateTwitterUsers:
    @classmethod
    def run(cls, _cfg, _logger):
        global cfg, logger
        cfg = _cfg
        logger = _logger
        
        updateTwitterUsers()

class FollowUsers:
    @classmethod
    def run(cls, _cfg, _logger):
        global cfg, logger
        cfg = _cfg
        logger = _logger
        
        followUsers()

class UpdateTweetMentioned:
    @classmethod
    def run(cls, _cfg, _logger):
        global cfg, logger
        cfg = _cfg
        logger = _logger
        
        updateTweetMentioned()

