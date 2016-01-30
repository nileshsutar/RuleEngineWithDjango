from __future__ import unicode_literals


from datetime import datetime

from django.db import models

# Create your models here.
class Rule(models.Model):
        rule_type = models.CharField("rule_type", max_length=30)
        rule_name = models.CharField("rule_name", max_length=30, unique=True)
        area_url = models.TextField("area_url")
        featureurls = models.ManyToManyField('FeatureURLs', null=False, blank=False, related_name="rules")
        scheduler = models.ForeignKey('RuleScheduler', related_name='rules', on_delete=models.CASCADE)
        createddate = models.DateTimeField('createddate', default=datetime.now)
        emailid = models.EmailField("emailid", max_length=250)

	class Meta:
		db_table = 'rules'


class FeatureURLs(models.Model):
        feature_url = models.TextField("feature_url", max_length=5000)
        featureurlfields = models.ManyToManyField('FeatureFields', null=False, blank=False, related_name='featureurls')
	
	class Meta:
		db_table = 'featureurls'

class FeatureFields(models.Model):
        feature_url_field = models.CharField("feature_url_fields", max_length=50)
        field_index = models.PositiveIntegerField("field_index")

	class Meta:
		db_table = 'featurefields'

class RuleScheduler(models.Model):
        schedulertime = models.DateTimeField('schedulertime', default=datetime.now)
        schedulertype = models.CharField("schedulertype", max_length=20)

	class Meta:
		db_table = 'rulescheduler'
