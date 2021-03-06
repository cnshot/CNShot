#!/usr/bin/python

import sys, traceback, twitpic, urllib2, urllib, re, tweepy, twitter_utils

from datetime import datetime, timedelta
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
from pyTweetPhoto import pyTweetPhoto
from lxml import etree

from lts.models import LinkShot, ShotPublish, Tweet, LinkRate, ShotBlogPost

def shortenURL(url_to_shorten,
               shortener = "http://is.gd/api.php", query = "longurl"):
    try:
        return urllib2.urlopen(shortener + "?" + urllib.urlencode({query: url_to_shorten})).read()
    except urllib2.HTTPError:
        logger.warn("Failed to shorten url: %s", url_to_shorten)
        return None

def post_image_twitpic(image_path, s):
    twitpic_url = None
    thumbnail_url = None

    try:
        logger.debug("Post image to twitpic: %s %s", image_path, s)

        twit = twitpic.TwitPicAPI(cfg.common.username,
                                  cfg.common.password)

        twitpic_url = twit.upload(image_path, 
                                  message = s[0:140],
                                  post_to_twitter=False)

        if isinstance(twitpic_url, int):
            logger.info("Failed to update image to Twitpic: %d", twitpic_url)
            twitpic_url = None
        else:
            logger.info("Uploaded %s to %s", image_path, twitpic_url)
            thumbnail_url = re.sub(r'^http://twitpic.com/(.+)$',
                                   r'http://twitpic.com/show/thumb/\1',
                                   twitpic_url)

        logger.debug("Twitpic posted: %s %s", image_path, s)
    except:
        logger.error("Failed to tweet image: %s", sys.exc_info()[0])
        logger.error('-'*60)
        logger.error("%s", traceback.format_exc())
        logger.error('-'*60)
    finally:
        return twitpic_url, thumbnail_url

def post_image_moby(image_path, s):
    image_url = None
    thumbnail_url = None

    try:
        logger.debug("Post image to moby: %s %s", image_path, s)

        datagen, headers = multipart_encode({'u':cfg.common.username,
                                             'p':cfg.common.password,
                                             'k':cfg.common.moby_key,
                                             'i':open(image_path, 'rb'),
                                             'action':'postMediaUrl',
                                             's': 'none',
                                             'd':s[0:140]})
        request = urllib2.Request("http://api.mobypicture.com/", datagen, headers)
        response = urllib2.urlopen(request)
        
        if response.code != 200:
            return None, None

        image_url = response.read()

        m = re.match(r'^http://moby\.to/(.+)', image_url)
        if not m:
            return None, None

        datagen, headers = multipart_encode({'t':m.group(1),
                                             's':'small',
                                             'k':cfg.common.moby_key,
                                             'action':'getThumbUrl'})
        request = urllib2.Request("http://api.mobypicture.com/", datagen, headers)
        response = urllib2.urlopen(request)
        if response.code != 200:
            return None, None

        thumbnail_url = response.read()

        logger.debug("Moby posted: %s %s", image_path, s)
    except:
        logger.error("Failed to tweet image: %s", sys.exc_info()[0])
        logger.error('-'*60)
        logger.error("%s", traceback.format_exc())
        logger.error('-'*60)
    finally:
        return image_url, thumbnail_url

def post_image_twitgoo(image_path, s):
    image_url = None
    thumbnail_url = None

    try:
        logger.debug("Post image to twitgoo: %s %s", image_path, s)

        datagen, headers = multipart_encode({'username':cfg.common.username,
                                             'password':cfg.common.password,
                                             'message':s[0:140],
                                             'media':open(image_path, "rb")})
        request = urllib2.Request("http://twitgoo.com/api/upload", datagen, headers)
        response = urllib2.urlopen(request)
        
        if response.code != 200:
            return None, None

        root = etree.fromstring(response.read())
        image_url = root.xpath('/rsp/mediaurl')[0].text
        thumbnail_url = root.xpath('/rsp/thumburl')[0].text

        logger.debug("Twitgoo posted: %s %s", image_path, s)
    except:
        logger.error("Failed to tweet image: %s", sys.exc_info()[0])
        logger.error('-'*60)
        logger.error("%s", traceback.format_exc())
        logger.error('-'*60)
    finally:
        return image_url, thumbnail_url

def post_image_tweetphoto(image_path, s):
    image_url = None
    thumbnail_url = None

    try:
        logger.debug("Post image to tweetphoto: %s %s", image_path, s)

        api = pyTweetPhoto.TweetPhotoApi(username=cfg.common.username,
                                         password=cfg.common.password,
                                         apikey=cfg.common.tweetphoto_key)
        r=api.Upload(image_path,
                     message=s[0:140],
                     post_to_twitter=False)

        image_url = r['MediaUrl']
        thumbnail_url = r['Thumbnail']

        logger.debug("Tweetphoto posted: %s %s", image_path, s)
    except:
        logger.error("Failed to tweet image: %s", sys.exc_info()[0])
        logger.error('-'*60)
        logger.error("%s", traceback.format_exc())
        logger.error('-'*60)
    finally:
        return image_url, thumbnail_url

