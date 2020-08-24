from django.db import models


class EducationMessage(models.Model):
    peer_id = models.IntegerField()
    message = models.CharField(max_length=300)


class Trigger(models.Model):
    trigger = models.CharField(max_length=300)
    answer = models.CharField(max_length=300)


class Picture(models.Model):
    vk_code = models.CharField(max_length=100)
    url = models.CharField(max_length=200)