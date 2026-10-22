"""Client HTTP du flux RSS We Work Remotely"""

from defusedxml import ElementTree

from utils.api_client import request_bytes

FEED_URL = "https://weworkremotely.com/remote-jobs.rss"


def get_items():
    """Retourne les éléments <item> du flux, une offre chacun."""

    # defusedxml : un flux distant ne peut pas exploiter les entités XML.
    vRoot = ElementTree.fromstring(request_bytes("GET", FEED_URL, pExpectedType="xml"))

    rItems = vRoot.findall("./channel/item")

    return rItems
