from django.urls import re_path
from wiki.core.plugins import registry
from wiki.core.plugins.base import BasePlugin

from . import settings
from . import views


class InsertStep(BasePlugin):
    slug = settings.SLUG

    urlpatterns = {
        "article": [
            re_path(r"^$", views.WhatLeadsHere.as_view(), name="stepsbefore"),
            re_path(
                r"b(?P<location>[^+]+):(?P<leadin>.+)$",
                views.InsertBetween.as_view(),
                name="insertstep",
            ),
        ]
    }

    markdown_extensions = [
        "wiki.plugins.insertstep.mdx",
    ]


registry.register(InsertStep)
