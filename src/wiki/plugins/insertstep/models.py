"""Define a model for storing which article links to which other article

Also define the function that stores links in that model, and connect it to the
ArticleRevision.post_save signal, so that links are always as up-to-date as
article revisions.

"""
from xml.etree import ElementTree as ET

import wiki.plugins.whatlinkswhere.models
from django.db import models
from django.utils.translation import gettext_lazy as _
from wiki import models as wiki_models
from wiki.core.markdown import article_markdown


__all__ = ["InternalStoryLink", "store_links"]


class InternalStoryLink(wiki.plugins.whatlinkswhere.models.InternalLink):
    """This model describes links between articles."""

    is_adventure_choice = models.BooleanField(
        default=False,
        verbose_name=_("is_adventure_choice"),
        help_text=_("The link is a choice in a choose-your-own-adventure page"),
    )

    def __str__(self):
        if not self.is_adventure_choice:
            return super().__str__(self)
        return _("Story page {:s} can lead to {:s}").format(
            self.from_article.current_revision.title,
            self.to_article.current_revision.title
            if self.to_article
            else self.to_nonexistant_url,
        )


def store_links(instance, *args, **kwargs):
    try:
        html = ET.fromstring(
            "<body>{:s}</body>".format(
                article_markdown(instance.content, instance.article, False)
            )
        )
    except ET.ParseError:
        # There are some cases where markdown doesn't evaluate to clean html.
        # It would probably be worth checking *how* they fail, but for now we
        # should at least not DIE due to them.
        return

    url = instance.article.get_absolute_url()
    article = instance.article

    for link in InternalStoryLink.objects.filter(to_nonexistant_url=url).all():
        link.to_nonexistant_url = None
        link.to_article = article
        link.save()

    InternalStoryLink.objects.filter(from_article=article).delete()

    for ul in html.iter():
        if ul.tag != "ul":
            continue
        for lc in ul.iter():
            if lc.tag != "a":
                continue
            store = InternalStoryLink.store_link(url, article, lc)
            if store:
                store.is_adventure_choice = True


# Whenever a new revision is created, update all links in there
models.signals.post_save.connect(
    store_links,
    sender=wiki_models.ArticleRevision,
)
