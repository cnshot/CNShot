#!/usr/bin/python

import tweepy, logging

from lts.models import TwitterAccount, TwitterApiSite

def createApi(account=None):
    auth = None

    if account is None:
        account = TwitterAccount.random()
        logger.debug("Random account: %s", account.screen_name)

    if account is not None:
        if account.consumer_key and account.consumer_secret:
            auto = tweepy.OAuthHandler(account.consumer_key,
                                       account.consumer_secret)
        elif account.screen_name and account.password:
            auth = tweepy.BasicAuthHandler(account.screen_name,
                                           account.password)
    elif cfg is not None:
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

    api_site = TwitterApiSite.random()
    logger.debug("Random API site: %d %s", api_site.id, api_site.api_host)
    if api_site is not None:
        api = tweepy.API(auth_handler=auth,
                         host=api_site.api_host,
                         search_host=api_site.search_host,
                         api_root=api_site.api_root,
                         search_root=api_site.search_root,
                         secure=api_site.secure_api)
    elif cfg is not None:
        api = tweepy.API(auth_handler=auth,
                         host=cfg.common.api_host,
                         search_host=cfg.common.search_host,
                         api_root=cfg.common.api_root,
                         search_root=cfg.common.search_root,
                         secure=cfg.common.secure_api)

    return api

def createActiveApis():
    accounts = TwitterAccount.objects.filter(active__exact=True)

    return map(lambda x: createApi(x), accounts)

cfg = None
logger = logging
