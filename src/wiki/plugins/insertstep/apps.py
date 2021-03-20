from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class InsertStepConfig(AppConfig):
    name = "wiki.plugins.insertstep"
    verbose_name = _("Insert Step")
    label = "wiki_insertstep"
