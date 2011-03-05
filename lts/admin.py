from django.contrib import admin

# Site patterns
from lts.models import ImageSitePattern, IgnoredSitePattern, \
    SizedCanvasSitePattern, \
    Link, Tweet, LinkShot, LinkRate, ShotPublish, TwitterUser, TwitterUserExt, \
    TwitterAccount, TwitterApiSite, TwitterApiAuth, ShotBlogPost, \
    ShotCache, TweetFreqHashCache, RTPublish

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
    list_display = ('id', 'url', 'thumbnail_url', 'link', 'tweet', 'rate',
                    'shot_time', 'title', 'keywords')
    search_fields = ['url', 'link__url', 'keywords']
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
        except (AttributeError, LinkShot.DoesNotExist):
            return ''
    tweet.short_description = 'Tweet'

admin.site.register(LinkShot, LinkShotAdmin)

class ShotCacheAdmin(admin.ModelAdmin):
    list_display = ('linkshot', 'image')

admin.site.register(ShotCache, ShotCacheAdmin)

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
        except (IndexError, Tweet.DoesNotExist):
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
        except (AttributeError, ShotPublish.DoesNotExist):
            return ''
    tweet.short_description = 'Tweet'

admin.site.register(ShotPublish, ShotPublishAdmin)

class ShotBlogPostAdmin(admin.ModelAdmin):
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
        except (AttributeError, ShotBlogPost.DoesNotExist):
            return ''
    tweet.short_description = 'Tweet'

admin.site.register(ShotBlogPost, ShotBlogPostAdmin)

class TwitterUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'screen_name', 
                    'followers_count','friends_count',
                    'statuses_count','favourites_count',
                    'last_update',
                    'link_rate', 'chinese_rate',
                    'following', 'followed_by',
                    )
    search_fields = ['name', 'screen_name']

    def link_rate(self, obj):
        return obj.twitteruserext.link_rate

    def chinese_rate(self, obj):
        return obj.twitteruserext.chinese_rate

    def following(self, obj):
        return ', '.join(map(lambda x: x.screen_name, obj.twitteruserext.following_account.all()))

    def followed_by(self, obj):
        return ', '.join(map(lambda x: x.screen_name, obj.twitteruserext.followed_by_account.all()))

admin.site.register(TwitterUser, TwitterUserAdmin)

class TwitterUserExtAdmin(admin.ModelAdmin):
    list_display = ('twitteruser',
                    'link_rate', 'chinese_rate',
                    'allowing_shot', 'last_update','ignored',
                    'following', 'followed_by',
                    )
    search_fields = ['twitteruser__name', 'twitteruser__screen_name']
    raw_id_fields = ['following_account', 'followed_by_account']

    def following(self, obj):
        return ', '.join(map(lambda x: x.screen_name, obj.following_account.all()))

    def followed_by(self, obj):
        return ', '.join(map(lambda x: x.screen_name, obj.followed_by_account.all()))

admin.site.register(TwitterUserExt, TwitterUserExtAdmin)

# class PendingTwitterUserAdmin(admin.ModelAdmin):
#     list_display = ("screen_name", "enqueue_time", "followers", "link_rate", "chinese_rate", "last_update")
#     search_fields = ["screen_name", "twitteruser__name"]

#     def followers(self, obj):
#         try:
#             return obj.twitteruser.followers
#         except(AttributeError, PendingTwitterUser.DoesNotExist):
#             return None

#     def link_rate(self, obj):
#         try:
#             return obj.twitteruser.twitteruserext.link_rate
#         except(AttributeError, PendingTwitterUser.DoesNotExist):
#             return None

#     def chinese_rate(self, obj):
#         try:
#             return obj.twitteruser.twitteruserext.chinese_rate
#         except(AttributeError, PendingTwitterUser.DoesNotExist):
#             return None

#     def last_update(self, obj):
#         try:
#             return obj.twitteruser.twitteruserext.last_update
#         except(AttributeError, PendingTwitterUser.DoesNotExist):
#             return None

# admin.site.register(PendingTwitterUser, PendingTwitterUserAdmin)
    
class TwitterAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'screen_name', 'active',
                    'followers_count','friends_count',
                    'statuses_count','favourites_count',
                    'last_update', 'password', 'last_update',
                    'consumer_key', 'consumer_secret',
                    'access_key', 'access_secret',
                    'since')
    search_fields = ['name', 'screen_name']

admin.site.register(TwitterAccount, TwitterAccountAdmin)

class TwitterApiSiteAdmin(admin.ModelAdmin):
    list_display = ('id', 'active', 'secure_api', 'api_host', 'api_root',
                    'search_host', 'search_root')
    search_fields = ['api_host', 'api_root', 'search_host', 'search_root']

admin.site.register(TwitterApiSite, TwitterApiSiteAdmin)
                    
class TwitterApiAuthAdmin(admin.ModelAdmin):
    list_display = ('account', 'api_site', 'active',
                    'screen_name', 'password',
                    'consumer_key', 'consumer_secret',
                    'access_key', 'access_secret',
                    'last_update')
    search_fields = ['screen_name']

admin.site.register(TwitterApiAuth, TwitterApiAuthAdmin)

class TweetFreqHashCacheAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_screenname', 'tweet_text', 'freq_hash')

    def id(self, obj):
        try:
            return obj.tweet.id
        except (AttributeError, TweetFreqHashCacheAdmin.DoesNotExist):
            return ''
    id.short_description = 'ID'

    def user_screenname(self, obj):
        try:
            return obj.tweet.user_screenname
        except (AttributeError, TweetFreqHashCacheAdmin.DoesNotExist):
            return ''
    user_screenname.short_description = 'Screen Name'

    def tweet_text(self, obj):
        try:
            return obj.tweet.text
        except (AttributeError, TweetFreqHashCacheAdmin.DoesNotExist):
            return ''
    tweet_text.short_description = 'Tweet'

admin.site.register(TweetFreqHashCache, TweetFreqHashCacheAdmin)

class RTPublishAdmin(admin.ModelAdmin):
    list_display = ('id', 'status_id', 'text', 'created_at', 'in_reply_to_status_id')
    search_fields = ['text']

admin.site.register(RTPublish, RTPublishAdmin)
