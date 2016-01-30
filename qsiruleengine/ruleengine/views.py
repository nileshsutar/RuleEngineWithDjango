import os, sys, csv
import simplejson
from httplib2 import Http
from datetime import datetime

from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.views import APIView
from django.http import Http404
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view

from ruleengine.models import Rule
from ruleengine.serializers import RuleSerializer, FeatureURLsSerializer

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
		rule = self.get_object(pk)
		serializer = RuleSerializer(rule)
		return Response(serializer.data)


@api_view(['GET'])
def executerule(request, pk):
	"""
	Execute a specific rule
	"""
	try:
		rule = Rule.objects.get(pk=pk)
	except Rule.DoesNotExist:
		return Response(status=status.HTTP_404_NOT_FOUND)

	areaurl = rule.area_url
	polygonurl = os.path.join(areaurl, settings.AREAURLQUERY)
	polygonurl = polygonurl.strip()
	status, resp = http.request(polygonurl, 'GET', headers = settings.HEADERS)
	try:
		response = simplejson.loads(resp)
		rings = response.get("features")[0].get("geometry").get("rings")
	except Exception as error:
		return Response('Invalid JSON for area url- {0}'.format(error.message), status=status.HTTP_400_BAD_REQUEST) 
	
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
		rulestatus = "InProgress"
		success=True
	except Exception as error:
		Response('Invalid JSON for feature url- {0}'.format(error.message), status=status.HTTP_400_BAD_REQUEST)
	
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

	return Response({"status": "success", "rulename": rule.rule_name, "ruleid": rule.pk})
	
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
