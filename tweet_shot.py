#!/usr/bin/python

import stompy, pickle, memcache, sys, traceback, logging, logging.config, os, \
    twitpic, urllib2, re, tweepy

from optparse import OptionParser
from datetime import datetime, timedelta
from django.core.exceptions import ObjectDoesNotExist
from config import Config, ConfigMerger
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
from pyTweetPhoto import pyTweetPhoto
from lxml import etree

#os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from lts.models import Link, LinkShot, ShotPublish, Tweet, LinkRate, ShotCache

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
    def getLinks(cls, rank_time, count):
        tt = datetime.utcnow() - timedelta(seconds = rank_time);
        lrs = LinkRate.objects.extra(select={'published':"SELECT COUNT(*) FROM lts_shotpublish WHERE lts_shotpublish.link_id=lts_linkrate.link_id",
                          'shot':"SELECT COUNT(*) FROM lts_linkshot WHERE lts_linkshot.link_id=lts_linkrate.link_id"}).filter(rating_time__gte=tt)

        logger.debug("Query for links to tweet: %s", lrs.query.as_sql())
            
        lrs = filter(lambda x: x.published==0 and x.shot>0, lrs)
        
        sorted_lrs = sorted(lrs, lambda x,y: y.link.getRateSum()-x.link.getRateSum())
        return map(lambda x: x.link.getRoot(), sorted_lrs[:count])

    @classmethod
    def tweetLink(cls, link, post_image_func):
        t = cls.getFirstTweet(link)
        if t is None:
            logger.warn("Failed to get tweet of link: %s", link.url)
            return

        try:
            ls = LinkShot.objects.filter(link=link)[0]
        except IndexError:
            logger.warn("Failed to get shot of link: %s", link.url)
            return

        try:
            rt_text = u'RT @' + t.user_screenname + u': ' + t.text
            cs = ShotCache.objects.get(linkshot=ls)
            url, thumbnail_url = post_image_func(cs.image.path,
                                                rt_text.encode('utf-8'))
            if url is None:
                logger.warn("Failed to post image: %s", link.url)
            else:
                ls.url = url
                ls.thumbnail_url = thumbnail_url
                ls.save()
        except ShotCache.DoesNotExist:
            logger.warn("Failed to get shot cache of link: %s", link.url)

        rt_text = unicode(ls.url) + ' RT @' + t.user_screenname + u': ' + t.text
        # api = twitter.Api(username=cfg.common.username,
        #                   password=cfg.common.password)
        # rts = api.PostUpdate(rt_text[0:140], in_reply_to_status_id=t.id)

        # logger.info("New tweet: %d %s %s", 
        #             rts.id, str(rts.created_at),
        #             rts.text.encode('utf-8'))

        auth = None
        if 'consumer_key' in cfg.common.keys() and \
                'consumer_secret' in cfg.common.keys():
            auth = tweepy.OAuthHandler(cfg.common.consumer_key, cfg.common.consumer_secret)
        elif 'username' in cfg.common.keys() and \
                'password' in cfg.common.keys():
            auth = tweepy.BasicAuthHandler(cfg.common.username, cfg.common.password)
        api = tweepy.API(auth_handler=auth,
                         host=cfg.common.api_host,
                         search_host=cfg.common.search_host,
                         api_root=cfg.common.api_root,
                         search_root=cfg.common.search_root)

        rts = api.update_status(status = rt_text[0:140],
                                in_reply_to_status_id = t.id)

        logger.info("New tweet: %d %s %s", 
                    rts.id, rts.created_at,
                    rts.text)

        # update ShotPublish
        ShotPublish.objects.filter(link=link).delete()
        url = "http://twitter.com/" + rts.user.screen_name + "/status/" + str(rts.id)
        sp = ShotPublish(link=link, shot=ls, publish_time=datetime.utcnow(),
                         url=url, site="Twitter")
        sp.save()

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

if __name__ == '__main__':
    description = '''Tweet screenshots.'''
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1, Copyright (c) 2010 Chinese Shot",
                          description=description)

    # parser.add_option("-u", "--username", dest="username", type="string",
    #                   default="username",
    #                   help="Twitter username [default: %default].",
    #                   metavar="USERNAME")

    # parser.add_option("-p", "--password", dest="password", type="string",
    #                   default="password",
    #                   help="Twitter password [default: %default].",
    #                   metavar="PASSWORD")

    # parser.add_option("-l", "--log-config",
    #                   dest="log_config", 
    #                   default="/etc/link_shot_tweet_log.conf",
    #                   type="string",
    #                   help="Logging config file [default: %default].",
    #                   metavar="LOG_CONFIG")

    parser.add_option("-c", "--config",
                      dest="config",
                      default="lts.cfg",
                      type="string",
                      help="Config file [default %default].",
                      metavar="CONFIG")

    # parser.add_option("-t", "--tweet", action="store_true", dest="tweet",
    #                   default=False)

    # parser.add_option("-r", "--rank_time",
    #                   dest="rank_time", default="7200", type="int",
    #                   help="Time perioud of link ranks to sort in second [default: %default].",
    #                   metavar="RANK_TIME")

    # parser.add_option("-n", "--number", dest="number", default=1, type="int",
    #                   help="Number of links to tweet [default:%default].",
    #                   metavar="NUMBER")

    (options,args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments")

    cfg=Config(file(filter(lambda x: os.path.isfile(x),
                           [options.config,
                            os.path.expanduser('~/.lts.cfg'),
                            '/etc/lts.cfg'])[0]))
    # cfg.addNamespace(options,'common')

    # walk around encoding issue
    reload(sys)
    sys.setdefaultencoding('utf-8') 

    logging.config.fileConfig(cfg.common.log_config)
    logger = logging.getLogger("tweet_shot")

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
    links = TweetShot.getLinks(cfg.tweet_shot.rank_time, cfg.tweet_shot.number)   
    for l in links:
        if cfg.tweet_shot.tweet:
            logger.info("Tweet: [%d] %s", l.id, l.url)
            TweetShot.tweetLink(l, f)
        else:
            logger.info("Skip tweet: [%d] %s", l.id, l.url)
