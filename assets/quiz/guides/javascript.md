# JavaScript

## L'essentiel
- Langage du navigateur, aussi utilisé côté serveur avec Node.js.
- Typage dynamique, fonctions de première classe, programmation asynchrone.
- Le DOM représente la page ; on le manipule pour réagir aux actions de l'utilisateur.

## Variables et types
- let et const (portée de bloc) ; éviter var (portée de fonction, remontée).
- Comparer avec === (sans conversion) plutôt que ==.
- Valeurs « fausses » : false, 0, "", null, undefined, NaN.
- null : absence voulue ; undefined : valeur non définie.

## Fonctions et objets
- Fonctions fléchées : pas de this propre.
- Fermetures (closures) : une fonction garde l'accès aux variables de son contexte.
- Objets et prototypes ; classes (sucre syntaxique sur les prototypes).
- Déstructuration, opérateur de décomposition (...), chaînage optionnel (?.) et coalescence (??).

## Asynchrone
- Boucle d'événements : le code ne bloque pas en attendant le réseau.
- Promesses (then, catch) et async/await.
- fetch pour les requêtes HTTP ; gérer les erreurs réseau et les codes HTTP.

## Tableaux
- map, filter, reduce, find, some, every, sort (attention : sort compare en texte par défaut).
- Préférer les méthodes qui ne modifient pas le tableau d'origine.

## Sécurité
- Ne pas insérer de texte utilisateur avec innerHTML (risque XSS) : textContent.
- Content Security Policy pour limiter les scripts exécutables.

## Pièges fréquents
- [10, 2, 1].sort() donne [1, 10, 2] : fournir une fonction de comparaison.
- Oublier await et manipuler une promesse au lieu de sa valeur.
- Confondre this dans une fonction classique et dans une fonction fléchée.
- 0.1 + 0.2 !== 0.3 : arrondir pour comparer des montants.

## En entretien
- Expliquez la boucle d'événements et async/await.
- Montrez une fermeture et une utilisation de map ou reduce.

## Références
- [JavaScript (MDN)](https://developer.mozilla.org/fr/docs/Web/JavaScript)
- [Guide JavaScript (MDN)](https://developer.mozilla.org/fr/docs/Web/JavaScript/Guide)
- [Fonctions asynchrones (MDN)](https://developer.mozilla.org/fr/docs/Web/JavaScript/Reference/Statements/async_function)
