"""qsiruleengine URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.conf.urls import url, include
from rest_framework import routers

from ruleengine import views


router = routers.DefaultRouter()
#router.register(r'rules', views.RuleViewSet)			
#router.register(r'rules', views.RuleList)			


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    #url(r'^', include(router.urls)),	
    url(r'^rules/$', views.RuleList.as_view()),
    url(r'^rules/(?P<pk>[0-9]+)/$', views.RuleDetail.as_view()),	
    url(r'^executerule/(?P<pk>[0-9]+)$', views.executerule),
    url(r'^getattrs(?P<featureurl>[a-zA-Z0-9_.-/:?=#]*)', views.getattributes, name='getattibutes'),
    url(r'^download/(?P<filename>[\w.]{0,256})$', views.filedownload)		
]
