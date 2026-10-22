"""Déclaration de la source Working Nomads"""

from job.sources.boards import define_feed_source
from job.sources.workingnomads.client import get_jobs
from job.sources.workingnomads.parser import parse_jobs

SOURCE = define_feed_source(
    "workingnomads", "Working Nomads", lambda: parse_jobs(get_jobs())
)
