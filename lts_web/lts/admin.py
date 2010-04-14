from django.contrib import admin

# Site patterns
from lts_web.lts.models import ImageSitePattern, IgnoredSitePattern, \
    Link, Tweet, LinkShot, LinkRate, ShotPublish, TwitterUser

class SiteAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'pattern')
    search_fields = ['name', 'pattern']

admin.site.register(ImageSitePattern, SiteAdmin)
admin.site.register(IgnoredSitePattern, SiteAdmin)

class LinkAdmin(admin.ModelAdmin):
    list_display = ('id', 'url', 'alias_of', 'rate')
    search_fields = ['url', 'alias_of__url']

    def rate(self, obj):
        try:
            return obj.getRoot().getRateSum()
        except LinkRate.DoesNotExist:
            return 0
    rate.short_description = 'Rate'

admin.site.register(Link, LinkAdmin)

class TweetAdmin(admin.ModelAdmin):
    list_display = ('id', 'text', 'created_at', 'user_screenname')
    search_fields = ['text', 'user_screenname']

admin.site.register(Tweet, TweetAdmin)

class LinkShotAdmin(admin.ModelAdmin):
    list_display = ('id', 'url', 'link', 'tweet', 'rate', 'shot_time',)
    search_fields = ['url', 'link__url']

    def rate(self, obj):
        try:
            return obj.link.getRoot().getRateSum()
        except LinkRate.DoesNotExist:
            return 0
    rate.short_description = 'Rate'

    def tweet(self, obj):
        try:
            return obj.in_reply_to.text
        except AttributeError, DoesNotExist:
            return ''
    tweet.short_description = 'Tweet'

admin.site.register(LinkShot, LinkShotAdmin)

class LinkRateAdmin(admin.ModelAdmin):
    list_display = ('id', 'link_url', 'tweet', 'rate', 'rating_time',)
#    list_filter = ('rate', )
    search_fields = ['link__url']

    def link_url(self, obj):
      return ("%s" % (obj.link.url))
    link_url.short_description = 'Link URL'

    def tweet(self, obj):
        try:
            return Tweet.objects.filter(links=obj.link).all()[0]
        except IndexError, DoesNotExist:
            return ''
    tweet.short_description = 'Tweet'
admin.site.register(LinkRate, LinkRateAdmin)

class ShotPublishAdmin(admin.ModelAdmin):
    list_display = ('id', 'tweet', 'rate', 'url', 'link', 'publish_time',)
    search_fields = ['url', 'link__url']

    def rate(self, obj):
        try:
            return obj.link.getRoot().getRateSum()
        except LinkRate.DoesNotExist:
            return 0
    rate.short_description = 'Rate'

    def tweet(self, obj):
        try:
            return obj.shot.in_reply_to.text
        except AttributeError, DoesNotExist:
            return ''
    tweet.short_description = 'Tweet'

admin.site.register(ShotPublish, ShotPublishAdmin)

admin.site.register(TwitterUser)
