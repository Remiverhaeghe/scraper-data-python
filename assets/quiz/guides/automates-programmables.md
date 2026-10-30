# Automates programmables

## L'essentiel
- L'automate (API, PLC) lit ses entrées, exécute son programme, puis écrit ses sorties, en boucle : le cycle automate.
- Les entrées sont lues une fois en début de cycle (image des entrées) : une impulsion plus courte qu'un cycle peut être manquée.
- Constructeurs courants : Siemens (TIA Portal), Schneider (EcoStruxure Control Expert, Machine Expert), Rockwell (Studio 5000), Omron.

## Langages (IEC 61131-3)
- LD (ladder, contacts et bobines), FBD (blocs fonctionnels), ST (texte structuré), SFC (grafcet), IL (liste, abandonnée).
- Temporisations : TON (retard à l'enclenchement), TOF (retard au déclenchement), TP (impulsion).
- Compteurs : CTU, CTD ; fronts montant et descendant (R_TRIG, F_TRIG).
- Bascule mémoire : SET et RESET, ou bobine auto-maintenue.

## Entrées et sorties
- TOR 24 V : PNP (sortie qui fournit le +24 V) ou NPN, à accorder avec la carte d'entrée.
- Analogiques : 0-10 V, 4-20 mA, avec mise à l'échelle dans le programme.
- Sorties relais (polyvalentes, lentes) ou transistor (rapides, en courant continu).
- Réseaux : Profinet, EtherNet/IP, Modbus TCP, Profibus.

## Dépannage
- Commencer par l'état des voyants d'entrées et de sorties sur la carte.
- Visualiser le programme en ligne et forcer avec prudence, machine sécurisée.
- Lire le diagnostic de la CPU (tampon de diagnostic, défauts de modules, réseau).
- Comparer le programme à la version de référence avant toute modification.

## Sécurité
- Les fonctions de sécurité passent par des automates ou relais de sécurité certifiés, pas par l'automate standard.
- Un forçage oublié peut mettre une machine en danger : on les liste et on les retire.
- Sauvegarder les programmes et les tracer (cybersécurité).

## Pièges fréquents
- Écrire la même sortie à deux endroits du programme : seule la dernière écriture compte.
- Oublier qu'une entrée change entre deux cycles.
- Mélanger capteur PNP et carte NPN.
- Modifier en ligne sans sauvegarde ni information de l'équipe.

## En entretien
- Expliquez le cycle automate et un dépannage par visualisation en ligne.
- Citez l'environnement que vous connaissez et les langages utilisés.

## Références
- [Automate programmable industriel (Wikipédia)](https://fr.wikipedia.org/wiki/Automate_programmable_industriel)
- [CEI 61131-3 (Wikipédia)](https://fr.wikipedia.org/wiki/CEI_61131-3)
- [Langage Ladder (Wikipédia)](https://fr.wikipedia.org/wiki/Langage_Ladder)
- [Grafcet (Wikipédia)](https://fr.wikipedia.org/wiki/Grafcet)
