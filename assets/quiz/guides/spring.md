# Spring et Spring Boot

## L'essentiel
- Spring fournit l'inversion de contrôle : le conteneur crée les objets (beans) et injecte leurs dépendances.
- Spring Boot simplifie la configuration : démarreurs (starters), configuration automatique, serveur embarqué.
- Une application se configure dans application.properties ou application.yml, par profil (dev, prod).

## Injection de dépendances
- Annotations de composants : @Component, @Service, @Repository, @Controller, @RestController.
- Préférer l'injection par constructeur : dépendances explicites, tests faciles.
- @Configuration et @Bean pour déclarer des beans à la main.
- Portées : singleton par défaut, prototype, request, session.

## Web
- @RestController, @GetMapping, @PostMapping, @PathVariable, @RequestParam, @RequestBody.
- Validation avec @Valid et les annotations Jakarta (@NotNull, @Size).
- Gestion des erreurs centralisée avec @ControllerAdvice et @ExceptionHandler.

## Données
- Spring Data JPA : interfaces Repository, méthodes dérivées (findByNom), @Query.
- @Transactional : délimite les transactions ; attention aux appels internes à la même classe.
- Problème N+1 : charger les relations avec des jointures (fetch join, EntityGraph).

## Sécurité et tests
- Spring Security : chaîne de filtres, authentification, autorisation par rôle.
- @SpringBootTest pour les tests d'intégration, @WebMvcTest et @DataJpaTest pour des tranches ciblées.
- Mockito pour simuler les dépendances.

## Exploitation
- Actuator : santé (/actuator/health), métriques, informations.
- Journaux avec SLF4J et Logback ; niveaux réglables par paquet.

## Pièges fréquents
- Appeler une méthode @Transactional depuis la même classe : le proxy n'intervient pas.
- Injection par champ (@Autowired sur un attribut) qui complique les tests.
- Charger des relations paresseuses hors transaction (LazyInitializationException).
- Exposer directement les entités JPA dans l'API.

## En entretien
- Expliquez l'inversion de contrôle et le rôle du conteneur.
- Décrivez une API REST que vous avez faite : couches, validation, erreurs, tests.

## Références
- [Spring Boot (documentation)](https://docs.spring.io/spring-boot/index.html)
- [Spring Framework (documentation)](https://docs.spring.io/spring-framework/reference/)
- [Guides Spring](https://spring.io/guides)
