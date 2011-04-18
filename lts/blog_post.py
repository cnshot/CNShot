#!/usr/bin/python

import sys, logging.config, os, xmlrpclib, buzz

from optparse import OptionParser
from datetime import datetime, timedelta
from django.template import Context, Template
from config import Config
from xml.parsers.expat import ExpatError

from lts.models import LinkShot, ShotBlogPost, Tweet, LinkRate

try:
  # This is where simplejson lives on App Engine
  from django.utils import simplejson
except (ImportError):
  import simplejson
  
class ExtBuzzClient(buzz.Client):
    def create_post(self, post):
        api_endpoint = buzz.API_PREFIX + "/activities/@me/@self"
        api_endpoint += "?alt=json"
        json_string = simplejson.dumps({'data': post._json_output})
        logging.debug('Creating post: %s' % json_string)

        return buzz.Result._parse_post(json_string)

class WordPressPoster:
    def __init__(self, _cfg, _logger):
        self.cfg = _cfg
        self.logger = _logger
        
    def post(self, t, link, ls):
        c = Context({"link": link, 
                     "tweet": t,
                     "link_shot": ls})        
        
        title_tmp = Template(self.cfg.blog_post.title_template)
        description_tmp = Template(self.cfg.blog_post.description_template)        
        
        content = {'title':str(title_tmp.render(c).encode('utf-8')),
                   'description':str(description_tmp.render(c).encode('utf-8')),
                   'mt_keywords':ls.keywords}

        wp_server = xmlrpclib.Server(self.cfg.blog_post.xmlrpc_url)
        try:
            post_id = wp_server.metaWeblog.newPost(self.cfg.blog_post.blog_id,
                                                   self.cfg.blog_post.username,
                                                   self.cfg.blog_post.password,
                                                   content,
                                                   1)
            post = wp_server.metaWeblog.getPost(post_id,
                                                self.cfg.blog_post.username,
                                                self.cfg.blog_post.password)
        except ExpatError:
            self.logger.warn('Blog post failed, try to recover from recent posts ...')
            try:
                posts = wp_server.metaWeblog.getRecentPosts(self.cfg.blog_post.blog_id,
                                                            self.cfg.blog_post.username,
                                                            self.cfg.blog_post.password,
                                                            self.cfg.blog_post.recent_posts)
            except ExpatError:
                self.logger.warn('Failed to get recent posts.')
                return None
            
            matched_posts = filter(lambda x: x['description'] == content, posts)
            if len(matched_posts)>0:
                self.logger.info('Found post in recent posts')
                post = matched_posts[0]
            else:
                self.logger.info("Didn't find post in recent posts")
                return None
        
        self.logger.info("Posted: [%s]",
                         post_id)
        return post['link']

class GoogleBuzzPoster:
    def __init__(self, _cfg, _logger):
        self.cfg = _cfg
        self.logger = _logger    

    def post(self, t, link, ls):
        client = ExtBuzzClient()
        client.build_oauth_consumer(self.cfg.blog_post.buzz_client_id,
                                    self.cfg.blog_post.buzz_client_secret)
        client.oauth_scopes.append(buzz.FULL_ACCESS_SCOPE)
        # Retrieve the persisted access token
        client.build_oauth_access_token(self.cfg.blog_post.buzz_access_token_key, 
                                        self.cfg.blog_post.buzz_access_token_secret)
        
        screenshot_attachment = buzz.Attachment(type='photo',
                                                title=ls.title,
                                                url=ls.thumbnail_url)
        article_attachment = buzz.Attachment(type='article',
                                             title=ls.title,
                                             uri=link.url)
        post = buzz.Post(content=t.text,
                         attachments=[screenshot_attachment, article_attachment])
        r = client.create_post(post)
        
        return r.link

class PosterFactory:
    def __init__(self, _cfg, _logger):
        self.cfg = _cfg
        self.logger = _logger
        
    def getPoster(self):
        if self.cfg.blog_post.poster == 'wordpress':
            return WordPressPoster(self.cfg, self.logger)
        elif self.cfg.blog_post.poster == 'buzz':
            return GoogleBuzzPoster(self.cfg, self.logger)

class BlogPost:
    @classmethod
    def getLinks(cls, rank_time):
        tt = datetime.utcnow() - timedelta(seconds = rank_time);
        lrs = LinkRate.objects.extra(select={'blog_posted':"""
SELECT COUNT(*)
FROM lts_shotblogpost
WHERE lts_shotblogpost.link_id=lts_linkrate.link_id
"""
                                             ,
                          'shot':"""
SELECT COUNT(*)
FROM lts_linkshot
WHERE lts_linkshot.link_id=lts_linkrate.link_id
  AND lts_linkshot.thumbnail_url IS NOT NULL
"""
                                             }).filter(rating_time__gte=tt)

        logger.debug("Query for links to post:\n%s", str(lrs.query))
            
        lrs = filter(lambda x: x.blog_posted==0 and x.shot>0, lrs)
        
        sorted_lrs = sorted(lrs,
                            lambda x,y: y.link.getRateSum()-x.link.getRateSum())
        return map(lambda x: x.link.getRoot(), sorted_lrs)

    @classmethod
    def postLink(cls, link):
        t = cls.getFirstTweet(link)
        if t is None:
            logger.warn("Failed to get tweet of link: %s", link.url)
            return None

        try:
            ls = LinkShot.objects.filter(link=link)[0]
        except IndexError:
            logger.warn("Failed to get shot of link: %s", link.url)
            return None

        if not ls.title:
            # just a fake for blog title
            # don't save it
            ls.title = t.text
        
        poster_factory = PosterFactory(cfg, logger)
        post_url = poster_factory.getPoster().post(t, link, ls)
                
        if post_url:
            # update ShotBlogPost
            ShotBlogPost.objects.filter(link=link).delete()
            sbp = ShotBlogPost(link=link, shot=ls, publish_time=datetime.utcnow(),
                               url=post_url, site=cfg.blog_post.xmlrpc_url)
            sbp.save()
    
            return sbp
        else:
            return None

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
    def blogPost(cls):
        # get links; if options.post, post them
        links = cls.getLinks(cfg.blog_post.rank_time)
        posted = 0
        for l in links:
            if posted >= cfg.blog_post.number:
                break

            if cfg.blog_post.post:
                logger.info("Post: [%d] %s", l.id, l.url)
                sbp = cls.postLink(l)
                if sbp is not None:
                    posted += 1
                else:
                    logger.warn("Failed to post: [%d] %s", l.id, l.url)
            else:
                logger.info("Skip post: [%d] %s", l.id, l.url)

        logger.info("Posted %d shots.", posted)

def run(_cfg, _logger):
    global cfg, logger
    cfg = _cfg
    logger = _logger

    BlogPost.blogPost()

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

    # walk around encoding issue
    reload(sys)
    sys.setdefaultencoding('utf-8') #@UndefinedVariable

    logging.config.fileConfig(cfg.common.log_config)
    logger = logging.getLogger("blog_post")

    BlogPost.blogPost()
