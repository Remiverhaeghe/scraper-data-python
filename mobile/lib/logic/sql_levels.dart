// Niveaux du bac à sable SQL, hors ligne : vérification d'une requête identique
// à job/sql_levels.py, sur le contenu reçu du PC.

import 'sql_sandbox.dart';

final _simpleColumn = RegExp(r'^[\p{L}\p{N}\p{M}_]+$', unicode: true);

/// Champ du niveau, propre au dialecte quand il en dépend.
Object? pick(Map<String, dynamic> pLevel, String pKey, String pDialect) {
  final vValue = pLevel[pKey];

  return vValue is Map ? vValue[pDialect] : vValue;
}

/// Masque les en-têtes calculés, qui donneraient la réponse : « colonne n ».
List<String> maskColumns(List pColumns) => [
      for (var vIndex = 0; vIndex < pColumns.length; vIndex++)
        _simpleColumn.hasMatch(pColumns[vIndex] as String)
            ? pColumns[vIndex] as String
            : 'colonne ${vIndex + 1}',
    ];

/// Conseils des erreurs classiques reconnues dans la requête.
List<String> findPitfalls(Map<String, dynamic> pLevel, String pQuery) => [
      for (final vPitfall in pLevel['pitfalls'] as List? ?? const [])
        if (RegExp((vPitfall as List)[0] as String, caseSensitive: false).hasMatch(pQuery))
          vPitfall[1] as String,
    ];

/// Niveaux SQL avec le résultat de leurs solutions, calculé une fois par dialecte.
class SqlLevels {
  SqlLevels(this.content);

  final SqlContent content;
  final _expected = <String, Future<Map<String, dynamic>>>{};

  Future<Map<String, dynamic>> expectedOf(Map<String, dynamic> pLevel, String pDialect) =>
      _expected.putIfAbsent(
        '${pLevel['id']}/$pDialect',
        () => content.execute(
          pick(pLevel, 'solution', pDialect) as String,
          pDialect,
          pLevel['check'] as String? ?? '',
        ),
      );

  /// Exécute la requête et la compare au résultat attendu du niveau.
  Future<Map<String, dynamic>> runLevel(
      Map<String, dynamic> pLevel, String pQuery, String pDialect) async {
    final vExpected = await expectedOf(pLevel, pDialect);
    final vCheck = pLevel['check'] as String? ?? '';
    final vResult = await content.execute(pQuery, pDialect, vCheck);
    var vMessage = vResult['error'] as String;

    if (vMessage.isEmpty && vCheck.isEmpty && vResult['changed'] != null) {
      vMessage = 'Ce niveau attend une requête SELECT : la vôtre modifie la base.';
    }

    if (vMessage.isEmpty) {
      vMessage = compareResults(vResult, vExpected, pLevel['ordered'] == true);
    }

    final vPassed = vMessage.isEmpty;

    return {
      'result': vResult,
      'expected': {...vExpected, 'columns': maskColumns(vExpected['columns'] as List)},
      'passed': vPassed,
      'message': vMessage,
      'advice': vPassed ? <String>[] : findPitfalls(pLevel, pQuery),
    };
  }
}
