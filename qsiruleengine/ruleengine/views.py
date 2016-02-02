import os, sys, csv
import simplejson
from httplib2 import Http
from datetime import datetime

from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.views import APIView
from django.http import Http404, HttpResponse
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from celery.decorators import task


from ruleengine.serializers import RuleSerializer, FeatureURLsSerializer, RuleExecutionSummarySerializer
from ruleengine.models import Rule, RuleExecutionSummary, TaskScheduler

from tasks import executeruleAsync

# Create your views here.

http = Http()

class RuleViewSet(viewsets.ModelViewSet):
	queryset = Rule.objects.all()
	serializer_class = RuleSerializer

class RuleList(APIView):
	"""
	List all rules, or create a new rule
	"""
	def get(self, request, format=None):
		rules = Rule.objects.all()
		serializer = RuleSerializer(rules, many=True)
		return Response(serializer.data)

	def post(self, request, format=None):
		serializer = RuleSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RuleDetail(APIView):
	"""
	Get, Update or Delete a specific rule
	"""
	def get_object(self, pk):
		try:
			return Rule.objects.get(pk=pk)
		except Rule.DoesNotExist:
			raise Http404

	def get(self, request, pk, format=None):
		import pdb;pdb.set_trace()
		from celery import registry
		registry.tasks.register(executerule_async)
		rule = self.get_object(pk)
		serializer = RuleSerializer(rule)
		
		from djcelery.models import PeriodicTask, CrontabSchedule
		return Response(serializer.data)


@api_view(['GET'])
def executerule(request, pk):
	"""
	Execute a specific rule
	"""
	asyncresp = executeruleAsync.delay(pk)
	asyncresp.wait()
	if asyncresp.status == "SUCCESS" :
		status, data = asyncresp.result
		return Response(data, status)
	else:
		return Response({"Status of Task": asyncresp.status})


#@task(name="executeruletask")
def executerule_async(pk):
	rulestatus = "InProgress"
	success = False
	try:
		rule = Rule.objects.get(pk=pk)
	except Rule.DoesNotExist:
		return 404, {"message": "Rule with id '%s' not found" % pk}
		#return Response({"message": "Rule with id '%s' not found" % pk}, status=404)

	areaurl = rule.area_url
	polygonurl = os.path.join(areaurl, settings.AREAURLQUERY)
	polygonurl = polygonurl.strip()
	status, resp = http.request(polygonurl, 'GET', headers = settings.HEADERS)
	try:
		response = simplejson.loads(resp)
		rings = response.get("features")[0].get("geometry").get("rings")
	except Exception as error:
		rulestatus = "Failed"
		message = 'Invalid JSON for area url- {0}'.format(error.message)
		summary = RuleExecutionSummary(rule_name=rule.rule_name, rule_id=rule.pk, execution_status=rulestatus, \
					error_message=message)
		if summary:
			#serializer.save()
			return Response({"message" : message}, status=400)
		else:
			return Response({"message" : message}, status=400)
	
	featureurlsobj = rule.featureurls.all()
	featureurlobj = featureurlsobj[0]#[featureurlobj.get('feature_url') for featureurlobj in rule.featureurls.values()]
	feature_url = featureurlobj.feature_url
	feature_url = "%s%s" % (feature_url, settings.FEATUREURIQUERY)
	feature_url = "%s%s" % (feature_url, simplejson.dumps(rings))
	feature_url = "%s%s" % (feature_url, settings.SPACIALREFURI)
	newFeatureURL = feature_url.replace(" ", "")
	newFeatureURL = newFeatureURL.strip()
	starttime = datetime.now()
	try:
		status, resp = http.request(newFeatureURL, 'GET', headers = settings.HEADERS)
		resp = simplejson.loads(resp)
		rulestatus = "Completed"
		success=True
	except Exception as error:
		rulestatus = "Failed"
		message = 'Invalid JSON for feature url- {0}'.format(error.message)
		status=status.HTTP_400_BAD_REQUEST

	stoptime = datetime.now()	
	features = resp.get("features", list())
	feature_attrs = list()
	featurefields = featureurlobj.featureurlfields.order_by('field_index').values('feature_url_field')
	fields = []
	for feature in features:
		attributes = feature.get("attributes", dict())
		feature_fields_tmp = dict()
		for fielddict in featurefields:
			field = fielddict.get("feature_url_field")
			fields.append(field)
			value = attributes.get(field, None)
			value = unicode(value).encode("utf8")
			feature_fields_tmp[field] = value
		feature_attrs.append(feature_fields_tmp)

	if not os.path.exists(settings.DOWNLOADLOC):
		os.makedirs(settings.DOWNLOADLOC)

	#import pdb;pdb.set_trace()
	tmprulename = rule.rule_name.replace(" ", "_")
	filename = "%s.csv" % tmprulename	
	fileloc = "%s%s" % (settings.DOWNLOADLOC, filename)
	
	with open(fileloc, "w") as csvfile:
		writer = csv.DictWriter(csvfile, fieldnames=fields)
		writer.writeheader()
		for feature_attr in feature_attrs:
			writer.writerow(feature_attr)

	#import pdb;pdb.set_trace()
	TaskScheduler.schedule_every(executerule, "minutes", 5, 2)	

	try:
		if success:
			summary = RuleExecutionSummary(rule_name=rule.rule_name, rule_id=rule.pk, starttime=starttime, \
								stoptime=stoptime, execution_status=rulestatus, filelocation=fileloc)
			summary.save()
			res_dict = {"status": "success", "rulename": rule.rule_name, "ruleid": rule.pk}
			return 201, res_dict
			#return Response({"status": "success", "rulename": rule.rule_name, "ruleid": rule.pk}, status=201)
		else:
			summary = RuleExecutionSummary(rule_name=rule.rule_name, rule_id=rule.pk, starttime=starttime, \
								stoptime=stoptime, execution_status=rulestatus, error_message=message)
			summary.save()
			return 400, {"message" : message}
			#return  Response({"message" : message}, status=400)
	except Exception as error:
		 return Response({"message" : error}, status=400)

@api_view(['GET'])
def getattributes(request, featureurl):
	"""
	Get attributes of a specific feature url.
	"""
	featureurl = request.GET.get('featureurl', None)
	if not featureurl:
		return Response(status=status.HTTP_404_NOT_FOUND)
	feature_url = "%s%s" %(featureurl, "/f=json?f=pjson")
	status, resp = http.request(feature_url, 'GET', headers = settings.HEADERS)
	try:
		response = simplejson.loads(resp)
	except Exception as error:
		return Response('Invalid JSON - {0}'.format(error.message), status=status.HTTP_400_BAD_REQUEST)
		 
	fields = response.get("fields", None)
	attrs = list()
	for eachfield in fields:
		fieldname = eachfield.get("name")
		attrs.append(fieldname)
	return Response(attrs)


def filedownload(request, filename):
	"""
	Download a specific csv file
	"""
	filepath = settings.DOWNLOADLOC+filename
	try:
		f= open(filepath)
		data = f.read()
		f.close()
		response = HttpResponse(data, content_type='text/csv')
		contentvalue = "attachment; filename=%s" % (filename) 
		response["Content-Disposition"] = contentvalue
		return response
	except :
		return Response('Filepath not exist', status=status.HTTP_404_NOT_FOUND)


class RuleExecutionSummaryList(APIView):
	"""
	"""
	def get(self, request, format=None):
		summary = RuleExecutionSummary.objects.all()
		serializer = RuleExecutionSummarySerializer(summary, many=True)
		return Response(serializer.data)

