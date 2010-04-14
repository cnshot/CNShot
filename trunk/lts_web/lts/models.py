from django.db import models

# Create your models here.

class Tweet(models.Model):
    id = models.IntegerField(primary_key=True)
    text = models.CharField(max_length=500)
    created_at = models.DateTimeField()
    user_screenname = models.CharField(max_length=100)
    links = models.ManyToManyField(Link)

class Link(models.Model):
    url = models.CharField(primary_key=True, max_length=2048)

class LinkShot(models.Model):
    link = models.ForeignKey('Link')
    shot_time = models.DateTimeField('date published')

class Choice(models.Model):
    poll = models.ForeignKey('LinkShot')
    choice = models.CharField(max_length=200)
    votes = models.IntegerField()
