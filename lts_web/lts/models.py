import re, random

from django.db import models
from datetime import timedelta, datetime

# Create your models here.

class Link(models.Model):
    id = models.AutoField(primary_key=True)
    url = models.URLField(max_length=2048)
    alias_of = models.ForeignKey('Link', null=True)

    def __unicode__(self):
        return self.url

    def getRoot(self):
        if self.alias_of is None:
            return self

        return self.alias_of.getRoot()

    def getAliases(self):
        # get child alias and self
        ls = Link.objects.filter(alias_of=self).all()
        aliases = []
        for l in ls:
            aliases += l.getAliases()
        aliases.append(self)
        return aliases

    def getRateSum(self):
        aliases = self.getAliases()
        r = 0
        for l in aliases:
            try:
                lr = LinkRate.objects.filter(link=l)[0]
                r += lr.rate
            except IndexError:
                pass
        return int(r)

    def getFirstTweet(self):
        ls = self.getRoot().getAliases()
        first_tweet = None
        first_t = None
        for l in ls:
            try:
                tweet = Tweet.objects.filter(links=l).order_by('created_at')[0]
                if first_t is None or tweet.created_at < first_t:
                    first_tweet = tweet
                    first_t = tweet.created_at
            except IndexError:
                pass
        if first_tweet is None:
            raise Tweet.DoesNotExist(u"Failed to get the first tweet of link: %s" % self.url)
        return first_tweet        

