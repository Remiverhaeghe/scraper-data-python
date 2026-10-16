"""Bibliothèque des composants des schémas à construire : symbole, bornes, symétrie

Chaque composant se dessine dans un cadre de WIDTH × HEIGHT. Ses bornes sont
nommées et placées sur ce cadre ; c'est entre elles que l'on tire les fils. Un
composant symétrique, comme un fusible, se branche indifféremment dans un sens
ou dans l'autre : ses deux bornes sont interchangeables à la correction.
"""

from dataclasses import dataclass

WIDTH = 80
HEIGHT = 100

STROKE = 'stroke="#0f172a" stroke-width="2.5" fill="none" stroke-linejoin="round"'


@dataclass(frozen=True)
class ComponentType:
    """Type de composant : libellé, domaine, bornes {nom : (x, y)} et dessin."""

    key: str
    label: str
    domain: str
    ports: tuple
    drawing: str
    symmetric: bool = False
    # Toutes les bornes forment un seul point de raccordement (équipement réseau)
    node: bool = False


TOP = (40, 0)
BOTTOM = (40, 100)


def two_terminals(pKey, pLabel, pDomain, pDrawing, pSymmetric=True):
    """Crée un composant à deux bornes, en haut et en bas du cadre."""

    rType = ComponentType(
        pKey,
        pLabel,
        pDomain,
        (("1", TOP), ("2", BOTTOM)),
        pDrawing,
        pSymmetric,
    )

    return rType


def one_terminal(pKey, pLabel, pDomain, pDrawing, pPort, pPosition=TOP):
    """Crée un composant à une seule borne : source, récepteur ou équipement."""

    rType = ComponentType(pKey, pLabel, pDomain, ((pPort, pPosition),), pDrawing)

    return rType


CONTACT = (
    f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="32"/>'
    '<line x1="40" y1="70" x2="40" y2="100"/>'
    '<line x1="40" y1="70" x2="24" y2="36"/></g>'
)

ELECTRICAL = "Électricité"
PNEUMATIC = "Pneumatique"
HYDRAULIC = "Hydraulique"
ELECTRONIC = "Électronique"
NETWORK = "Réseau"


def network_device(pKey, pLabel, pText):
    """Crée un équipement réseau : un cadre légendé, raccordable en haut ou en bas.

    Les deux bornes forment un même point : peu importe celle que l'on câble.
    """

    rType = ComponentType(
        pKey,
        pLabel,
        NETWORK,
        (("haut", (40, 26)), ("bas", (40, 74))),
        f'<rect x="8" y="26" width="64" height="48" rx="8" {STROKE}/>'
        f'<text x="40" y="56" text-anchor="middle" font-size="13" '
        f'font-weight="bold" fill="#0f172a">{pText}</text>',
        node=True,
    )

    return rType


