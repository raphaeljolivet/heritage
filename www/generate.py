#!/usr/bin/env python
from staticjinja import Site
import yaml
from urllib.parse import urlparse

LINKS_PATH = "data/links.yaml"

TITLE = "Héritage Pour Tous et Toutes"
DESCRIPTION = "Réformer l'héritage au bénéfice de la majorité des citoyen·nes"

def domain(url) :
    return urlparse(url).netloc

if __name__ == "__main__":

    with open(LINKS_PATH, "r") as f:
        links = yaml.safe_load(f)

    site = Site.make_site(
        extensions=['jinja_markdown.MarkdownExtension'],
        outpath="dist",
        filters=dict(domain=domain),
        env_globals=dict(
            links=links,
            title=TITLE,
            description=DESCRIPTION))

    # enable automatic reloading
    site.render(use_reloader=True)