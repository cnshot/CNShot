#!/usr/bin/python

import stompy, pickle, memcache, sys, traceback, logging, logging.config, os, \
    twitpic, twitter, wordpresslib

from optparse import OptionParser
from datetime import datetime, timedelta
from django.core.exceptions import ObjectDoesNotExist
from django.template import Context, Template
from config import Config, ConfigMerger

#os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from lts.models import Link, LinkShot, ShotBlogPost, Tweet, LinkRate

class BlogPost:
    @classmethod
    def getLinks(cls, rank_time, count):
        tt = datetime.utcnow() - timedelta(seconds = rank_time);
        lrs = LinkRate.objects.extra(select={'blog_posted':"SELECT COUNT(*) FROM lts_shotblogpost WHERE lts_shotblogpost.link_id=lts_linkrate.link_id",
                          'shot':"SELECT COUNT(*) FROM lts_linkshot WHERE lts_linkshot.link_id=lts_linkrate.link_id"}).filter(rating_time__gte=tt)

        logger.debug("Query for links to post: %s", lrs.query.as_sql())
            
        lrs = filter(lambda x: x.blog_posted==0 and x.shot>0, lrs)
        
        sorted_lrs = sorted(lrs, lambda x,y: y.link.getRateSum()-x.link.getRateSum())
        return map(lambda x: x.link.getRoot(), sorted_lrs[:count])

    @classmethod
    def postLink(cls, link):
        t = cls.getFirstTweet(link)
        if t is None:
            logger.warn("Failed to get tweet of link: %s", link.url)
            return

        try:
            ls = LinkShot.objects.filter(link=link)[0]
        except IndexError:
            logger.warn("Failed to get shot of link: %s", link.url)
            return

        title_tmp = Template(cfg.blog_post.title_template)
        description_tmp = Template(cfg.blog_post.description_template)

        c = Context({"link": link, 
                     "tweet": t,
                     "link_shot": ls})

        wp = wordpresslib.WordPressClient(cfg.blog_post.xmlrpc_url,
                                          cfg.blog_post.username,
                                          cfg.blog_post.password)
        wp.selectBlog(cfg.blog_post.blog_id)
        post = wordpresslib.WordPressPost()
        post.title = str(title_tmp.render(c).encode('utf-8'))
        post.description = str(description_tmp.render(c).encode('utf-8'))
        # logger.debug("Title: %s", post.title)
        # logger.debug("Description: %s", post.description)
        # import pickle
        # logger.debug("Post: %s", pickle.dumps(post))

        idPost = wp.newPost(post, True)

        logger.info("Posted: [%d] %s %s",
                    idPost, ls.title, t.text.encode('utf-8'))

        # update ShotBlogPost
        ShotBlogPost.objects.filter(link=link).delete()
        # url = "http://twitter.com/" + rts.user.screen_name + "/status/" + str(rts.id)
        sbp = ShotBlogPost(link=link, shot=ls, publish_time=datetime.utcnow(),
                           url=post.link, site=cfg.blog_post.xmlrpc_url)
        sbp.save()

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
    description = '''Blog post screenshots.'''
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
    # cfg.addNamespace(options,'common')

    # walk around encoding issue
    reload(sys)
    sys.setdefaultencoding('utf-8') 

    logging.config.fileConfig(cfg.common.log_config)
    logger = logging.getLogger("blog_post")

    # get links; if options.post, post them
    links = BlogPost.getLinks(cfg.blog_post.rank_time, cfg.blog_post.number)
    for l in links:
        if cfg.blog_post.post:
            logger.info("Post: [%d] %s", l.id, l.url)
            BlogPost.postLink(l)
        else:
            logger.info("Skip post: [%d] %s", l.id, l.url)
