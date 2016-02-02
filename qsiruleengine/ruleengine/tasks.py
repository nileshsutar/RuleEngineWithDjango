
import os, sys, csv
import simplejson
from httplib2 import Http
from datetime import datetime

from django.conf import settings
from rest_framework.response import Response
from celery.decorators import task

from ruleengine.models import Rule, RuleExecutionSummary, TaskScheduler

http = Http()

@task(name="executerule")
def executeruleAsync(pk):
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


