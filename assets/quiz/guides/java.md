# Java

## L'essentiel
- Langage objet compilé en bytecode, exécuté par la JVM : « écrire une fois, exécuter partout ».
- Typage statique, gestion automatique de la mémoire (ramasse-miettes).
- Versions LTS à connaître : 8, 11, 17, 21.

## Bases du langage
- Types primitifs (int, long, double, boolean) et objets ; boxing automatique (Integer).
- Comparer des objets avec equals, pas avec == (qui compare les références).
- Redéfinir equals et hashCode ensemble pour les objets placés dans un HashSet ou une HashMap.
- String est immuable ; StringBuilder pour concaténer en boucle.
- Exceptions vérifiées (à déclarer ou attraper) et non vérifiées (RuntimeException).

## Collections
- List (ArrayList, LinkedList), Set (HashSet, TreeSet), Map (HashMap, TreeMap).
- HashMap : accès en temps constant moyen ; TreeMap : clés triées.
- Collections immuables : List.of, Map.of (Java 9+).

## Java moderne
- Java 8 : lambdas, streams (filter, map, collect), Optional, nouvelle API de dates (java.time).
- Java 10 : var pour l'inférence de type locale.
- Java 14-17 : records, switch expressions, text blocks, sealed classes.
- Java 21 : pattern matching pour switch, threads virtuels.

## Mémoire et performances
- Tas (objets) et pile (appels, variables locales) ; OutOfMemoryError et StackOverflowError.
- Ramasse-miettes G1 par défaut ; fuites possibles via des références gardées (caches, listeners).
- Outils : jstack, jmap, VisualVM, JDK Mission Control.

## Concurrence
- Thread, ExecutorService, CompletableFuture.
- synchronized, volatile, classes de java.util.concurrent (ConcurrentHashMap, AtomicInteger).

## Pièges fréquents
- Comparer des chaînes avec ==.
- Modifier une collection pendant qu'on la parcourt (ConcurrentModificationException).
- Avaler une exception sans la journaliser.
- Retourner null au lieu d'un Optional ou d'une collection vide.

## En entretien
- Expliquez equals et hashCode, la différence entre ArrayList et LinkedList, le fonctionnement d'une HashMap.
- Montrez un exemple de stream et un record.
- Parlez d'un problème de performance ou de mémoire que vous avez diagnostiqué.

## Références
- [Documentation Java (Oracle)](https://docs.oracle.com/en/java/javase/21/)
- [Java (Wikipédia)](https://fr.wikipedia.org/wiki/Java_%28langage%29)
- [Dev.java (Oracle)](https://dev.java/learn/)
