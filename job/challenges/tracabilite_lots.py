"""Défi : remonter et descendre la généalogie des lots de fabrication"""

ID = "tracabilite-lots"
TITLE = "La traçabilité des lots"
SERIES = "Industrie"
LEVEL = "confirmé"

STATEMENTS = (
    """Une usine trace la composition de chaque lot. Les lots de matière première
commencent par M, les lots intermédiaires par L et les produits finis par P. Chaque
ligne de composition indique un lot puis ceux qui le composent, dans n'importe quel
ordre : `L0042 <- M0007 L0031` signifie que L0042 est fabriqué avec M0007 et L0031.

Les deux premières lignes signalent des incidents : `reclamation P…`, un produit fini
qui fait l'objet d'une réclamation client, et `alerte M…`, un lot de matière déclaré
contaminé.

**Combien de lots de matière première distincts entrent, directement ou non, dans le
produit faisant l'objet de la réclamation ?**""",
    """Le fournisseur confirme la contamination du lot de matière en alerte. Tous les
produits finis qui le contiennent, directement ou à travers des lots intermédiaires,
doivent être rappelés.

**Combien de produits finis faut-il rappeler ?**""",
)
EXAMPLE = """reclamation P1
alerte M2
L1 <- M1 M2
L2 <- M3 L1
P1 <- L2 M4
P2 <- L1
P3 <- M3"""
EXAMPLE_ANSWERS = ("4", "2")
HINTS = (
    "Un dictionnaire lot → composants permet de remonter ; il suffit de l'inverser "
    "pour descendre.",
    "Un même lot peut être atteint par plusieurs chemins : retenez les lots déjà "
    "visités.",
)
NOTE = """Les compositions forment un graphe orienté sans cycle. La réclamation se
traite en remontant le graphe depuis le produit (parcours en profondeur ou en largeur)
et en gardant les lots en M ; le rappel se traite en descendant le graphe inversé
depuis la matière et en gardant les lots en P. Sans ensemble des lots visités, un lot
partagé serait compté plusieurs fois et le parcours pourrait exploser sur un grand
graphe.

C'est exactement ce que fait un système de traçabilité en agroalimentaire ou en
pharmacie : remonter vers les fournisseurs à partir d'une plainte, descendre vers les
clients à partir d'une alerte."""


def generate(pRandom):
    """Retourne les incidents puis les compositions, mélangées, de quelques centaines de lots."""

    vMaterials = [f"M{vIndex:04d}" for vIndex in range(1, pRandom.randint(200, 300))]
    vIntermediates = []
    vLines = []

    for vIndex in range(1, pRandom.randint(120, 180)):
        vLot = f"L{vIndex:04d}"
        vParts = pRandom.sample(vMaterials, pRandom.randint(1, 3))

        if vIntermediates:
            vParts += pRandom.sample(
                vIntermediates, min(len(vIntermediates), pRandom.randint(0, 2))
            )

        vLines.append(f"{vLot} <- {' '.join(vParts)}")
        vIntermediates.append(vLot)

    vProducts = [f"P{vIndex:04d}" for vIndex in range(1, pRandom.randint(60, 90))]

    for vProduct in vProducts:
        vParts = pRandom.sample(vIntermediates, pRandom.randint(1, 3))
        vParts += pRandom.sample(vMaterials, pRandom.randint(0, 1))
        vLines.append(f"{vProduct} <- {' '.join(vParts)}")

    pRandom.shuffle(vLines)
    vUsers = build_users(vLines)
    # Une alerte sans produit touché donnerait une réponse nulle, trop facile.
    vAlerts = [
        vMaterial
        for vMaterial in vMaterials
        if sum(vLot.startswith("P") for vLot in explore(vUsers, vMaterial)) >= 2
    ]
    vIncidents = [
        f"reclamation {pRandom.choice(vProducts)}",
        f"alerte {pRandom.choice(vAlerts)}",
    ]

    rInput = "\n".join(vIncidents + vLines)

    return rInput


def build_users(pLines):
    """Retourne, pour chaque lot, ceux qui l'utilisent comme composant."""

    rUsers = {}

    for vLine in pLines:
        vLot, vComponents = vLine.split(" <- ")

        for vComponent in vComponents.split():
            rUsers.setdefault(vComponent, []).append(vLot)

    return rUsers


def explore(pGraph, pStart):
    """Retourne tous les lots atteints depuis pStart en suivant le graphe."""

    rSeen = set()
    vPending = [pStart]

    while vPending:
        for vNext in pGraph.get(vPending.pop(), ()):
            if vNext not in rSeen:
                rSeen.add(vNext)
                vPending.append(vNext)

    return rSeen


def solve(pInput):
    """Retourne les matières du produit en réclamation et les produits à rappeler."""

    vLines = pInput.strip().splitlines()
    vComplaint = vLines[0].split()[1]
    vAlert = vLines[1].split()[1]
    vParts = {
        vLot: vComponents.split()
        for vLot, vComponents in (vLine.split(" <- ") for vLine in vLines[2:])
    }
    vUsers = build_users(vLines[2:])

    vMaterials = {vLot for vLot in explore(vParts, vComplaint) if vLot.startswith("M")}
    vRecalled = {vLot for vLot in explore(vUsers, vAlert) if vLot.startswith("P")}

    rAnswers = (str(len(vMaterials)), str(len(vRecalled)))

    return rAnswers
