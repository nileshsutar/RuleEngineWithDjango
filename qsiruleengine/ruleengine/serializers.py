
from rest_framework import serializers

from models import Rule, FeatureURLs, FeatureFields, RuleScheduler



class FeatureFieldsSerializer(serializers.ModelSerializer):
	class Meta:
		model = FeatureFields
		fields = ('feature_url_field', 'field_index')
	

class FeatureURLsSerializer(serializers.ModelSerializer):
	featureurlfields = FeatureFieldsSerializer(many=True)
	class Meta:
		model = FeatureURLs
		fields = ('feature_url', 'featureurlfields')

	#def create(self, validated_data):
	#	import pdb;pdb.set_trace()
	#	featureurlfieldsdata = validated_data.pop("featureurlfields")
	#	feaurefieldsobj = FeatureFields.objects.create(**featureurlfieldsdata)

class RuleSchedulerSerializer(serializers.ModelSerializer):
	class Meta:
		model = RuleScheduler
		fields = ('schedulertime', 'schedulertype')


class RuleSerializer(serializers.ModelSerializer):

	featureurls = FeatureURLsSerializer(many=True, required=False)
	scheduler = RuleSchedulerSerializer()
	class Meta:
		model= Rule
		fields = ('id', 'rule_type', 'rule_name', 'area_url', 'featureurls', 'scheduler', 'createddate', 'emailid')

	def create(self, validated_data):
		#import pdb;pdb.set_trace()
		featureurlfieldsdata = validated_data.pop("featureurls")
		schedulerdata = validated_data.pop("scheduler")
		rulescheduler = RuleScheduler.objects.create(**schedulerdata)
		rule = Rule.objects.create(scheduler=rulescheduler, **validated_data)
		featureurlsobj = list()
		for featureurls in featureurlfieldsdata:
			url = featureurls.get("feature_url", None)
			furlobj = FeatureURLs.objects.create(feature_url=url)
			featurefields = featureurls.get("featureurlfields", list())
			
			for featurefield in featurefields:
				field = featurefield.get("feature_url_field", None)
				index = featurefield.get("field_index", None)
				featurefieldobj = FeatureFields.objects.create(feature_url_field=field, field_index=index)
				furlobj.featureurlfields.add(featurefieldobj)	
			rule.featureurls.add(furlobj)
		return rule		
