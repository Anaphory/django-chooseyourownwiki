from urllib.parse import urljoin

from django import forms
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from wiki import forms as wiki_forms
from wiki import models as wiki_models
from wiki.conf import settings
from wiki.forms import CreateForm
from wiki.plugins.linknetwork.views import LinkNetwork
from wiki.plugins.linknetwork.views import WhatLinksHere
from wiki.views.article import Create as CreateView

from . import models


class WhatLeadsHere(WhatLinksHere):
    template_name = "wiki/plugins/insertstep/whatleadshere.html"
    model = models.InternalStoryLink


class StoryNetwork(LinkNetwork):
    template_name = "wiki/plugins/insertstep/storynetwork.html"
    paginator_class = None
    paginate_by = 1000000000000
    model = models.InternalStoryLink


class CreateBetweenForm(CreateForm):
    leadinghere = forms.CharField(
        label=pgettext_lazy("Lead-In", "Lead-In"),
        help_text=_("The text in the previous step, leading to here"),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class InsertBetween(CreateView):
    form_class = CreateBetweenForm

    def get_form(self, form_class=None):
        """
        Returns an instance of the form to be used in this view.
        """
        print("GET_FORM")
        if form_class is None:
            form_class = self.get_form_class()
        kwargs = self.get_form_kwargs()
        print(kwargs)
        initial = kwargs.get("initial", {})
        initial["slug"] = self.request.GET.get("slug", None)

        try:
            initial["content"] = _("Would you like to…") + "\n\n - [{:}]({:})".format(
                self.leadin, self.path
            )
            initial["leadinghere"] = self.leadin
        except AttributeError:
            pass

        kwargs["initial"] = initial
        form = form_class(self.request, self.urlpath, **kwargs)
        form.fields["slug"].widget = wiki_forms.TextInputPrepend(
            prepend="/" + self.urlpath.path,
            attrs={
                # Make patterns force lowercase if we are case insensitive to bless the user with a
                # bit of strictness, anyways
                "pattern": "[a-z0-9_-]+"
                if not settings.URL_CASE_SENSITIVE
                else "[a-zA-Z0-9_-]+",
                "title": "Lowercase letters, numbers, hyphens and underscores"
                if not settings.URL_CASE_SENSITIVE
                else "Letters, numbers, hyphens and underscores",
            },
        )
        return form

    def dispatch(self, request, *args, **kwargs):
        if request.method == "GET":
            print("GET")
            self.path = kwargs["location"]
            self.leadin = kwargs["leadin"].replace("+", " ")
            kwargs["path"] = urljoin(kwargs["path"], "../")
            print(kwargs)
            return super().dispatch(request, *args, **kwargs)
        else:
            print("POST")
            kwargs["frompath"] = kwargs["path"]
            kwargs["path"] = urljoin(kwargs["path"], "../")
            try:
                old_leadin = kwargs["leadin"]
                old_location = kwargs["location"]
                old_link = "[{:}]({:})".format(old_leadin, old_location)

                data = self.get_form_kwargs()["data"]
                new_leadin = data["leadinghere"]
                new_location = data["slug"]
                new_link = "[{:}](../{:}/)".format(new_leadin, new_location)

                article = wiki_models.URLPath.get_by_path(kwargs["frompath"]).article
                old_text = article.current_revision.content
                index = old_text.index(old_link)

                new_text = (
                    old_text[:index] + new_link + old_text[index + len(old_link) :]
                )
                article.current_revision.content = new_text
                article.current_revision.save()
                print(article)
                print(article.current_revision.content)
            except KeyError:
                messages.error(
                    request, _("Unable to insert lead-in back in ") + str(article)
                )
            return super().dispatch(request, *args, **kwargs)
