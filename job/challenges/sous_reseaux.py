"""Défi : l'inventaire des sous-réseaux d'un site"""

import ipaddress

ID = "sous-reseaux"
TITLE = "L'inventaire des sous-réseaux"
SERIES = "Réseau"
LEVEL = "intermédiaire"

STATEMENTS = (
    """L'équipe réseau a exporté les adresses des équipements du site, chacune avec son
préfixe, sous la forme `adresse/préfixe`. Un réseau de préfixe p compte 2^(32 − p)
adresses, dont 2 réservées : l'adresse du réseau et celle de diffusion.

**Plusieurs équipements partagent souvent le même réseau. Combien de réseaux distincts
la liste contient-elle ?**""",
    """Pour préparer une migration, l'équipe veut connaître la capacité totale.

**Quelle est la somme des adresses utilisables, 2^(32 − p) − 2, sur l'ensemble des
réseaux distincts ?**""",
)
EXAMPLE = """192.168.1.10/24
192.168.1.200/24
10.0.4.17/22
10.0.7.1/22
172.16.0.5/30"""
EXAMPLE_ANSWERS = ("3", "1278")
HINTS = (
    "L'adresse du réseau s'obtient avec un ET binaire entre l'adresse et le masque.",
    "10.0.4.17/22 et 10.0.7.1/22 appartiennent au même réseau 10.0.4.0/22.",
)
NOTE = """Le module `ipaddress` de Python fait le calcul avec `ip_network(texte,
strict=False)`. À la main : le masque d'un préfixe p a ses p premiers bits à 1, et le
réseau vaut adresse ET masque. Un ensemble suffit ensuite à compter les réseaux
distincts."""


def generate(pRandom):
    """Retourne une liste d'adresses réparties sur quelques dizaines de réseaux."""

    vLines = []

    for _ in range(pRandom.randint(30, 50)):
        vPrefix = pRandom.randint(16, 30)
        vBase = int(
            ipaddress.ip_network(
                f"10.{pRandom.randint(0, 255)}.{pRandom.randint(0, 255)}.0/{vPrefix}",
                strict=False,
            ).network_address
        )
        vSize = 2 ** (32 - vPrefix)

        for _ in range(pRandom.randint(1, 6)):
            vAddress = ipaddress.ip_address(vBase + pRandom.randint(1, vSize - 2))
            vLines.append(f"{vAddress}/{vPrefix}")

    rInput = "\n".join(pRandom.sample(vLines, len(vLines)))

    return rInput


def solve(pInput):
    """Retourne le nombre de réseaux distincts et leur nombre d'adresses utilisables."""

    vNetworks = {
        ipaddress.ip_network(vLine.strip(), strict=False)
        for vLine in pInput.strip().splitlines()
    }

    rAnswers = (
        str(len(vNetworks)),
        str(sum(vNetwork.num_addresses - 2 for vNetwork in vNetworks)),
    )

    return rAnswers
