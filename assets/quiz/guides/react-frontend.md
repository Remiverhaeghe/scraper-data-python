# Frameworks frontend (React, Angular, Vue)

## L'essentiel
- Ces frameworks construisent l'interface en composants réutilisables qui se mettent à jour quand les données changent.
- React : bibliothèque de composants en JSX, très répandue. Angular : framework complet en TypeScript. Vue : progressif, simple à adopter.

## React
- Composants fonctions qui reçoivent des props et retournent du JSX.
- État local avec useState ; effets (appels réseau, abonnements) avec useEffect et son tableau de dépendances.
- Les listes ont besoin d'une key stable et unique.
- Contexte pour partager une donnée sans la passer à chaque niveau ; bibliothèques d'état pour les cas complexes.
- Ne jamais modifier l'état directement : créer une nouvelle valeur.

## Angular
- Composants, modules ou composants autonomes, services injectés.
- Liaisons de données : interpolation, propriété, événement, double liaison.
- RxJS et observables pour l'asynchrone ; signaux dans les versions récentes.

## Vue
- Composants monofichiers (.vue) ; réactivité avec ref et reactive.
- Directives v-if, v-for, v-model ; propriétés calculées (computed).

## Bonnes pratiques communes
- Petits composants, données qui descendent, événements qui remontent.
- Typage avec TypeScript, tests de composants (Testing Library, Vitest, Jest).
- Accessibilité : vrais boutons, libellés, navigation au clavier.
- Performance : éviter les rendus inutiles, charger à la demande.

## Pièges fréquents
- Oublier une dépendance de useEffect, ou en provoquer une boucle infinie.
- Utiliser l'index du tableau comme key d'une liste qui change.
- Muter un objet d'état et ne pas voir l'écran se mettre à jour.

## En entretien
- Expliquez le cycle de rendu et le rôle de l'état.
- Décrivez une interface que vous avez construite et ses composants.

## Références
- [React (documentation)](https://react.dev/learn)
- [Angular (documentation)](https://angular.dev/overview)
- [Vue.js (documentation)](https://vuejs.org/guide/introduction.html)
