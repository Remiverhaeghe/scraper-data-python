part of '../revision_state.dart';

/// Progression du jeu reçue du PC, niveaux fêtés, bilan de la semaine et records.
mixin GameProgress on ChangeNotifier {
  Map<String, dynamic> get preferences;

  Future<void> savePreference(String pKey, Object pValue);

  bool get reminderEnabled;

  Reminders? get reminders;

  /// Progression reçue du PC, ou null avant la première synchronisation.
  Map<String, dynamic>? get game {
    final vGame = preferences[gamePreference];

    final rGame = vGame is Map ? Map<String, dynamic>.from(vGame) : null;

    return rGame;
  }

  /// Niveau atteint depuis la dernière fête, ou null : la première progression
  /// reçue sert de référence, sans fête pour l'historique.
  int? get levelToCelebrate {
    final vLevel = (game?['level'] as num?)?.toInt();
    final vCelebrated = (preferences[celebratedLevelPreference] as num?)?.toInt();

    final rLevel = vLevel != null && vCelebrated != null && vLevel > vCelebrated ? vLevel : null;

    return rLevel;
  }

  /// Note le niveau actuel comme fêté.
  Future<void> markLevelCelebrated() async {
    final vLevel = (game?['level'] as num?)?.toInt();

    if (vLevel != null) {
      await savePreference(celebratedLevelPreference, vLevel);
    }
  }

  /// Garde la progression du PC ; la première reçue devient la référence des fêtes.
  Future<void> exchangeGame(ApiClient pClient) async {
    try {
      final vGame = await pClient.downloadGame();

      await savePreference(gamePreference, vGame);

      if (preferences[celebratedLevelPreference] == null && vGame['level'] is num) {
        await savePreference(celebratedLevelPreference, vGame['level'] as num);
      }

      await notifySeason(vGame['season']);
    } on ApiException catch (vException) {
      if (vException.unreachable) {
        rethrow;
      }

      log('Progression non reçue : ${vException.message}', name: 'sync');
    }
  }

  /// Annonce une fois le bilan d'une nouvelle semaine, si les rappels sont actifs.
  Future<void> notifySeason(Object? pSeason) async {
    if (pSeason is! Map || preferences[notifiedSeasonPreference] == '${pSeason['key']}') {
      return;
    }

    if (reminderEnabled && reminders != null) {
      await reminders!.showSeasonReview(Map<String, dynamic>.from(pSeason));
    }

    await savePreference(notifiedSeasonPreference, '${pSeason['key']}');
  }

  /// Meilleur score du jeu « Contre la montre », 0 avant la première partie.
  int get timeAttackBest => (preferences[timeAttackBestPreference] as num?)?.toInt() ?? 0;

  /// Garde le score s'il bat le record ; retourne si c'est un nouveau record.
  Future<bool> recordTimeAttack(int pScore) async {
    final rRecord = pScore > timeAttackBest;

    if (rRecord) {
      await savePreference(timeAttackBestPreference, pScore);
    }

    return rRecord;
  }
}
