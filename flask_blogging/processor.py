import re
try:
    from builtins import object
except ImportError:
    pass
import markdown
from markdown.extensions.meta import MetaExtension
from flask import url_for
from flask_login import current_user
from slugify import slugify

class MathJaxPattern(markdown.inlinepatterns.InlineProcessor):
    """
    Matches unescaped `$` or `$$` and wraps the whole match in a <mathjax> tag.
    The pattern keeps the original delimiters so that downstream processors (e.g. KaTeX)
    see exactly what was typed by the author.

    Regex (read as:  negative , then $ or $$, then
    minimal content, then *the same delimiter again*):
        (?<!\\)(\$\$?)(.+?)\2
    """
    def __init__(self):
        # No need to pass a Markdown  it will be supplied when we register.
        super().__init__(r'(?<!\\)(\$\$?)(.+?)\2')

    def handleMatch(self, m, data):
        """Return the `<mathjax>` element and span of the original match."""
        node = etree.Element('mathjax')
        # Preserve the original delimiters (1) around the content (2)
        node.text = AtomicString(m.group(1) + m.group(2) + m.group(1))
        return node, m.start(0), m.end(0)

class MathJaxExtension(markdown.Extension):
    """Register the `MathJaxPattern` as an inline processor."""

    def extendMarkdown(self, md: markdown.Markdown):
        # Use a high numeric priority so this runs **before** the in escape
        # pattern (`escape`).  The exact value t  it just has to be
        # larger 200).  175 works for the default stack.
        md.inlinePatterns.register(MathJaxPattern(), 'mathjax', 175)


def makeExtension(**kwargs):
    """Compatibility hook used by `markdown.Extension`."""
    return MathJaxExtension(**kwargs)


class PostProcessor(object):

    _markdown_extensions = [MathJaxExtension(), MetaExtension()]

    @staticmethod
    def create_slug(title):
        return slugify(title)

    @staticmethod
    def extract_images(post):
        regex = re.compile(r'<\s*img [^>]*src="([^"]+)')
        return regex.findall(post["rendered_text"])

    @classmethod
    def construct_url(cls, post):
        url = url_for("blogging.page_by_id", post_id=post["post_id"],
                      slug=cls.create_slug(post["title"]))
        return url

    @classmethod
    def render_text(cls, post):
        md = markdown.Markdown(extensions=cls.all_extensions())
        post["rendered_text"] = md.convert(post["text"])
        post["meta"] = md.Meta

    @classmethod
    def is_author(cls, post, user):
        return user.get_id() == u''+str(post['user_id'])

    @classmethod
    def process(cls, post, render=True):
        """
        This method takes the post data and renders it
        :param post:
        :param render:
        :return:
        """
        post["slug"] = cls.create_slug(post["title"])
        post["editable"] = cls.is_author(post, current_user)
        post["url"] = cls.construct_url(post)
        post["priority"] = 0.8
        if render:
            cls.render_text(post)
            post["meta"]["images"] = cls.extract_images(post)

    @classmethod
    def all_extensions(cls):
        return cls._markdown_extensions

    @classmethod
    def set_custom_extensions(cls, extensions):
        if type(extensions) == list:
            cls._markdown_extensions.extend(extensions)
