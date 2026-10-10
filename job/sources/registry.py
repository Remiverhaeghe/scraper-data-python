"""Liste des sources d'emploi disponibles"""

from job.sources.adzuna.source import SOURCE as ADZUNA
from job.sources.france_travail.source import SOURCE as FRANCE_TRAVAIL
from job.sources.greenhouse.source import SOURCE as GREENHOUSE
from job.sources.lever.source import SOURCE as LEVER

# L'ordre détermine l'ordre de scraping et d'affichage.
SOURCES = {
    vSource.name: vSource for vSource in (FRANCE_TRAVAIL, ADZUNA, GREENHOUSE, LEVER)
}
