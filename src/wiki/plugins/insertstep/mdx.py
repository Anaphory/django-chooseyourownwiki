from urllib.parse import quote
from urllib.parse import urljoin
from urllib.parse import urlparse
from xml.etree.ElementTree import dump
from xml.etree.ElementTree import Element

import wiki.models as wiki_models
from django.urls import resolve
from django.urls.exceptions import Resolver404
from django.utils.translation import gettext as _
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from wiki.core.exceptions import NoRootURL
from wiki.decorators import which_article


class LinkTreeprocessor(Treeprocessor):
    def __init__(self, md, config):
        super().__init__(md)
        self.md = md
        self.choice_class = config.get("choice", "choice")
        self.new_class = config.get("new", "new")

    @property
    def my_article(self):
        try:
            return self._my_article
        except AttributeError:
            self._my_article = self.md.article
            return self._my_article

    def is_wiki_link(self, el):
        href = el.get("href")
        try:
            assert href
            url = urlparse(href)
            # Ensure that path ends with a slash
            assert not url.scheme
            assert not url.netloc
            target = urljoin(
                self.my_article.get_absolute_url(), url.path.rstrip("/") + "/"
            )
            resolution = resolve(target)
            assert resolution.app_names == ["wiki"]
            article, destination = which_article(**resolution.kwargs)
            # All other cases have raised exceptions: We have an internal link,
            # which should be reflected in the database.
        except (
            AssertionError,
            TypeError,
            ValueError,
            Resolver404,
            NoRootURL,
            wiki_models.URLPath.DoesNotExist,
            wiki_models.Article.DoesNotExist,
        ):
            # No wiki-internal link
            return None
        return article

    def run(self, doc):
        for ul in doc.iter():
            if ul.tag != "ul":
                continue
            parents = {}
            for lc in ul.iter():
                for child in lc:
                    parents[child] = lc
                if lc.tag != "a":
                    continue
                if lc.get("class") == self.new_class:
                    continue
                if not lc.get("href").startswith("../"):
                    continue
                if self.is_wiki_link(lc):
                    print(parents, lc)
                    index = min(i for i, c in enumerate(parents[lc]) if c == lc)
                    lc.set("class", self.choice_class)
                    lc.tail = " "
                    # find the parent again
                    step = Element(
                        "a",
                        href="_plugin/insertstep/b{:}:{:}".format(
                            lc.get("href"), quote(lc.text)
                        ),
                    )
                    step.set("class", self.new_class)
                    step.text = _("[Insert a step in between]")
                    parents[lc].insert(index + 1, step)
                    dump(parents[lc])


class LinkExtension(Extension):

    TreeProcessorClass = LinkTreeprocessor

    def extendMarkdown(self, md):
        md.registerExtension(self)
        self.md = md
        ext = self.TreeProcessorClass(md, self.getConfigs())
        md.treeprocessors.add("insertstep", ext, ">inline")


def makeExtension(*args, **kwargs):
    """Return an instance of the extension."""
    return LinkExtension(*args, **kwargs)