COMPONENT_TYPES = (
    one_terminal(
        "reseau",
        "Réseau d'alimentation",
        ELECTRICAL,
        f'<circle cx="40" cy="44" r="24" {STROKE}/>'
        '<path d="M28,44 q6,-10 12,0 t12,0" stroke="#0f172a" stroke-width="2.5" '
        'fill="none"/><line x1="40" y1="68" x2="40" y2="100" stroke="#0f172a" '
        'stroke-width="2.5"/>',
        "sortie",
        BOTTOM,
    ),
    two_terminals(
        "sectionneur",
        "Sectionneur",
        ELECTRICAL,
        CONTACT + '<line x1="32" y1="32" x2="48" y2="32" stroke="#0f172a" '
        'stroke-width="2.5"/>',
    ),
    two_terminals(
        "fusible",
        "Fusible",
        ELECTRICAL,
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="100"/>'
        '<rect x="30" y="26" width="20" height="48"/></g>',
    ),
    two_terminals(
        "disjoncteur",
        "Disjoncteur",
        ELECTRICAL,
        CONTACT
        + '<g stroke="#0f172a" stroke-width="2.5"><line x1="34" y1="26" x2="46" '
        'y2="38"/><line x1="46" y1="26" x2="34" y2="38"/></g>',
    ),
    two_terminals(
        "differentiel",
        "Interrupteur différentiel",
        ELECTRICAL,
        CONTACT + f'<ellipse cx="40" cy="86" rx="16" ry="6" {STROKE}/>',
    ),
    two_terminals(
        "contacteur",
        "Contact de puissance du contacteur",
        ELECTRICAL,
        CONTACT
        + '<path d="M40,32 a7,7 0 0,1 0,-12" stroke="#0f172a" stroke-width="2.5" '
        'fill="none"/>',
    ),
    two_terminals(
        "relais_thermique",
        "Relais thermique",
        ELECTRICAL,
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="30"/>'
        '<rect x="14" y="30" width="52" height="40"/>'
        '<polyline points="22,60 32,60 32,42 48,42 48,60 58,60"/>'
        '<line x1="40" y1="70" x2="40" y2="100"/></g>',
    ),
    one_terminal(
        "moteur",
        "Moteur asynchrone triphasé",
        ELECTRICAL,
        f'<line x1="40" y1="0" x2="40" y2="26" {STROKE}/>'
        f'<circle cx="40" cy="56" r="28" {STROKE}/>'
        '<text x="40" y="56" text-anchor="middle" font-size="17" '
        'font-weight="bold" fill="#0f172a">M</text>'
        '<text x="40" y="74" text-anchor="middle" font-size="12" '
        'font-weight="bold" fill="#0f172a">3~</text>',
        "entrée",
    ),
    one_terminal(
        "prise",
        "Prise de courant",
        ELECTRICAL,
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="44"/>'
        '<path d="M16,70 a24,24 0 0,1 48,0"/><line x1="40" y1="44" x2="40" '
        'y2="70"/></g>',
        "entrée",
    ),
    one_terminal(
        "lampe",
        "Point lumineux",
        ELECTRICAL,
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="34"/>'
        '<circle cx="40" cy="56" r="22"/><line x1="25" y1="41" x2="55" y2="71"/>'
        '<line x1="55" y1="41" x2="25" y2="71"/></g>',
        "entrée",
    ),
    two_terminals(
        "transformateur",
        "Transformateur",
        ELECTRICAL,
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="20"/>'
        '<circle cx="40" cy="40" r="20"/><circle cx="40" cy="62" r="20"/>'
        '<line x1="40" y1="82" x2="40" y2="100"/></g>',
        pSymmetric=False,
    ),
    ComponentType(
        "moteur_six_bornes",
        "Moteur asynchrone à six bornes",
        ELECTRICAL,
        (("débuts", TOP), ("fins", BOTTOM)),
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="22"/>'
        '<circle cx="40" cy="50" r="28"/><line x1="40" y1="78" x2="40" '
        'y2="100"/></g>'
        '<text x="40" y="50" text-anchor="middle" font-size="16" '
        'font-weight="bold" fill="#0f172a">M</text>'
        '<text x="40" y="66" text-anchor="middle" font-size="11" '
        'font-weight="bold" fill="#0f172a">3~</text>'
        '<text x="46" y="12" font-size="9" fill="#475569">U1 V1 W1</text>'
        '<text x="46" y="96" font-size="9" fill="#475569">U2 V2 W2</text>',
    ),
    one_terminal(
        "point_etoile",
        "Point étoile",
        ELECTRICAL,
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="50"/>'
        '<line x1="40" y1="50" x2="20" y2="74"/><line x1="40" y1="50" x2="60" '
        'y2="74"/><line x1="40" y1="50" x2="40" y2="80"/></g>',
        "liaison",
    ),
    one_terminal(
        "source_air",
        "Source d'air comprimé",
        PNEUMATIC,
        f'<g {STROKE}><circle cx="40" cy="44" r="24"/>'
        '<polygon points="40,22 31,38 49,38"/>'
        '<line x1="40" y1="68" x2="40" y2="100"/></g>',
        "sortie",
        BOTTOM,
    ),
    two_terminals(
        "frl",
        "Unité FRL",
        PNEUMATIC,
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="24"/>'
        '<rect x="10" y="24" width="60" height="52" rx="6"/>'
        '<line x1="40" y1="76" x2="40" y2="100"/></g>'
        '<text x="40" y="56" text-anchor="middle" font-size="14" '
        'font-weight="bold" fill="#0f172a">FRL</text>',
        pSymmetric=False,
    ),
    ComponentType(
        "distributeur_32",
        "Distributeur 3/2",
        PNEUMATIC,
        (("2", (50, 0)), ("1", (44, 100)), ("3", (60, 100))),
        f'<g {STROKE}><rect x="12" y="34" width="28" height="32"/>'
        '<rect x="40" y="34" width="28" height="32"/>'
        '<line x1="50" y1="0" x2="50" y2="34"/><line x1="44" y1="66" x2="44" '
        'y2="100"/><line x1="60" y1="66" x2="60" y2="100"/>'
        '<line x1="50" y1="38" x2="58" y2="62"/><line x1="18" y1="62" x2="24" '
        'y2="38"/></g>',
    ),
    ComponentType(
        "distributeur_52",
        "Distributeur 5/2",
        PNEUMATIC,
        (
            ("4", (46, 0)),
            ("2", (62, 0)),
            ("5", (42, 100)),
            ("1", (54, 100)),
            ("3", (66, 100)),
        ),
        f'<g {STROKE}><rect x="4" y="34" width="36" height="32"/>'
        '<rect x="40" y="34" width="36" height="32"/>'
        '<line x1="46" y1="0" x2="46" y2="34"/><line x1="62" y1="0" x2="62" '
        'y2="34"/><line x1="42" y1="66" x2="42" y2="100"/><line x1="54" y1="66" '
        'x2="54" y2="100"/><line x1="66" y1="66" x2="66" y2="100"/>'
        '<line x1="54" y1="62" x2="62" y2="38"/><line x1="46" y1="38" x2="42" '
        'y2="62"/><line x1="18" y1="62" x2="10" y2="38"/><line x1="26" y1="38" '
        'x2="30" y2="62"/></g>',
    ),
    two_terminals(
        "reducteur",
        "Réducteur de débit unidirectionnel",
        PNEUMATIC,
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="30"/>'
        '<path d="M34,30 Q44,50 34,70"/><path d="M46,30 Q36,50 46,70"/>'
        '<line x1="40" y1="70" x2="40" y2="100"/>'
        '<line x1="24" y1="72" x2="56" y2="28"/></g>',
    ),
    one_terminal(
        "verin_simple",
        "Vérin simple effet",
        PNEUMATIC,
        f'<g {STROKE}><rect x="4" y="30" width="72" height="30"/>'
        '<line x1="22" y1="30" x2="22" y2="60"/><line x1="22" y1="45" x2="80" '
        'y2="45"/><polyline points="28,32 34,58 40,32 46,58 52,32 58,58 64,32" '
        'stroke-width="1.6"/><line x1="12" y1="60" x2="12" y2="100"/></g>',
        "fond",
        (12, 100),
    ),
    ComponentType(
        "verin_double",
        "Vérin double effet",
        PNEUMATIC,
        (("fond", (12, 100)), ("tige", (66, 100))),
        f'<g {STROKE}><rect x="4" y="30" width="72" height="30"/>'
        '<line x1="30" y1="30" x2="30" y2="60"/><line x1="30" y1="45" x2="80" '
        'y2="45"/><line x1="12" y1="60" x2="12" y2="100"/><line x1="66" y1="60" '
        'x2="66" y2="100"/></g>',
    ),
    one_terminal(
        "silencieux",
        "Silencieux d'échappement",
        PNEUMATIC,
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="40"/>'
        '<rect x="26" y="40" width="28" height="34"/>'
        '<line x1="30" y1="46" x2="50" y2="46"/><line x1="30" y1="56" x2="50" '
        'y2="56"/><line x1="30" y1="66" x2="50" y2="66"/></g>',
        "entrée",
    ),
    one_terminal(
        "manometre",
        "Manomètre",
        PNEUMATIC,
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="32"/>'
        '<circle cx="40" cy="56" r="24"/><line x1="28" y1="68" x2="52" '
        'y2="44"/></g>',
        "prise",
    ),
    ComponentType(
        "reservoir",
        "Réservoir d'huile",
        HYDRAULIC,
        (("aspiration", (26, 30)), ("retour", (54, 30))),
        f'<g {STROKE}><polyline points="10,40 10,84 70,84 70,40"/>'
        '<line x1="26" y1="30" x2="26" y2="74"/><line x1="54" y1="30" x2="54" '
        'y2="74"/></g>',
        node=True,
    ),
    ComponentType(
        "pompe",
        "Pompe hydraulique",
        HYDRAULIC,
        (("refoulement", TOP), ("aspiration", BOTTOM)),
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="22"/>'
        '<circle cx="40" cy="50" r="28"/>'
        '<polygon points="40,24 31,40 49,40" fill="#0f172a"/>'
        '<line x1="40" y1="78" x2="40" y2="100"/></g>',
    ),
    ComponentType(
        "limiteur",
        "Limiteur de pression",
        HYDRAULIC,
        (("réservoir", TOP), ("entrée", BOTTOM)),
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="24"/>'
        '<rect x="24" y="24" width="32" height="52"/>'
        '<line x1="40" y1="76" x2="40" y2="100"/>'
        '<line x1="47" y1="70" x2="47" y2="32"/>'
        '<polygon points="47,30 43,38 51,38" fill="#0f172a"/>'
        '<polyline points="56,50 60,44 64,56 68,44 72,50"/>'
        '<polyline points="40,90 14,90 14,50 24,50" stroke-dasharray="5 3"/></g>',
    ),
    ComponentType(
        "distributeur_43",
        "Distributeur 4/3 à centre fermé",
        HYDRAULIC,
        (("A", (34, 0)), ("B", (46, 0)), ("P", (34, 100)), ("T", (46, 100))),
        f'<g {STROKE}><rect x="4" y="34" width="24" height="32"/>'
        '<rect x="28" y="34" width="24" height="32"/>'
        '<rect x="52" y="34" width="24" height="32"/>'
        '<line x1="34" y1="0" x2="34" y2="34"/><line x1="46" y1="0" x2="46" '
        'y2="34"/><line x1="34" y1="66" x2="34" y2="100"/><line x1="46" y1="66" '
        'x2="46" y2="100"/>'
        '<line x1="30" y1="40" x2="38" y2="40"/><line x1="42" y1="40" x2="50" '
        'y2="40"/><line x1="30" y1="60" x2="38" y2="60"/><line x1="42" y1="60" '
        'x2="50" y2="60"/>'
        '<line x1="10" y1="62" x2="10" y2="38"/><line x1="22" y1="38" x2="22" '
        'y2="62"/><line x1="58" y1="62" x2="70" y2="38"/><line x1="58" y1="38" '
        'x2="70" y2="62"/></g>',
    ),
    ComponentType(
        "clapet",
        "Clapet anti-retour",
        HYDRAULIC,
        (("sortie", TOP), ("entrée", BOTTOM)),
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="40"/>'
        '<circle cx="40" cy="48" r="9"/><polyline points="26,54 40,68 54,54"/>'
        '<line x1="40" y1="68" x2="40" y2="100"/></g>',
    ),
    two_terminals(
        "filtre",
        "Filtre",
        HYDRAULIC,
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="22"/>'
        '<polygon points="40,22 66,50 40,78 14,50"/>'
        '<line x1="16" y1="50" x2="64" y2="50" stroke-dasharray="5 3"/>'
        '<line x1="40" y1="78" x2="40" y2="100"/></g>',
    ),
    two_terminals(
        "moteur_hydraulique",
        "Moteur hydraulique",
        HYDRAULIC,
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="22"/>'
        '<circle cx="40" cy="50" r="28"/>'
        '<polygon points="31,26 49,26 40,42" fill="#0f172a"/>'
        '<line x1="40" y1="78" x2="40" y2="100"/></g>',
    ),
    one_terminal(
        "accumulateur",
        "Accumulateur",
        HYDRAULIC,
        f'<g {STROKE}><rect x="24" y="8" width="32" height="66" rx="16"/>'
        '<line x1="24" y1="40" x2="56" y2="40"/>'
        '<line x1="40" y1="74" x2="40" y2="100"/></g>',
        "raccord",
        BOTTOM,
    ),
    ComponentType(
        "pile",
        "Source de tension continue",
        ELECTRONIC,
        (("+", TOP), ("−", BOTTOM)),
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="42"/>'
        '<line x1="18" y1="42" x2="62" y2="42"/>'
        '<line x1="30" y1="54" x2="50" y2="54" stroke-width="5"/>'
        '<line x1="40" y1="54" x2="40" y2="100"/></g>'
        '<text x="66" y="38" font-size="14" font-weight="bold" '
        'fill="#0f172a">+</text>',
    ),
    two_terminals(
        "resistance",
        "Résistance",
        ELECTRONIC,
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="22"/>'
        '<rect x="30" y="22" width="20" height="56"/>'
        '<line x1="40" y1="78" x2="40" y2="100"/></g>',
    ),
    ComponentType(
        "diode",
        "Diode",
        ELECTRONIC,
        (("anode", TOP), ("cathode", BOTTOM)),
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="34"/>'
        '<polygon points="22,34 58,34 40,64" fill="#0f172a"/>'
        '<line x1="22" y1="64" x2="58" y2="64"/>'
        '<line x1="40" y1="64" x2="40" y2="100"/></g>',
    ),
    ComponentType(
        "led",
        "Diode électroluminescente (LED)",
        ELECTRONIC,
        (("anode", TOP), ("cathode", BOTTOM)),
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="34"/>'
        '<polygon points="22,34 58,34 40,64" fill="#0f172a"/>'
        '<line x1="22" y1="64" x2="58" y2="64"/>'
        '<line x1="40" y1="64" x2="40" y2="100"/>'
        '<line x1="60" y1="46" x2="74" y2="34"/><line x1="60" y1="58" x2="74" '
        'y2="46"/><polyline points="68,34 74,34 74,40"/>'
        '<polyline points="68,46 74,46 74,52"/></g>',
    ),
    two_terminals(
        "condensateur",
        "Condensateur",
        ELECTRONIC,
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="44"/>'
        '<line x1="18" y1="44" x2="62" y2="44"/>'
        '<line x1="18" y1="56" x2="62" y2="56"/>'
        '<line x1="40" y1="56" x2="40" y2="100"/></g>',
    ),
    ComponentType(
        "transistor_npn",
        "Transistor NPN",
        ELECTRONIC,
        (("collecteur", (56, 0)), ("base", (0, 50)), ("émetteur", (56, 100))),
        f'<g {STROKE}><circle cx="44" cy="50" r="28"/>'
        '<line x1="0" y1="50" x2="34" y2="50"/>'
        '<line x1="34" y1="34" x2="34" y2="66"/>'
        '<line x1="34" y1="42" x2="56" y2="26"/><line x1="56" y1="26" x2="56" '
        'y2="0"/><line x1="34" y1="58" x2="56" y2="74"/>'
        '<line x1="56" y1="74" x2="56" y2="100"/>'
        '<polygon points="56,74 46,72 51,65" fill="#0f172a"/></g>',
    ),
    two_terminals(
        "bobine_relais",
        "Bobine de relais",
        ELECTRONIC,
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="34"/>'
        '<rect x="18" y="34" width="44" height="32"/>'
        '<line x1="40" y1="66" x2="40" y2="100"/></g>',
    ),
    two_terminals("interrupteur", "Interrupteur de commande", ELECTRONIC, CONTACT),
    one_terminal(
        "masse",
        "Masse",
        ELECTRONIC,
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="50"/>'
        '<line x1="20" y1="50" x2="60" y2="50"/>'
        '<line x1="28" y1="60" x2="52" y2="60"/>'
        '<line x1="36" y1="70" x2="44" y2="70"/></g>',
        "masse",
    ),
    ComponentType(
        "pont_diodes",
        "Pont de diodes",
        ELECTRONIC,
        (("alternatif", TOP), ("+", (24, 100)), ("−", (56, 100))),
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="20"/>'
        '<polygon points="40,20 68,50 40,80 12,50"/>'
        '<polygon points="32,44 48,44 40,58" fill="#0f172a"/>'
        '<line x1="32" y1="58" x2="48" y2="58"/>'
        '<line x1="24" y1="64" x2="24" y2="100"/>'
        '<line x1="56" y1="64" x2="56" y2="100"/></g>'
        '<text x="12" y="96" font-size="12" font-weight="bold" '
        'fill="#0f172a">+</text>',
    ),
    ComponentType(
        "regulateur",
        "Régulateur de tension",
        ELECTRONIC,
        (("entrée", TOP), ("sortie", BOTTOM), ("masse", (78, 60))),
        f'<g {STROKE}><line x1="40" y1="0" x2="40" y2="28"/>'
        '<rect x="14" y="28" width="52" height="44"/>'
        '<line x1="40" y1="72" x2="40" y2="100"/>'
        '<line x1="66" y1="60" x2="78" y2="60"/></g>'
        '<text x="40" y="55" text-anchor="middle" font-size="12" '
        'font-weight="bold" fill="#0f172a">REG</text>',
    ),
    network_device("internet", "Internet", "Internet"),
    network_device("routeur", "Routeur", "Routeur"),
    network_device("pare_feu", "Pare-feu", "Pare-feu"),
    network_device("switch", "Switch", "Switch"),
    network_device("poste", "Poste de travail", "Poste"),
    network_device("serveur_web", "Serveur web", "Web"),
    network_device("base_donnees", "Serveur de base de données", "BDD"),
    network_device("point_acces", "Point d'accès Wi-Fi", "Wi-Fi"),
)

COMPONENTS = {vType.key: vType for vType in COMPONENT_TYPES}


def build_icon(pKey):
    """Retourne le SVG autonome d'un composant, pour une palette ou une liste."""

    rSvg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
        f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'font-family="Arial, sans-serif">{COMPONENTS[pKey].drawing}</svg>'
    )

    return rSvg
