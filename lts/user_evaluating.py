#!/usr/bin/python

import re, tweepy, twitter_utils, traceback

from lts.models import TwitterUser, TwitterUserExt
from chinese_detecting import isChinesePhase
from datetime import timedelta, datetime

global cfg, logger

def evaluate_screen_name(screen_name, api=None):
    logger.debug("Evaluating screen_name: %s", screen_name)

    if api is None:
        api = twitter_utils.createCfgApi(cfg.common)

    try:
        user = TwitterUser.objects.filter(screen_name__exact=screen_name)[0]
    except IndexError:
        logger.debug("Creating new user: %s", screen_name)
        try:
            f = api.get_user(screen_name=screen_name)
        except tweepy.error.TweepError, e:
            logger.warn("Failed to evaluate screen_name %s: %s", screen_name, e)
            return
        user = TwitterUser(id=f.id,
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
        user.save()

    try:
        ue = TwitterUserExt.objects.get(twitteruser = user)
        if len(ue.followed_by_account.all()) > 0:
            logger.debug("Followed user, Skip evaluating: %s", screen_name)
            return
        if ue.last_update >= datetime.now() - timedelta(seconds = cfg.update_twitter_users.update_interval):
            logger.debug("Updated during the last %d seconds, skip it.",
                         cfg.update_twitter_users.update_interval)
            return
    except TwitterUserExt.DoesNotExist:
        pass

    evaluate_user(user, api)

def evaluate_user(user, api=None):
    logger.debug("Evaluating user: %s", user.screen_name)

    if api is None:
        api = twitter_utils.createCfgApi(cfg.common)
    
    try:
        ue = TwitterUserExt.objects.get(twitteruser = user)
    except TwitterUserExt.DoesNotExist:
        logger.debug("Creating new user ext: %s", user.screen_name)
        ue = TwitterUserExt(twitteruser = user)
        ue.save()

        # following_account and followed_by_account will be updated by
        #   update_twitter_users.py .

        # get recent tweets
        # caculate and update link_rate and chinese_rate

    url_pattern = re.compile('((http|ftp|https):\/\/[\w\-_]+(\.[\w\-_]+)+([\w\-\.,@?^=%&amp;:/~\+#]*[\w\-\@?^=%&amp;/~\+#])?)')

    try:
        ss = []
        max_id = None
        while len(ss) < cfg.user_evaluating.count:
            if max_id is None:
                status = api.user_timeline(screen_name=user.screen_name,
                                           count=cfg.user_evaluating.count,
                                           include_rts=1,
                                           include_entities=1)
            else:
                status = api.user_timeline(screen_name=user.screen_name,
                                           count=cfg.user_evaluating.count,
                                           max_id=max_id,
                                           include_rts=1,
                                           include_entities=1)
            logger.debug("Got %d tweets.", len(status))
            if len(status) == 0:
                break
            max_id = status[-1].id - 1
            ss += status
    except tweepy.error.TweepError, e:
        logger.warn("Failed to evaluate user %s: %s", user.screen_name, e)
        return
    except (NameError, AttributeError):
        logger.warn("Failed to evaluate user %s: %s", user.screen_name,
                    traceback.format_exc())
        return

    chinese_tweet_count = 0
    link_tweet_count = 0

    logger.debug("Evaluating with %d tweets ...", len(ss))

    if len(ss) == 0:
        logger.debug("User with no tweet, delete it: %s", user.screen_name)
        ue.delete()
        return

    for s in ss:
        if isChinesePhase(s.text.encode("utf-8", "ignore")):
            logger.debug("Chinese tweet %d: %s",
                         chinese_tweet_count, s.text.encode("utf-8", "ignore"))
            chinese_tweet_count += 1
        if url_pattern.search(s.text):
            logger.debug("Link tweet %d: %s",
                         link_tweet_count, s.text.encode("utf-8", "ignore"))
            link_tweet_count += 1
    ue.chinese_rate = float(chinese_tweet_count) / len(ss)
    ue.link_rate = float(link_tweet_count) / len(ss)
    logger.info("User %s: chinese rate = %f, link rate = %f",
                user.screen_name, ue.chinese_rate, ue.link_rate)

    ue.last_status_created_at = ss[0].created_at

    ue.last_update = datetime.now()

    ue.save()