class Tweet(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    text = models.CharField(max_length=500)
    created_at = models.DateTimeField(db_index=True)
    user_screenname = models.CharField(max_length=100, db_index=True)
    links = models.ManyToManyField(Link, null=True)

    def __unicode__(self):
        return u"%s [%s] %s" % (self.user_screenname, self.created_at, self.text)

    class Meta:
        ordering = ['-created_at']

class LinkShot(models.Model):
#    id = models.IntegerField(primary_key=True)
    id = models.AutoField(primary_key=True)
    link = models.ForeignKey('Link', null=True)
    url = models.URLField(max_length=2048, null=True)
    thumbnail_url = models.URLField(max_length=2048, null=True)
    shot_time = models.DateTimeField(null=True, db_index=True)
    in_reply_to = models.ForeignKey(Tweet, null=True)
    title = models.TextField(max_length=2048)
    text = models.TextField()
    abstract = models.TextField()
    keywords = models.CharField(max_length=128)

    def __unicode__(self):
        return self.link.url

    def getRate(self):
        links = self.link.getAliases()
        r = 0
        for l in links:
            try:
                lr = LinkRate.filter(link=l)[0]
            except IndexError:
                continue
            r += lr.rate
        return r

    def thumbnailUrl(self):
        if self.thumbnail_url:
            return self.thumbnail_url
        if re.match(r'^http://twitpic.com/', self.url):
            return re.sub(r'^http://twitpic.com/(.+)$', r'http://twitpic.com/show/thumb/\1', self.url)
        return None

class ShotCache(models.Model):
    linkshot = models.ForeignKey('LinkShot', null=True, primary_key=True)
    image = models.ImageField(upload_to='shot_cache', null=True)

class ShotPublish(models.Model):
#    id = models.AutoField(primary_key=True)
    id = models.AutoField(primary_key=True)
    link = models.ForeignKey('Link', null=True)
    shot = models.ForeignKey('LinkShot', null=True)
    publish_time = models.DateTimeField(null=True, db_index=True)
    url = models.URLField(max_length=2048)
    site = models.CharField(max_length=128, null=True, db_index=True)

class ShotBlogPost(models.Model):
    id = models.AutoField(primary_key=True)
    link = models.ForeignKey('Link', null=True)
    shot = models.ForeignKey('LinkShot', null=True)
    publish_time = models.DateTimeField(null=True, db_index=True)
    url = models.URLField(max_length=2048)
    site = models.CharField(max_length=128, null=True, db_index=True)

class LinkRate(models.Model):
    id = models.AutoField(primary_key=True)
    link = models.ForeignKey('Link')
    rate = models.IntegerField(null=True, db_index=True)
    rating_time = models.DateTimeField(null=True, db_index=True)

    def __unicode__(self):
        return self.link.url

# class LinkRateSum(models.Model):
#     link = models.ForeignKey('Link', primary_key=True)
#     rate = models.IntegerField(null=True, db_index=True)
#     tweet = models.ForeignKey('Tweet')

#     def __unicode__(self):
#         return self.link.url

class TwitterAccount(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=128, null=True, blank=True)
    screen_name = models.CharField(max_length=128, db_index=True)
    location = models.CharField(max_length=256, null=True, blank=True)
    description = models.CharField(max_length=256, null=True, blank=True)
    profile_image_url = models.CharField(max_length=2048, null=True, blank=True)
    protected = models.BooleanField()
    utc_offset = models.IntegerField(null=True, blank=True)
    time_zone = models.CharField(max_length=32, null=True, blank=True)
    followers_count = models.IntegerField(default=0)
    friends_count = models.IntegerField(default=0)
    statuses_count = models.IntegerField(default=0)
    favourites_count = models.IntegerField(default=0)
    url = models.CharField(max_length=2048, null=True, blank=True)
    # app info
    password = models.CharField(max_length=128, null=True, blank=True)
    active = models.BooleanField(default=False)
    last_update = models.DateTimeField(null=False,auto_now=True)
    consumer_key = models.CharField(max_length=64, null=True, blank=True)
    consumer_secret = models.CharField(max_length=64, null=True, blank=True)

    def __unicode__(self):
        return self.screen_name

    @classmethod
    def random(cls):
        accounts = cls.objects.filter(active__exact=True)
        try:
            return accounts[random.randint(0, accounts.count()-1)]
        except IndexError:
            return None

class TwitterApiSite(models.Model):
    id = models.AutoField(primary_key=True)
    # api_protocol = models.CharField(max_length=128, default="http")
    api_host = models.CharField(max_length=128)
    api_root = models.CharField(max_length=128)
    # search_protocol = models.CharField(max_length=128, default="http")
    search_host = models.CharField(max_length=128)
    search_root = models.CharField(max_length=128)
    secure_api = models.BooleanField(default=False, db_index=True)
    active = models.BooleanField(default=False, db_index=True)

    def __unicode__(self):
        return "%s%s %s%s" % \
            (self.api_host, self.api_root,
             self.search_host, self.search_root)

    @classmethod
    def random(cls):
        sites = cls.objects.filter(active__exact=True)
        try:
            return sites[random.randint(0, sites.count()-1)]
        except IndexError:
            return None

class TwitterUser(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=128)
    screen_name = models.CharField(max_length=128, db_index=True)
    location = models.CharField(max_length=256, null=True)
    description = models.CharField(max_length=256, null=True)
    profile_image_url = models.CharField(max_length=2048, null=True)
    protected = models.BooleanField(default=False)
    utc_offset = models.IntegerField(null=True)
    time_zone = models.CharField(max_length=32, null=True)
    followers_count = models.IntegerField(null=True)
    friends_count = models.IntegerField(null=True)
    statuses_count = models.IntegerField(null=True)
    favourites_count = models.IntegerField(null=True)
    url = models.CharField(max_length=2048, null=True)
    last_update = models.DateTimeField(null=False, auto_now=True, db_index=True)

    def __unicode__(self):
        return self.screen_name

class TwitterUserExt(models.Model):
    twitteruser = models.OneToOneField(TwitterUser, primary_key=True)
    following_account = models.ManyToManyField(TwitterAccount,
                                               related_name='twitteruserext_follower_set',
                                               null=True, blank=True)
    followed_by_account = models.ManyToManyField(TwitterAccount,
                                                 related_name='twitteruserext_friend_set',
                                                 null=True, blank=True)
    link_rate = models.FloatField(null=True, db_index=True, blank=True)
    chinese_rate = models.FloatField(null=True, db_index=True, blank=True)
    allowing_shot = models.BooleanField(default=True, db_index=True)
    last_status_created_at = models.DateTimeField(null=True, db_index=True,
                                                  blank=True)
    last_update = models.DateTimeField(null=False, auto_now=False, db_index=True,
                                       default=datetime.fromtimestamp(0))

    def __unicode__(self):
        return self.twitteruser.screen_name

# class PendingTwitterUser(models.Model):
#     screen_name = models.CharField(max_length=128, primary_key=True)
#     twitteruser = models.ForeignKey('TwitterUser', null=True)
#     enqueue_time = models.DateTimeField(null=False,auto_now=True, db_index=True)

#     def __unicode__(self):
#         return self.screen_name

#     @classmethod
#     def addPending(cls, scrn_name):
#         try:
#             puser = cls.objects.get(screen_name = scrn_name)
#         except cls.DoesNotExist:
#             puser = cls(screen_name = scrn_name)
#             puser.save()

#         if puser.twitteruser is None:
#             try:
#                 user = TwitterUser.objects.get(screen_name = scrn_name)
#                 puser.twitteruser = user
#                 puser.save()
#             except Twitteruser.DoesNotExist:
#                 pass

#         return puser

class ImageSitePattern(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=128)
    pattern = models.CharField(max_length=1024)

    def __unicode__(self):
        return self.name

class IgnoredSitePattern(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=128)
    pattern = models.CharField(max_length=1024)

    def __unicode__(self):
        return self.name
    
class SizedCanvasSitePattern(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=128)
    pattern = models.CharField(max_length=1024)
    width = models.IntegerField(null=True)
    height = models.IntegerField(null=True)

    
