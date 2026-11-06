part of '../revision_state.dart';

/// Bac à sable SQL : niveaux, moteur, dialecte, requêtes en cours et niveaux réussis.
mixin SqlSimulation on LabsState {
  SqlLevels? _sqlLevels;
  Object? _sqlSource;

  Map<String, dynamic> get sqlPackage => Map<String, dynamic>.from(labs['sql'] as Map? ?? const {});

  /// Niveaux SQL et leur moteur, refaits seulement quand le contenu reçu change.
  SqlLevels? get sqlLevels {
    final vPackage = labs['sql'];

    if (vPackage == null) {
      return null;
    }

    if (!identical(vPackage, _sqlSource)) {
      _sqlSource = vPackage;
      _sqlLevels = SqlLevels(SqlContent.fromJson(Map<String, dynamic>.from(vPackage as Map)));
    }

    return _sqlLevels;
  }

  List<Map<String, dynamic>> get sqlLevelList => [
        for (final vItem in sqlPackage['levels'] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  int get sqlXp => (sqlPackage['xp'] as num? ?? 15).toInt();

  /// Dialecte choisi sur le téléphone, celui du PC à défaut.
  String get sqlDialect =>
      preferences[sqlDialectPreference] as String? ?? sqlPackage['dialect'] as String? ?? 'mysql';

  Future<void> setSqlDialect(String pDialect) => savePreference(sqlDialectPreference, pDialect);

  /// Niveaux SQL réussis, sur le PC ou sur le téléphone.
  Set<String> get sqlPassed => {
        for (final vId in sqlPackage['passed'] as List? ?? const []) vId as String,
        for (final vId in preferences[sqlPassedPreference] as List? ?? const []) vId as String,
      };

  /// Dernière requête écrite pour un niveau, ou son point de départ.
  String sqlQuery(Map<String, dynamic> pLevel) =>
      (preferences[sqlQueriesPreference] as Map?)?[pLevel['id']] as String? ??
      pLevel['starter'] as String;

  Future<void> saveSqlQuery(String pLevelId, String pQuery) => savePreference(
        sqlQueriesPreference,
        {
          ...Map<String, dynamic>.from(preferences[sqlQueriesPreference] as Map? ?? const {}),
          pLevelId: pQuery
        },
      );

  /// Garde un niveau SQL réussi ; la requête part au PC, qui la réexécute.
  Future<bool> recordSql(String pLevelId, String pQuery, String pDialect) async {
    final rFirst = !sqlPassed.contains(pLevelId);

    await queueLab(
      'sql',
      {'level': pLevelId, 'query': pQuery, 'dialect': pDialect},
      pChanges: {
        sqlPassedPreference: [...sqlPassed, if (rFirst) pLevelId]
      },
    );

    return rFirst;
  }
}
