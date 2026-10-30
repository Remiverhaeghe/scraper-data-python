# Électronique

## L'essentiel
- Composants passifs : résistance, condensateur, bobine. Actifs : diode, transistor, circuit intégré.
- Loi d'Ohm U = R × I et lois de Kirchhoff (somme des courants à un nœud, somme des tensions dans une maille).
- Signaux analogiques (continus) et numériques (0 ou 1, niveaux logiques).

## Composants courants
- Résistance : limite le courant ; code couleur ; puissance dissipée P = R × I².
- Condensateur : stocke une charge, filtre, découple ; attention à la polarité des électrolytiques.
- Diode : laisse passer le courant dans un sens ; diode de roue libre aux bornes d'une bobine de relais.
- LED : toujours avec une résistance de limitation.
- Transistor : interrupteur ou amplificateur commandé ; MOSFET pour commuter des charges.
- Optocoupleur : isole galvaniquement commande et puissance.
- Régulateur de tension : fournit une tension stable (5 V, 3,3 V).

## Formules utiles
- Diviseur de tension : Us = Ue × R2 / (R1 + R2).
- Constante de temps RC : τ = R × C ; charge à 63 % en τ, quasi complète en 5τ.
- Résistance d'une LED : R = (U alim - U LED) / I.
- Fréquence de coupure d'un filtre RC : f = 1 / (2π × R × C).

## Électronique en industrie
- Entrées et sorties d'automates en 24 V, signaux analogiques 0-10 V et 4-20 mA.
- Variateurs de fréquence : redresseur, bus continu, onduleur à IGBT.
- Alimentations à découpage, protections contre les surtensions.
- Compatibilité électromagnétique : blindage relié à la masse, séparation puissance et signaux.

## Mesures
- Multimètre : tension, courant, continuité, test de diode.
- Oscilloscope : forme du signal, fréquence, parasites.
- Attention aux condensateurs chargés, même hors tension.

## Pièges fréquents
- Oublier la diode de roue libre : la surtension de la bobine détruit le transistor.
- Inverser un condensateur électrolytique : il peut éclater.
- Mesurer une résistance sous tension.
- Faire passer des câbles de signaux le long des câbles de puissance.

## En entretien
- Expliquez une carte que vous avez dépannée et la mesure qui a trouvé la panne.
- Montrez que vous connaissez les signaux industriels (24 V, 4-20 mA) et leur câblage.

## Références
- [Loi d'Ohm (Wikipédia)](https://fr.wikipedia.org/wiki/Loi_d%27Ohm)
- [Lois de Kirchhoff (Wikipédia)](https://fr.wikipedia.org/wiki/Lois_de_Kirchhoff)
- [Transistor (Wikipédia)](https://fr.wikipedia.org/wiki/Transistor)
- [Diode (Wikipédia)](https://fr.wikipedia.org/wiki/Diode)
- [Compatibilité électromagnétique (Wikipédia)](https://fr.wikipedia.org/wiki/Compatibilit%C3%A9_%C3%A9lectromagn%C3%A9tique)
