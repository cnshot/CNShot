#!/usr/bin/python

import sys, traceback, twitpic, urllib2, re, pycurl, simplejson, StringIO

from datetime import datetime, timedelta
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
from pyTweetPhoto import pyTweetPhoto
from lxml import etree

#os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from lts.models import Tweet, LinkRate, ShotCache

class ImageUploader:
    def __init__(self, uploader_list_cfg):
        self.uploaders = []
        for c in uploader_list_cfg:
            f = None
            if c == 'twitpic':
                f = self.post_image_twitpic
            elif c == 'moby':
                f = self.post_image_moby
            elif c == 'tweetphoto':
                f = self.post_image_tweetphoto
            elif c == 'twitgoo':
                f = self.post_image_twitgoo
            elif c == 'imj.tw':
                f = self.post_image_imjtw
            elif c == 'imgur':
                f = self.post_image_imgur
            if f is not None:
                logger.debug("Enabling uploader: %s", c)
                self.uploaders.append(f)

    def upload(self, image_path, s):
        for f in self.uploaders:
            twitpic_url, thumbnail_url = f(image_path, s)
            if twitpic_url is not None:
                return twitpic_url, thumbnail_url
        return None, None

    def post_image_twitpic(self, image_path, s):
        twitpic_url = None
        thumbnail_url = None
        image_url = None

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
                image_url = re.sub(r'^http://twitpic.com/(.+)$',
                                   r'http://twitpic.com/show/large/\1',
                                   twitpic_url)

            logger.debug("Twitpic posted: %s %s", image_path, s)
        except:
            logger.error("Failed to tweet image: %s", sys.exc_info()[0])
            logger.error('-'*60)
            logger.error("%s", traceback.format_exc())
            logger.error('-'*60)
        finally:
            return image_url, thumbnail_url

    def post_image_moby(self, image_path, s):
        image_url = None
        thumbnail_url = None

        try:
            logger.debug("Post image to moby: %s %s", image_path, s)

            datagen, headers = multipart_encode({'u':cfg.common.moby_username,
                                                 'p':cfg.common.moby_password,
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
                logger.error("Failed to upload image: %d %s",
                             response.code, image_url)
                image_url = None
                thumbnail_url = None
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
            
            p = re.compile('www\.mobypicture\.com/images/user', re.VERBOSE)
            thumbnail_url = p.sub(r'a2.img.mobypicture.com', thumbnail_url)
            image_url = thumbnail_url.replace('_small', '_full')

            logger.debug("Moby posted: %s %s", image_path, s)
        except:
            logger.error("Failed to tweet image: %s", sys.exc_info()[0])
            logger.error('-'*60)
            logger.error("%s", traceback.format_exc())
            logger.error('-'*60)
        finally:
            return image_url, thumbnail_url

    def post_image_twitgoo(self, image_path, s):
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

    def post_image_tweetphoto(self, image_path, s):
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

    def post_image_imjtw(self, image_path, s):
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

    def post_image_imgur(self, image_path, s):
        image_url = None
        thumbnail_url = None

        try:
            logger.debug("Post image to imgur: %s %s", image_path, s)

            b = StringIO.StringIO()
            c = pycurl.Curl()
            values = [("key", cfg.common.imgur_api_key),
                      ("image", (c.FORM_FILE, str(image_path)))]
            c.setopt(c.URL, "http://api.imgur.com/2/upload.json")
            c.setopt(c.HTTPPOST, values)
            c.setopt(pycurl.WRITEFUNCTION, b.write)
            c.perform()

            r = c.getinfo(pycurl.HTTP_CODE)
            if r < 200 or r >= 300:
                return None, None
            
            j = simplejson.loads(b.getvalue())
            thumbnail_url = j['upload']['links']['small_square']
            image_url = j['upload']['links']['original']

            logger.debug("imgur posted: %s %s", image_path, s)
        except:
            logger.error("Failed to tweet image: %s", sys.exc_info()[0])
            logger.error('-'*60)
            logger.error("%s", traceback.format_exc())
            logger.error('-'*60)
        finally:
            return image_url, thumbnail_url

class ImageUpload:
    @classmethod
    def uploadImages(cls):
        register_openers()
        iu = ImageUploader(cfg.image_upload.uploaders)

        def link_filter(l):
            ls = l.getLinkShot()
            return (ls is not None and ls.url is None)

        # get links; if options.tweet, tweet them
        links = LinkRate.orderedLinks(datetime.utcnow() - timedelta(seconds = cfg.image_upload.rank_time),
                                      filter_func=link_filter)

        uploaded = 0
        for l in links:
            if uploaded >= cfg.image_upload.number:
                break

            try:
#                l = ls.link.getRoot()
                t = l.getFirstTweet()
#                ls = LinkShot.objects.filter(link=l)[0]
                ls = l.getLinkShot()
                if ls.url is not None:
                    continue

                cs = ShotCache.objects.get(linkshot=ls)

                rt_text = u'RT @' + t.user_screenname + u': ' + t.text

                url, thumbnail_url = iu.upload(cs.image.path, rt_text.encode('utf-8'))
                if url is None:
                    logger.warn("Failed to post image: %s", l.url)
                    uploaded += 1
                    continue

                ls.url = url
                ls.thumbnail_url = thumbnail_url
                ls.save()

                uploaded += 1
            except (Tweet.DoesNotExist, IndexError, ShotCache.DoesNotExist), e:
                logger.warn("Failed to get tweet info of link: %s %s", ls.link.getRoot().url, e)

def run(_cfg, _logger):
    global cfg, logger
    cfg = _cfg
    logger = _logger

    ImageUpload.uploadImages()
