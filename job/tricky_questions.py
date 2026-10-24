"""Questions pièges selon le type d'employeur, avec la manière d'y répondre

Une ESN, une agence d'intérim et un client final ne posent pas les mêmes
questions délicates : mobilité et intercontrat pour l'une, disponibilité et
taux horaire pour l'autre, motivation à long terme pour le dernier.
"""

from job.agencies import is_agency_offer, is_consulting_offer

EMPLOYER_LABELS = {
    "consulting": "Société de conseil (ESN)",
    "agency": "Agence d'intérim",
    "final": "Client final",
}

TRICKY_QUESTIONS = {
    "consulting": (
        (
            "Êtes-vous mobile géographiquement ?",
            "Un « oui » sans limite engage à des missions lointaines : donnez votre "
            "périmètre réel (par exemple la métropole et une heure de trajet) et ce "
            "qui reste négociable.",
        ),
        (
            "Que feriez-vous en intercontrat ?",
            "Montrez votre autonomie : formation, certification, projets internes, "
            "aide à l'avant-vente. Demandez comment l'ESN gère cette période.",
        ),
        (
            "Accepteriez-vous une mission éloignée de votre projet ?",
            "Ouvert à court terme, avec une limite claire (technologie, durée), "
            "puis demandez comment l'ESN suit l'évolution de ses consultants.",
        ),
        (
            "Quel salaire visez-vous ?",
            "Raisonnez en brut annuel, jamais à partir du tarif facturé au client ; "
            "appuyez-vous sur le salaire du marché affiché sur l'offre.",
        ),
        (
            "Êtes-vous en discussion avec d'autres entreprises ?",
            "Restez honnête sans citer de noms : d'autres échanges sont en cours, "
            "ce qui montre que votre profil intéresse.",
        ),
    ),
    "agency": (
        (
            "Êtes-vous disponible immédiatement ?",
            "Donnez une date précise, préavis compris : l'agence place d'abord les "
            "candidats disponibles.",
        ),
        (
            "Accepteriez-vous des horaires décalés ou des missions courtes ?",
            "Dites ce que vous acceptez vraiment (2x8, nuit, week-end) : un « oui » "
            "contraint finit souvent en mission écourtée.",
        ),
        (
            "Vos habilitations et certificats sont-ils à jour ?",
            "Ayez sous la main leurs dates de validité ; à défaut, dites quand ils "
            "seront renouvelés.",
        ),
        (
            "Quel taux horaire demandez-vous ?",
            "Annoncez un taux brut ; les indemnités de fin de mission et de congés "
            "payés (10 % chacune) s'y ajoutent.",
        ),
        (
            "Un CDI intérimaire vous intéresserait-il ?",
            "Demandez ce qu'il implique : périmètre des missions, rémunération "
            "entre deux missions, distance maximale imposée.",
        ),
    ),
    "final": (
        (
            "Pourquoi souhaitez-vous quitter votre poste ?",
            "Parlez de ce que vous cherchez, jamais d'une critique de votre "
            "employeur actuel.",
        ),
        (
            "Où vous voyez-vous dans cinq ans ?",
            "Une évolution cohérente avec ce poste et possible dans cette "
            "entreprise : montrez que vous comptez rester.",
        ),
        (
            "Pourquoi vous plutôt qu'un autre candidat ?",
            "Trois atouts reliés chacun à une exigence de l'offre, avec un exemple "
            "concret pour au moins l'un d'eux.",
        ),
        (
            "Quel est votre principal défaut ?",
            "Un vrai point de progrès, suivi de ce que vous faites déjà pour "
            "l'améliorer.",
        ),
        (
            "Avez-vous des questions ?",
            "Répondre non passe pour du désintérêt : préparez-en deux sur l'équipe "
            "et les premiers mois dans le poste.",
        ),
    ),
}


def get_employer_kind(pOffer, pAgencies=()):
    """Retourne le type d'employeur de l'offre : agency, consulting ou final."""

    if is_agency_offer(pOffer, pAgencies):
        rKind = "agency"
    elif is_consulting_offer(pOffer):
        rKind = "consulting"
    else:
        rKind = "final"

    return rKind


def build_tricky_questions(pOffer, pAgencies=()):
    """Retourne le type d'employeur et ses questions pièges : question, conseil."""

    vKind = get_employer_kind(pOffer, pAgencies)

    rTricky = {
        "employer": EMPLOYER_LABELS[vKind],
        "questions": [
            {"question": vQuestion, "hint": vHint}
            for vQuestion, vHint in TRICKY_QUESTIONS[vKind]
        ],
    }

    return rTricky
