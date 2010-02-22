from django.contrib import admin

# Site patterns
from lts_web.lts.models import ImageSitePattern, IgnoredSitePattern

# Running time models
from lts_web.lts.models import Link, Tweet, LinkShot, LinkRate

admin.site.register(ImageSitePattern)
admin.site.register(IgnoredSitePattern)

admin.site.register(Link)
admin.site.register(Tweet)
admin.site.register(LinkShot)
admin.site.register(LinkRate)
