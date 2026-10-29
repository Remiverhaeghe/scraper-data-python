# Fiabilité et méthodes de maintenance

## L'essentiel
- Fiabilité : aptitude à fonctionner sans panne (mesurée par le MTBF).
- Maintenabilité : aptitude à être remis en état vite (mesurée par le MTTR).
- Disponibilité : part du temps où l'équipement peut produire ; elle dépend des deux.
- La stratégie de maintenance se choisit selon la criticité de l'équipement et le mode de défaillance, pas par habitude.

## Formules utiles
- MTBF = temps de bon fonctionnement / nombre de défaillances.
- MTTR = somme des durées de réparation / nombre de réparations.
- Disponibilité = MTBF / (MTBF + MTTR).
- Taux de défaillance constant : MTBF = 1 / λ et R(t) = e^(-λt). À t = MTBF, R vaut 37 %, ce n'est pas une durée garantie.
- Éléments en série : fiabilités multipliées, le système est moins fiable que son maillon le plus faible.
- Éléments en parallèle (redondance) : 1 - produit des probabilités de défaillance.
- Backlog = travaux en attente / capacité hebdomadaire de l'équipe.

## Les types de maintenance
- Corrective : après la panne ; palliative (dépannage provisoire) ou curative (réparation définitive).
- Préventive systématique : échéancier fixe (heures, cycles) ; utile contre l'usure prévisible.
- Conditionnelle : seuil d'une mesure dépassé (vibrations, température, huile).
- Prévisionnelle : tendance des mesures extrapolée pour prévoir la défaillance.
- Améliorative : modifier l'équipement pour supprimer une cause de panne.

## Courbe en baignoire et loi de Weibull
- Jeunesse (β < 1) : défauts de fabrication et de montage ; réception, rodage, qualité de montage.
- Maturité (β = 1) : pannes aléatoires ; remplacer à date fixe n'apporte rien, surveiller l'état.
- Vieillissement (β > 1) : usure ; le remplacement préventif devient rentable.

## AMDEC
- Découper l'équipement, lister les modes de défaillance, leurs causes et leurs effets.
- Coter Fréquence, Gravité et Détection (la note de détection est haute quand la défaillance passe inaperçue).
- Criticité = F × G × D ; agir au-delà du seuil, et dès que la gravité est maximale.
- Réévaluer après action et mettre à jour avec le retour d'expérience.

## Surveillance de l'état
- Analyse vibratoire : roulements, balourd (1 × la vitesse), désalignement (souvent 2 × en axial).
- Thermographie : connexions desserrées, surcharges, frottements.
- Analyse d'huile : usure interne, pollution, dégradation du lubrifiant.
- Ultrasons : fuites d'air comprimé, décharges électriques.
- Mesure d'isolement : vieillissement des bobinages.

## GMAO et méthodes
- Chaque intervention a son bon de travail : constats, cause, actions, pièces, temps passé.
- L'historique alimente le Pareto des pannes (par temps d'arrêt et par nombre), le MTBF et l'optimisation du préventif.
- Le magasin se pilote par criticité et valeur (méthode ABC) ; les pièces stratégiques restent en stock malgré leur coût.
- Gammes, kits préparés et dossiers techniques à jour réduisent le MTTR.
- Les niveaux de maintenance (NF X60-000) répartissent les tâches entre opérateur, technicien et spécialiste.

## Sécurité
- Avant toute intervention : consignation (séparer, condamner, identifier, vérifier l'absence d'énergie). En anglais : LOTO.
- Toutes les énergies : électrique, pneumatique, hydraulique, mécanique, thermique.

## Pièges fréquents
- Croire que le MTBF est une durée de vie garantie.
- Multiplier le préventif intrusif : chaque démontage peut introduire un défaut.
- Réparer une panne répétitive sans chercher sa cause racine.
- Laisser un historique GMAO vide : plus aucun indicateur n'est fiable.

## En entretien
- Racontez une analyse : panne répétitive, cause trouvée, action, résultat chiffré (MTBF, temps d'arrêt).
- Montrez que vous savez arbitrer : préventif là où il est rentable, correctif accepté ailleurs.
- Citez la GMAO que vous connaissez (Mainta, Carl Source, Coswin, SAP PM) et ce que vous en avez tiré.

## Références
- [AMDEC (Wikipédia)](https://fr.wikipedia.org/wiki/Analyse_des_modes_de_d%C3%A9faillance,_de_leurs_effets_et_de_leur_criticit%C3%A9)
- [MTBF (Wikipédia)](https://fr.wikipedia.org/wiki/Moyenne_des_temps_de_bon_fonctionnement)
- [GMAO (Wikipédia)](https://fr.wikipedia.org/wiki/Gestion_de_maintenance_assist%C3%A9e_par_ordinateur)
- [Courbe en baignoire (Wikipédia)](https://fr.wikipedia.org/wiki/Courbe_en_baignoire)
- [Maintenance prévisionnelle (Wikipédia)](https://fr.wikipedia.org/wiki/Maintenance_pr%C3%A9visionnelle)
- [Loi de Weibull (Wikipédia)](https://fr.wikipedia.org/wiki/Loi_de_Weibull)
