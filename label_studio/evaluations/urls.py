"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
from django.urls import path, include
from rest_framework import routers
from evaluations.views import EvaluationViewSet

router = routers.DefaultRouter()
router.register(r'evaluations', EvaluationViewSet, basename='evaluation')

urlpatterns = [
    path('api/', include(router.urls)),
]
