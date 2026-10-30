# Capteurs et actionneurs

## L'essentiel
- Le capteur transforme une grandeur physique en signal ; l'actionneur transforme un ordre en action.
- Capteurs TOR (présence oui ou non) et analogiques (valeur continue : température, pression, niveau).
- Choisir un capteur : grandeur, plage, précision, temps de réponse, environnement, signal de sortie.

## Capteurs de présence
- Inductif : détecte les métaux, sans contact, portée de quelques millimètres.
- Capacitif : détecte aussi les non-métaux (plastique, liquide), réglable.
- Photoélectrique : barrage (émetteur et récepteur face à face), reflex (réflecteur), proximité (sur l'objet).
- Fin de course mécanique : simple, fiable, à contact.
- Câblage 3 fils PNP ou NPN, contact NO (normalement ouvert) ou NF (normalement fermé).

## Mesures analogiques
- Température : sonde Pt100 (précise), thermocouple (hautes températures).
- Pression : capteur à membrane, transmetteur 4-20 mA.
- Niveau : flotteur, ultrasons, radar, pression hydrostatique.
- Débit : électromagnétique (liquides conducteurs), vortex, Coriolis (débit massique).
- Position et vitesse : codeur incrémental ou absolu, résolveur.

## Actionneurs
- Moteurs asynchrones (avec contacteur ou variateur), moteurs pas à pas, servomoteurs.
- Vérins pneumatiques et hydrauliques, pilotés par distributeurs.
- Électrovannes, résistances chauffantes, voyants et avertisseurs.
- Pré-actionneurs : contacteur, distributeur, variateur, relais.

## Formules utiles
- Signal 4-20 mA : valeur = (I - 4) / 16 × étendue de mesure.
- Pt100 : environ 100 Ω à 0 °C, + 0,385 Ω par °C.
- Codeur incrémental : vitesse = impulsions par seconde / résolution.

## Pièges fréquents
- Confondre NO et NF : une sécurité doit souvent utiliser un contact NF (rupture de fil détectée).
- Choisir un inductif pour détecter une pièce plastique.
- Monter un photoélectrique face à une surface brillante qui renvoie le faisceau.
- Oublier l'étalonnage des capteurs de mesure.

## En entretien
- Expliquez comment vous choisiriez un capteur pour un cas concret.
- Racontez un remplacement de capteur et son réglage.

## Références
- [Capteur (Wikipédia)](https://fr.wikipedia.org/wiki/Capteur)
- [Capteur de proximité (Wikipédia)](https://fr.wikipedia.org/wiki/Capteur_de_proximit%C3%A9)
- [Actionneur (Wikipédia)](https://fr.wikipedia.org/wiki/Actionneur)
- [Codeur rotatif (Wikipédia)](https://fr.wikipedia.org/wiki/Codeur_rotatif)
