#!/usr/bin/python

import tweepy, logging

from lts.models import TwitterAccount, TwitterApiSite, TwitterApiAuth

class MyOAuthHandler(tweepy.OAuthHandler):
    def set_org_url(self, org_host, org_root,
                    twitter_host='api.twitter.com', twitter_root='/1'):
        self.org_host = org_host
        self.org_root = org_root
        self.twitter_host = twitter_host
        self.twitter_root = twitter_root

    def apply_auth(self, url, method, headers, parameters):
        new_url = url.replace(self.org_host+self.org_root, 
                    self.twitter_host+self.twitter_root,
                    1)
        logger.debug("apply_auth with new URL: %s %s %s",
                     new_url,
                     self.org_host+self.org_root,
                     self.twitter_host+self.twitter_root)
        tweepy.OAuthHandler.apply_auth(self, new_url, method, headers, parameters)

def createApi(account=None):
    auth = None

    if account is None:
        account = TwitterAccount.random()
        logger.debug("Random account: %s", account.screen_name)

    # api_site = TwitterApiSite.random()
    # logger.debug("Random API site: %d %s", api_site.id, api_site.api_host)

    api_auth = TwitterApiAuth.random(account)
    logger.debug("Random auth for account %s: %s", account, api_auth)

    if api_auth is None:
        return None

    if(api_auth.consumer_key and api_auth.consumer_secret and
       api_auth.access_key and api_auth.access_secret):
        auth = MyOAuthHandler(api_auth.consumer_key,
                              api_auth.consumer_secret)
        auth.set_org_url(api_auth.api_site.api_host, api_auth.api_site.api_root)
        auth.set_access_token(api_auth.access_key, api_auth.access_secret)
    elif api_auth.screen_name and api_auth.password:
        auth = tweepy.BasicAuthHandler(api_auth.screen_name,
                                       api_auth.password)

    api = tweepy.API(auth_handler=auth,
                     host=api_auth.api_site.api_host,
                     search_host=api_auth.api_site.search_host,
                     api_root=api_auth.api_site.api_root,
                     search_root=api_auth.api_site.search_root,
                     secure=api_auth.api_site.secure_api)

    return api

    # elif account is not None:
    #     if (account.consumer_key and account.consumer_secret and
    #         account.access_key and account.access_secret):
    #         # auth = tweepy.OAuthHandler(account.consumer_key,
    #         #                            account.consumer_secret)
    #         auth = MyOAuthHandler(account.consumer_key,
    #                               account.consumer_secret)
    #         auth.set_org_url(api_site.api_host, api_site.api_root)
    #         auth.set_access_token(account.access_key, account.access_secret)
    #     elif account.screen_name and account.password:
    #         auth = tweepy.BasicAuthHandler(account.screen_name,
    #                                        account.password)
    # elif cfg is not None:
    #     if 'consumer_key' in cfg.common.keys() and \
    #             'consumer_secret' in cfg.common.keys():
    #         auth = tweepy.OAuthHandler(cfg.common.consumer_key,
    #                                    cfg.common.consumer_secret)
    #     elif 'username' in cfg.common.keys() and \
    #             'proxy_password' in cfg.common.keys():
    #         auth = tweepy.BasicAuthHandler(cfg.common.username,
    #                                        cfg.common.proxy_password)
    #     elif 'username' in cfg.common.keys() and \
    #             'password' in cfg.common.keys():
    #         auth = tweepy.BasicAuthHandler(cfg.common.username, cfg.common.password)

    # if api_site is not None:
    #     api = tweepy.API(auth_handler=auth,
    #                      host=api_site.api_host,
    #                      search_host=api_site.search_host,
    #                      api_root=api_site.api_root,
    #                      search_root=api_site.search_root,
    #                      secure=api_site.secure_api)
    # elif cfg is not None:
    #     api = tweepy.API(auth_handler=auth,
    #                      host=cfg.common.api_host,
    #                      search_host=cfg.common.search_host,
    #                      api_root=cfg.common.api_root,
    #                      search_root=cfg.common.search_root,
    #                      secure=cfg.common.secure_api)

    # return api

def createActiveApis():
    accounts = TwitterAccount.objects.filter(active__exact=True)

    return map(lambda x: createApi(x), accounts)

def createCfgApi(cfg):
    auth = None
    if 'consumer_key' in cfg.common.keys() and \
            'consumer_secret' in cfg.common.keys() and \
            'access_key' in cfg.common.keys() and \
            'access_secret' in cfg.common.keys():
        auth = MyOAuthHandler(cfg.common.consumer_key,
                                            cfg.common.consumer_secret)
        auth.set_org_url(cfg.common.api_host, cfg.common.api_root)
        auth.set_access_token(cfg.common.access_key, cfg.common.access_secret)
    elif 'username' in cfg.common.keys() and \
            'proxy_password' in cfg.common.keys():
        auth = tweepy.BasicAuthHandler(cfg.common.username,
                                       cfg.common.proxy_password)
    elif 'username' in cfg.common.keys() and \
            'password' in cfg.common.keys():
        auth = tweepy.BasicAuthHandler(cfg.common.username,
                                       cfg.common.password)

    api = tweepy.API(auth_handler=auth,
                     host=cfg.common.api_host,
                     search_host=cfg.common.search_host,
                     api_root=cfg.common.api_root,
                     search_root=cfg.common.search_root,
                     secure=cfg.common.secure_api)
    return api

cfg = None
logger = logging
