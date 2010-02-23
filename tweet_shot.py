#!/usr/bin/python

import stompy, pickle, memcache, sys, traceback, logging, logging.config, os
import twitpic, twitter

from optparse import OptionParser
from datetime import datetime, timedelta
from django.core.exceptions import ObjectDoesNotExist

#os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from lts.models import Link, LinkShot, ShotPublish, Tweet, LinkRate

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
    def tweetLink(cls, link):
        t = cls.getFirstTweet(link)
        if t is None:
            logger.warn("Failed to get tweet of link: %s", link.url)
            return

        try:
            ls = LinkShot.objects.filter(link=link)[0]
        except IndexError:
            logger.warn("Failed to get shot of link: %s", link.url)
            return

        rt_text = unicode(ls.url) + ' RT @' + t.user_screenname + u': ' + t.text
        api = twitter.Api(username=options.username, password=options.password)
        rts = api.PostUpdate(rt_text[0:140], in_reply_to_status_id=t.id)
        logger.info("New tweet: %d %s %s", 
                    rts.id, str(rts.created_at),
                    rts.text.encode('utf-8'))

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
        first_t = datetime.utcnow()
        for l in ls:
            try:
                tweet = Tweet.objects.filter(links=l).order_by('-created_at')[0]
                if tweet.created_at < first_t:
                    first_tweet = tweet
                    first_t = tweet.created_at
            except IndexError:
                pass
        return first_tweet

if __name__ == '__main__':
    description = '''Tweet screenshots.'''
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1, Copyright (c) 2010 Chinese Shot",
                          description=description)

    parser.add_option("-u", "--username", dest="username", type="string",
                      default="username",
                      help="Twitter username [default: %default].",
                      metavar="USERNAME")

    parser.add_option("-p", "--password", dest="password", type="string",
                      default="password",
                      help="Twitter password [default: %default].",
                      metavar="PASSWORD")

    parser.add_option("-l", "--log-config",
                      dest="log_config", 
                      default="/etc/link_shot_tweet_log.conf",
                      type="string",
                      help="Logging config file [default: %default].",
                      metavar="LOG_CONFIG")

    parser.add_option("-t", "--tweet", action="store_true", dest="tweet",
                      default=False)

    parser.add_option("-r", "--rank_time",
                      dest="rank_time", default="7200", type="int",
                      help="Time perioud of link ranks to sort in second [default: %default].",
                      metavar="RANK_TIME")

    parser.add_option("-n", "--number", dest="number", default=1, type="int",
                      help="Number of links to tweet [default:%default].",
                      metavar="NUMBER")

    (options,args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments")

    # walk around encoding issue
    reload(sys)
    sys.setdefaultencoding('utf-8') 

    logging.config.fileConfig(options.log_config)
    logger = logging.getLogger("tweet_shot")

    # get links; if options.tweet, tweet them
    links = TweetShot.getLinks(options.rank_time, options.number)
    for l in links:
        if options.tweet:
            logger.info("Tweet: [%d] %s", l.id, l.url)
            TweetShot.tweetLink(l)
        else:
            logger.info("Skip tweet: [%d] %s", l.id, l.url)
