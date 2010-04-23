from django.contrib import admin

# Site patterns
from lts_web.lts.models import ImageSitePattern, IgnoredSitePattern, \
    SizedCanvasSitePattern, \
    Link, Tweet, LinkShot, LinkRate, ShotPublish, TwitterUser, TwitterUserExt, \
    TwitterAccount, TwitterApiSite

class SiteAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'pattern')
    search_fields = ['name', 'pattern']

admin.site.register(ImageSitePattern, SiteAdmin)
admin.site.register(IgnoredSitePattern, SiteAdmin)

class SizedCanvasSitePatternAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'pattern', 'width', 'height')
    search_fields = ['name', 'pattern']

admin.site.register(SizedCanvasSitePattern, SizedCanvasSitePatternAdmin)

class LinkAdmin(admin.ModelAdmin):
    list_display = ('id', 'url', 'alias_of', 'rate')
    search_fields = ['url', 'alias_of__url']
    raw_id_fields = ["alias_of"]

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
    raw_id_fields = ["links"]

admin.site.register(Tweet, TweetAdmin)

class LinkShotAdmin(admin.ModelAdmin):
    list_display = ('id', 'url', 'link', 'tweet', 'rate', 'shot_time', 'title')
    search_fields = ['url', 'link__url']
    raw_id_fields = ("link", "in_reply_to")

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
    raw_id_fields = ['link']

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
    raw_id_fields = ['link', 'shot']

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

class TwitterUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'screen_name', 
                    'followers_count','friends_count',
                    'statuses_count','favourites_count',
                    'last_update')
    search_fields = ['name', 'screen_name']

admin.site.register(TwitterUser, TwitterUserAdmin)

class TwitterUserExtAdmin(admin.ModelAdmin):
    list_display = ('twitteruser',
                    'following_account', 'followed_by_account',
                    'link_rate', 'chinese_rate',
                    'allowing_shot', 'last_update')
    search_fields = ['twitteruser__name', 'twitteruser__screen_name']

admin.site.register(TwitterUserExt, TwitterUserExtAdmin)

class TwitterAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'screen_name', 'active',
                    'followers_count','friends_count',
                    'statuses_count','favourites_count',
                    'last_update', 'password', 'last_update')
    search_fields = ['name', 'screen_name']

admin.site.register(TwitterAccount, TwitterAccountAdmin)

class TwitterApiSiteAdmin(admin.ModelAdmin):
    list_display = ('id', 'active', 'api_protocol', 'api_host', 'api_root',
                    'search_protocol', 'search_host', 'search_root')
    search_fields = ['api_host', 'api_root', 'search_host', 'search_root']

admin.site.register(TwitterApiSite, TwitterApiSiteAdmin)
                    
