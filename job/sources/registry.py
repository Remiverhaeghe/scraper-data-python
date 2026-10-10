"""Liste des sources d'emploi disponibles"""

from job.sources.adzuna.source import SOURCE as ADZUNA
from job.sources.arbeitnow.source import SOURCE as ARBEITNOW
from job.sources.france_travail.source import SOURCE as FRANCE_TRAVAIL
from job.sources.greenhouse.source import SOURCE as GREENHOUSE
from job.sources.himalayas.source import SOURCE as HIMALAYAS
from job.sources.jobicy.source import SOURCE as JOBICY
from job.sources.lever.source import SOURCE as LEVER
from job.sources.remotive.source import SOURCE as REMOTIVE

# L'ordre détermine l'ordre de scraping et d'affichage.
SOURCES = {
    vSource.name: vSource
    for vSource in (
        FRANCE_TRAVAIL,
        ADZUNA,
        JOBICY,
        HIMALAYAS,
        REMOTIVE,
        ARBEITNOW,
        GREENHOUSE,
        LEVER,
    )
}
