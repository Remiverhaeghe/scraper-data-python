"""Déclaration de la source Remote OK"""

from job.sources.boards import define_feed_source
from job.sources.remoteok.client import get_jobs
from job.sources.remoteok.parser import parse_jobs

SOURCE = define_feed_source("remoteok", "Remote OK", lambda: parse_jobs(get_jobs()))
