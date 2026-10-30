# TypeScript

## L'essentiel
- TypeScript ajoute un typage statique à JavaScript, vérifié à la compilation puis effacé.
- Il détecte des erreurs avant l'exécution et améliore l'autocomplétion.
- Configuration dans tsconfig.json ; activer strict.

## Types
- Types de base : string, number, boolean, null, undefined, any (à éviter), unknown (à vérifier avant usage).
- Unions (string | number) et types littéraux ("ouvert" | "ferme").
- interface et type pour décrire des objets ; propriétés optionnelles (?) et en lecture seule (readonly).
- Tableaux (number[]), tuples ([string, number]), enum ou unions littérales.

## Types avancés
- Génériques : function premier<T>(liste: T[]): T.
- Types utilitaires : Partial, Required, Pick, Omit, Record, ReturnType.
- Rétrécissement (narrowing) avec typeof, in, instanceof et gardes de type.
- Unions discriminées : un champ commun (kind) distingue les variantes.

## Bonnes pratiques
- Mode strict, pas de any implicite.
- unknown plutôt que any pour les données externes, puis validation (zod par exemple).
- Typer les réponses d'API à la frontière de l'application.

## Pièges fréquents
- Croire que les types existent à l'exécution : une donnée JSON non validée peut mentir.
- Abuser de as pour faire taire le compilateur.
- Confondre interface (extensible par fusion) et type (alias, unions possibles).

## En entretien
- Expliquez any, unknown et never.
- Montrez un générique et un type utilitaire.

## Références
- [Documentation TypeScript](https://www.typescriptlang.org/docs/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
