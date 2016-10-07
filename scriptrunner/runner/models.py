from __future__ import unicode_literals


from datetime import datetime

from django.db import models
from djcelery.models import PeriodicTask, IntervalSchedule

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

class RuleExecutionSummary(models.Model):
	rule_name = models.CharField("rule_name", max_length=30)
	rule_id = models.PositiveIntegerField("rule_id")
	starttime = models.DateTimeField("starttime", default=datetime.now)
	stoptime = models.DateTimeField("stoptime", default=datetime.now)
	execution_status = models.CharField("execution_status", max_length=20)
	filelocation = models.CharField("filelocation", max_length=255)
	error_message = models.CharField("error_message", max_length=255)

	class Meta:
		db_table = "ruleexecutionsummary"


class TaskScheduler(models.Model):

    periodic_task = models.ForeignKey(PeriodicTask)

    @staticmethod
    def schedule_every(task_name, period, every, args=None, kwargs=None):
        """ 
        schedules a task by name every "every" "period". So an example call would be:
        TaskScheduler('mycustomtask', 'seconds', 30, [1,2,3]) 
        that would schedule your custom task to run every 30 seconds with the arguments 1,2 and 3 passed to the actual task. 
        """
        permissible_periods = ['days', 'hours', 'minutes', 'seconds']
        if period not in permissible_periods:
            raise Exception('Invalid period specified')
        # create the periodic task and the interval
        ptask_name = "%s_%s" % (task_name, datetime.now()) # create some name for the period task
        interval_schedules = IntervalSchedule.objects.filter(period=period, every=every)
        if interval_schedules: # just check if interval schedules exist like that already and reuse em
            interval_schedule = interval_schedules[0]
        else: # create a brand new interval schedule
            interval_schedule = IntervalSchedule()
            interval_schedule.every = every # should check to make sure this is a positive int
            interval_schedule.period = period 
            interval_schedule.save()
        ptask = PeriodicTask(name=ptask_name, task=task_name, interval=interval_schedule)
        if args:
            ptask.args = args
        if kwargs:
            ptask.kwargs = kwargs
        ptask.save()
        return TaskScheduler.objects.create(periodic_task=ptask)

    def stop(self):
        """pauses the task"""
        ptask = self.periodic_task
        ptask.enabled = False
        ptask.save()

    def start(self):
        """starts the task"""
        ptask = self.periodic_task
        ptask.enabled = True
        ptask.save()

    def terminate(self):
        self.stop()
        ptask = self.periodic_task
        self.delete()
        ptask.delete()	
