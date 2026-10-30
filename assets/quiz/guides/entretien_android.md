# Entretien Android

## L'essentiel
- Les questions portent sur les cycles de vie, les composants, l'architecture et la gestion des ressources.
- Kotlin est le langage recommandé ; Jetpack Compose remplace progressivement les vues XML.

## Cycle de vie
- Activité : onCreate, onStart, onResume, onPause, onStop, onDestroy ; onRestart au retour.
- Rotation de l'écran : l'activité est recréée ; garder l'état dans un ViewModel ou avec onSaveInstanceState.
- Fragment : cycle proche, avec une vue qui peut être détruite indépendamment.

## Composants
- Activity, Service, BroadcastReceiver, ContentProvider.
- Intent explicite (composant précis) ou implicite (action, l'utilisateur choisit l'application).
- WorkManager pour les tâches en arrière-plan garanties.
- Permissions demandées à l'exécution pour les données sensibles.

## Architecture
- MVVM : ViewModel exposant un état observable (StateFlow, LiveData) à l'interface.
- Repository qui centralise les sources (réseau, base Room).
- Coroutines pour l'asynchrone ; ne jamais bloquer le thread principal.
- Injection de dépendances (Hilt).

## Performances et qualité
- Éviter les fuites de mémoire : pas de référence à une activité dans un objet de longue durée.
- Listes efficaces (RecyclerView, LazyColumn).
- Tests unitaires et tests d'interface (Espresso, tests Compose).

## Pièges fréquents
- Faire un appel réseau sur le thread principal.
- Perdre l'état à la rotation.
- Garder un Context d'activité dans un singleton.

## Références
- [Documentation Android](https://developer.android.com/guide)
- [Cycle de vie d'une activité](https://developer.android.com/guide/components/activities/activity-lifecycle)
- [Guide de l'architecture des applications](https://developer.android.com/topic/architecture)
