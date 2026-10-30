# Régulation et boucles PID

## L'essentiel
- Une boucle de régulation maintient une mesure égale à une consigne malgré les perturbations.
- Éléments : capteur (mesure), régulateur (calcule l'écart et la commande), actionneur (vanne, variateur, résistance).
- Boucle ouverte : pas de retour de mesure. Boucle fermée : la mesure corrige la commande.

## Les actions du PID
- P (proportionnelle) : commande proportionnelle à l'écart ; rapide, mais laisse souvent un écart statique.
- I (intégrale) : accumule l'écart dans le temps et l'annule ; trop forte, elle fait osciller.
- D (dérivée) : réagit à la vitesse de variation ; amortit, mais amplifie le bruit de mesure.
- Bande proportionnelle (%) = 100 / gain : plus elle est faible, plus l'action est forte.

## Réglage
- Commencer par P seul, ajouter I pour supprimer l'écart, D si la boucle est lente et oscillante.
- Méthodes : Ziegler-Nichols (limite de pompage), méthode de Broïda (réponse indicielle).
- Critères : temps de réponse, dépassement, stabilité, précision.
- Sens d'action : direct ou inverse selon que la commande doit augmenter quand la mesure augmente.

## Structures courantes
- Régulation en cascade : une boucle rapide (débit) asservie à une boucle lente (température).
- Régulation de rapport : maintenir un rapport entre deux débits.
- Tout ou rien avec hystérésis : thermostat simple.

## Diagnostic
- Mesure qui oscille : gain trop fort, intégrale trop forte, vanne qui colle.
- Écart permanent : intégrale absente ou actionneur en butée (saturation).
- Vérifier d'abord le capteur et l'actionneur avant de toucher aux réglages.

## Pièges fréquents
- Régler le PID pour compenser une vanne défectueuse.
- Oublier l'anti-saturation de l'intégrale (windup).
- Mettre de la dérivée sur une mesure bruitée.

## En entretien
- Expliquez le rôle de P, I et D avec un exemple (température d'un four).
- Racontez un réglage ou un diagnostic de boucle.

## Références
- [Régulateur PID (Wikipédia)](https://fr.wikipedia.org/wiki/R%C3%A9gulateur_PID)
- [Régulation automatique (Wikipédia)](https://fr.wikipedia.org/wiki/R%C3%A9gulation_automatique)
- [Méthode de Ziegler-Nichols (Wikipédia)](https://fr.wikipedia.org/wiki/M%C3%A9thode_de_Ziegler-Nichols)
