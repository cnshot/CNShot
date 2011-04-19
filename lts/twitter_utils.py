#!/usr/bin/python

import tweepy, logging

from lts.models import TwitterAccount, TwitterApiAuth

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

def createActiveApis():
    accounts = TwitterAccount.objects.filter(active__exact=True)

    return map(lambda x: createApi(x), accounts)

def createCfgApi(user_cfg):
    auth = None
    if 'consumer_key' in user_cfg.keys() and \
            'consumer_secret' in user_cfg.keys() and \
            'access_key' in user_cfg.keys() and \
            'access_secret' in user_cfg.keys():
        auth = MyOAuthHandler(user_cfg.consumer_key,
                                            user_cfg.consumer_secret)
        auth.set_org_url(user_cfg.api_host, user_cfg.api_root)
        auth.set_access_token(user_cfg.access_key, user_cfg.access_secret)
    elif 'username' in user_cfg.keys() and \
            'proxy_password' in user_cfg.keys():
        auth = tweepy.BasicAuthHandler(user_cfg.username,
                                       user_cfg.proxy_password)
    elif 'username' in user_cfg.keys() and \
            'password' in user_cfg.keys():
        auth = tweepy.BasicAuthHandler(user_cfg.username,
                                       user_cfg.password)

    api = tweepy.API(auth_handler=auth,
                     host=user_cfg.api_host,
                     search_host=user_cfg.search_host,
                     api_root=user_cfg.api_root,
                     search_root=user_cfg.search_root,
                     secure=user_cfg.secure_api)
    return api

cfg = None
logger = logging
