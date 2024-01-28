#!/usr/bin/env python
from staticjinja import Site


if __name__ == "__main__":
    site = Site.make_site(
        extensions=['jinja_markdown.MarkdownExtension'],
        outpath="dist")

    # enable automatic reloading
    site.render(use_reloader=True)