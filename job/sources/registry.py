"""Liste des sources d'emploi disponibles"""

from job.sources.adzuna.source import SOURCE as ADZUNA
from job.sources.arbeitnow.source import SOURCE as ARBEITNOW
from job.sources.ashby.source import SOURCE as ASHBY
from job.sources.careerjet.source import SOURCE as CAREERJET
from job.sources.findwork.source import SOURCE as FINDWORK
from job.sources.france_travail.source import SOURCE as FRANCE_TRAVAIL
from job.sources.greenhouse.source import SOURCE as GREENHOUSE
from job.sources.hackernews.source import SOURCE as HACKERNEWS
from job.sources.himalayas.source import SOURCE as HIMALAYAS
from job.sources.jobicy.source import SOURCE as JOBICY
from job.sources.jooble.source import SOURCE as JOOBLE
from job.sources.labonnealternance.source import SOURCE as LABONNEALTERNANCE
from job.sources.lever.source import SOURCE as LEVER
from job.sources.recruitee.source import SOURCE as RECRUITEE
from job.sources.remoteok.source import SOURCE as REMOTEOK
from job.sources.remotive.source import SOURCE as REMOTIVE
from job.sources.smartrecruiters.source import SOURCE as SMARTRECRUITERS
from job.sources.weworkremotely.source import SOURCE as WEWORKREMOTELY
from job.sources.workable.source import SOURCE as WORKABLE
from job.sources.workday.source import SOURCE as WORKDAY
from job.sources.workingnomads.source import SOURCE as WORKINGNOMADS

# L'ordre détermine l'ordre de scraping et d'affichage.
SOURCES = {
    vSource.name: vSource
    for vSource in (
        FRANCE_TRAVAIL,
        ADZUNA,
        JOOBLE,
        CAREERJET,
        LABONNEALTERNANCE,
        SMARTRECRUITERS,
        LEVER,
        ASHBY,
        GREENHOUSE,
        RECRUITEE,
        WORKABLE,
        WORKDAY,
        JOBICY,
        HIMALAYAS,
        REMOTIVE,
        REMOTEOK,
        WORKINGNOMADS,
        WEWORKREMOTELY,
        ARBEITNOW,
        FINDWORK,
        HACKERNEWS,
    )
}
