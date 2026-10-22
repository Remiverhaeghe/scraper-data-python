"""Déclaration de la source We Work Remotely"""

from job.sources.boards import define_feed_source
from job.sources.weworkremotely.client import get_items
from job.sources.weworkremotely.parser import parse_items

SOURCE = define_feed_source(
    "weworkremotely", "We Work Remotely", lambda: parse_items(get_items())
)
