# Entretien Java

## L'essentiel
- L'entretien technique Java mêle questions de cours, lecture de code piégé, revue de code et conception.
- On attend un raisonnement à voix haute plus qu'une réponse récitée.

## Les classiques à maîtriser
- equals et hashCode, == et equals, immutabilité de String.
- ArrayList et LinkedList, HashMap (fonctionnement, collisions), HashSet.
- Exceptions vérifiées et non vérifiées, try-with-resources.
- Streams : filter, map, collect, groupingBy ; Optional.
- Interfaces et classes abstraites, polymorphisme, surcharge et redéfinition.
- Concurrence : synchronized, volatile, ExecutorService, ConcurrentHashMap.
- JVM : tas et pile, ramasse-miettes, fuites de mémoire.

## Code piégé fréquent
- Integer comparés avec == (cache entre -128 et 127).
- Modification d'une liste pendant un for-each.
- Division entière (5 / 2 = 2).
- finally qui écrase un return.
- static partagé entre instances.

## Patterns et conception
- Singleton, Factory, Builder, Strategy, Observer, Decorator : savoir quand et pourquoi.
- SOLID et injection de dépendances (Spring).
- Concevoir une petite API : couches, validation, erreurs, tests.

## Méthode en direct
- Reformuler la question, citer les cas limites (null, liste vide, très grand volume).
- Proposer une solution simple, puis l'améliorer.
- Tester mentalement avec un exemple.

## Pièges fréquents
- Répondre trop vite sans lire tout le code.
- Ne pas oser dire « je ne sais pas, mais voici comment je chercherais ».

## Références
- [Documentation Java (Oracle)](https://docs.oracle.com/en/java/javase/21/)
- [Dev.java (Oracle)](https://dev.java/learn/)
- [Patron de conception (Wikipédia)](https://fr.wikipedia.org/wiki/Patron_de_conception)