def post_image_imjtw(image_path, s):
    image_url = None
    thumbnail_url = None

    try:
        logger.debug("Post image to imj.tw: %s %s", image_path, s)

        datagen, headers = multipart_encode({'username':cfg.common.username,
                                             'password':cfg.common.password,
                                             'media':open(image_path, "rb")})
        request = urllib2.Request("http://api.imj.tw/upload", datagen, headers)
        response = urllib2.urlopen(request)
        
        if response.code != 200:
            return None, None

        root = etree.fromstring(response.read())
        image_url = root.xpath('/res/media_url')[0].text
        thumbnail_url = root.xpath('/res/thumbnail_url')[0].text

        logger.debug("imj.tw posted: %s %s", image_path, s)
    except:
        logger.error("Failed to tweet image: %s", sys.exc_info()[0])
        logger.error('-'*60)
        logger.error("%s", traceback.format_exc())
        logger.error('-'*60)
    finally:
        return image_url, thumbnail_url

class TweetShot:
    @classmethod
    def tweetLink(cls, link, post_image_func):
        t = cls.getFirstTweet(link)
        if t is None:
            logger.warn("Failed to get tweet of link: %s", link.url)
            return

        try:
            ls = LinkShot.objects.filter(link=link)[0]
            sbp = ShotBlogPost.objects.filter(link=link)[0]
        except IndexError:
            logger.warn("Failed to get shot of link: %s", link.url)
            return

        url = shortenURL(sbp.url)
        if url is None:
            url = ls.url

        rt_text = unicode(url) + ' RT @' + t.user_screenname + u': ' + t.text
        logger.debug("Status text: %s", rt_text)

        api = twitter_utils.createCfgApi(cfg.common)
        rts = api.update_status(status = rt_text[0:140],
                                in_reply_to_status_id = t.id)

        if hasattr(rts, 'error'):
            logger.warn("Failed to update status: %s", rts.error)
            return

        try:
            logger.info("New tweet: %d %s %s", 
                        rts.id, rts.created_at,
                        rts.text)

            # update ShotPublish
            ShotPublish.objects.filter(link=link).delete()
            url = "http://twitter.com/" + rts.user.screen_name + "/status/" + str(rts.id)
            sp = ShotPublish(link=link, shot=ls, publish_time=datetime.utcnow(),
                             url=url, site="Twitter")
            sp.save()
        except AttributeError:
            logger.info("AttributeError of status: %s %s", rts.error, dir(rts))

    @classmethod
    def getFirstTweet(cls, link):
        ls = link.getRoot().getAliases()
        first_tweet = None
        first_t = datetime.utcnow() + timedelta(days = 1)
        for l in ls:
            try:
                tweet = Tweet.objects.filter(links=l).order_by('created_at')[0]
                if tweet.created_at < first_t:
                    first_tweet = tweet
                    first_t = tweet.created_at
            except IndexError:
                logger.debug("Failed to get the first tweet of link: [%d] %s", l.id, l)
                pass
        return first_tweet

    @classmethod
    def tweetShot(cls):
        # user_evaluating.logger = logger

        register_openers()

        if cfg.tweet_shot.image_service == 'twitpic':
            f = post_image_twitpic
        elif cfg.tweet_shot.image_service == 'moby':
            f = post_image_moby
        elif cfg.tweet_shot.image_service == 'tweetphoto':
            f = post_image_tweetphoto
        elif cfg.tweet_shot.image_service == 'twitgoo':
            f = post_image_twitgoo
        elif cfg.tweet_shot.image_service == 'imj.tw':
            f = post_image_imjtw
        else:
            f = post_image_twitpic

        # get links; if options.tweet, tweet them
#        lrs = cls.getLinkRatings(cfg.tweet_shot.rank_time)
#        sbps = cls.getBlogRatings(cfg.tweet_shot.rank_time)
        
        def link_filter(link):
            ls = link.getLinkShot()
            if ls is None or ls.thumbnail_url is None or ls.url is None:
                return False
            if link.getShotBlogPost() is None:
                return False
            if link.getShotPublish() is not None:
                return False
            return True

        links = LinkRate.orderedLinks(datetime.utcnow() - timedelta(seconds = cfg.image_upload.rank_time),
                                      filter_func=link_filter)

        tweeted = 0
        for l in links:
            if tweeted >= cfg.tweet_shot.number:
                break

#            l = sbp.link.getRoot()

            if cfg.tweet_shot.tweet:
                logger.info("Tweet: [%d] %s", l.id, l.url)
                try:
                    TweetShot.tweetLink(l, f)
                except tweepy.error.TweepError, e:
                    logger.warn("Failed to tweet: %s", e)
                    continue
            else:
                logger.info("Skip tweet: [%d] %s", l.id, l.url)

            tweeted += 1

        logger.info("Tweeted %d shots.", tweeted)

def run(_cfg, _logger):
    global cfg, logger
    cfg = _cfg
    logger = _logger

    TweetShot.tweetShot()
        
