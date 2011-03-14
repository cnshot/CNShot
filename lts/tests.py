#coding:utf-8
'''
Created on 2011-3-13

@author: yale
'''

import unittest
import twitter_utils

from django.conf import settings
from config import Config

class TweetTest(unittest.TestCase):
    def testTweet(self):
        cfg = Config(file(settings.LTS_CONFIG))
        api = twitter_utils.createCfgApi(cfg.common)
#        rt_text = 'http://is.gd/N7U1Bo RT @bonnae: RT @tuzzi: [超強的紐時flash報導] RT @nytimes More #Japan: 福島核電廠危機flash詳細示意圖 http://nyti.ms/e8J5tN'
        rt_text = 'http://www.google.com'
        rts = api.update_status(status = rt_text[0:140])
        if hasattr(rts, 'error'):
            print "\nrts.error = %s" % rts.error
        self.assertFalse(hasattr(rts, 'error'))
        self.assertEqual(rt_text[0:140], rts.text)
        
#    def testJSONTweet(self):
#        import urllib
#        
#        cfg = Config(file(settings.LTS_CONFIG))
#        api = twitter_utils.createCfgApi(cfg.common)
#        rt_text = 'http://is.gd/N7U1Bo RT @bonnae: RT @tuzzi: [超強的紐時flash報導] RT @nytimes More #Japan: 福島核電廠危機flash詳細示意圖 http://nyti.ms/e8J5tN'
#        rts = api.update_status(post_data=urllib.urlencode(dict([('status',rt_text[0:140])])))
#        if hasattr(rts, 'error'):
#            print "\nrts.error = %s" % rts.error
#        self.assertFalse(hasattr(rts, 'error'))
#        self.assertEqual(rt_text[0:140], rts.text)

    def testBitLy(self):
        import logging, tweet_shot
        tweet_shot.logger = logging
        url = tweet_shot.shortenURL('http://cnshot.wordpress.com/2011/03/14/%e8%83%a1%e6%99%b4%e8%88%ab%ef%bc%9a%e4%ba%ba%e5%9c%a8%e6%9d%b1%e4%ba%ac%e5%a4%a7%e5%9c%b0%e9%9c%87-%e5%90%8d%e4%ba%ba%e5%a0%82-%e6%84%8f%e8%a6%8b%e8%a9%95%e8%ab%96-%e8%81%af%e5%90%88%e6%96%b0/',
                                    shortener = 'http://tinyurl.com/api-create.php', query='url')
        print "\nurl: %s" % url
        self.assertNotEqual(url, None)

        

                                
        