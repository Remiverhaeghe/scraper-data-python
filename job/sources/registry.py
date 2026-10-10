"""Liste des sources d'emploi disponibles"""

from job.sources.adzuna.source import SOURCE as ADZUNA
from job.sources.arbeitnow.source import SOURCE as ARBEITNOW
from job.sources.findwork.source import SOURCE as FINDWORK
from job.sources.france_travail.source import SOURCE as FRANCE_TRAVAIL
from job.sources.greenhouse.source import SOURCE as GREENHOUSE
from job.sources.hackernews.source import SOURCE as HACKERNEWS
from job.sources.himalayas.source import SOURCE as HIMALAYAS
from job.sources.jobicy.source import SOURCE as JOBICY
from job.sources.jooble.source import SOURCE as JOOBLE
from job.sources.remotive.source import SOURCE as REMOTIVE

# L'ordre détermine l'ordre de scraping et d'affichage.
SOURCES = {
    vSource.name: vSource
    for vSource in (
        FRANCE_TRAVAIL,
        ADZUNA,
        JOOBLE,
        JOBICY,
        HIMALAYAS,
        REMOTIVE,
        ARBEITNOW,
        FINDWORK,
        HACKERNEWS,
        GREENHOUSE,
    )
}
