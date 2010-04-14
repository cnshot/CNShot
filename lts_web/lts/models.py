from django.db import models

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

class Tweet(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    text = models.CharField(max_length=500)
    created_at = models.DateTimeField()
    user_screenname = models.CharField(max_length=100)
    links = models.ManyToManyField(Link, null=True)

    def __unicode__(self):
        return u"%s [%s] %s" % (self.user_screenname, self.created_at, self.text)

class LinkShot(models.Model):
#    id = models.IntegerField(primary_key=True)
    id = models.AutoField(primary_key=True)
    link = models.ForeignKey('Link', null=True)
    url = models.URLField(max_length=2048, null=True)
    shot_time = models.DateTimeField(null=True)
    in_reply_to = models.ForeignKey(Tweet, null=True)

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

class ShotPublish(models.Model):
#    id = models.AutoField(primary_key=True)
    id = models.AutoField(primary_key=True)
    link = models.ForeignKey('Link', null=True)
    shot = models.ForeignKey('LinkShot', null=True)
    publish_time = models.DateTimeField(null=True)
    url = models.URLField(max_length=2048)
    site = models.CharField(max_length=128, null=True)

class LinkRate(models.Model):
    id = models.AutoField(primary_key=True)
    link = models.ForeignKey('Link')
    rate = models.IntegerField(null=True)
    rating_time = models.DateTimeField(null=True)

    def __unicode__(self):
        return self.link.url

class TwitterUser(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=128)
    screen_name = models.CharField(max_length=128)
    location = models.CharField(max_length=256, null=True)
    description = models.CharField(max_length=256, null=True)
    profile_image_url = models.CharField(max_length=2048, null=True)
    protected = models.BooleanField()
    utc_offset = models.IntegerField(null=True)
    time_zone = models.CharField(max_length=32, null=True)
    followers_count = models.IntegerField(null=True)
    friends_count = models.IntegerField(null=True)
    statuses_count = models.IntegerField(null=True)
    favourites_count = models.IntegerField(null=True)
    url = models.CharField(max_length=2048, null=True)

    def __unicode__(self):
        return self.screen_name

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
    
