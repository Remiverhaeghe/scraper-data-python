// Puzzles de code, réécrits depuis job/code_puzzles.py : correction, niveau après
// une série et tirage d'une série de difficulté croissante. Les puzzles et les
// règles viennent du PC, qui recorrige chaque série à la synchronisation.

import 'dart:math';

import 'python_compat.dart';

const _maxTextAnswerLength = 200;

/// Erreur d'une réponse incomplète ou illisible, avec le message du PC.
class PuzzleAnswerError implements Exception {
  const PuzzleAnswerError(this.message);

  final String message;

  @override
  String toString() => message;
}

/// Bonne réponse d'un puzzle, au format des réponses saisies.
Object answerOf(Map<String, dynamic> pPuzzle) => switch (pPuzzle['type']) {
      'ordre' => [
          for (var vIndex = 0; vIndex < (pPuzzle['items'] as List).length; vIndex++) vIndex
        ],
      'saisie' => (pPuzzle['accepted'] as List).first as String,
      _ => (pPuzzle['line'] as int) - 1,
    };

String _normalizeCode(String pText) => pySplit(pText).join(' ');

/// Corrige une réponse : (juste, réponse donnée, réponse attendue), ou lève PuzzleAnswerError.
(bool, String, String) gradePuzzle(Map<String, dynamic> pPuzzle, Object? pResponse) {
  switch (pPuzzle['type']) {
    case 'ordre':
      final vItems = List<String>.from(pPuzzle['items'] as List);

      if (pResponse is! List ||
          pResponse.length != vItems.length ||
          pResponse.any((pIndex) => pIndex is! int || pIndex < 0 || pIndex >= vItems.length)) {
        throw const PuzzleAnswerError('Réponse incomplète.');
      }

      final vIndexes = List<int>.from(pResponse);

      if (vIndexes.toSet().length != vItems.length) {
        throw const PuzzleAnswerError('Chaque élément doit avoir sa propre place.');
      }

      return (
        [for (var vIndex = 0; vIndex < vIndexes.length; vIndex++) vIndexes[vIndex] == vIndex]
            .every((pOk) => pOk),
        vIndexes.map((pIndex) => vItems[pIndex]).join(' → '),
        vItems.join(' → '),
      );
    case 'saisie':
      final vRaw = pResponse == null || pResponse == false || pResponse == 0 ? '' : '$pResponse';
      var vAnswer = pyStrip(vRaw);

      if (vAnswer.isEmpty) {
        throw const PuzzleAnswerError('Saisissez une réponse.');
      }

      if (vAnswer.length > _maxTextAnswerLength) {
        vAnswer = vAnswer.substring(0, _maxTextAnswerLength);
      }

      final vAccepted = List<String>.from(pPuzzle['accepted'] as List);

      return (
        vAccepted.map(_normalizeCode).contains(_normalizeCode(vAnswer)),
        vAnswer,
        vAccepted.first,
      );
    default:
      final vLines = List<String>.from(pPuzzle['lines'] as List);
      final vLine = pPuzzle['line'] as int;

      if (pResponse is! int || pResponse < 0 || pResponse >= vLines.length) {
        throw const PuzzleAnswerError('Touchez la ligne fautive.');
      }

      return (
        pResponse == vLine - 1,
        'ligne ${pResponse + 1} : ${pyStrip(vLines[pResponse])}',
        'ligne $vLine : ${pyStrip(vLines[vLine - 1])}',
      );
  }
}

/// Règles des séries reçues du PC : longueur, composition, seuils de niveau.
class PuzzleRules {
  PuzzleRules(Map<String, dynamic> pRules)
      : seriesLength = (pRules['series_length'] as num? ?? 10).toInt(),
        levelUp = (pRules['level_up'] as num? ?? 8).toInt(),
        levelDown = (pRules['level_down'] as num? ?? 4).toInt(),
        plan = [
          for (final vStep in pRules['plan'] as List? ?? const [])
            ((vStep as List)[0] as int, vStep[1] as int),
        ],
        levels = Map<String, dynamic>.from(pRules['levels'] as Map? ?? const {}),
        types = Map<String, dynamic>.from(pRules['types'] as Map? ?? const {});

  final int seriesLength;
  final int levelUp;
  final int levelDown;
  final List<(int, int)> plan;
  final Map<String, dynamic> levels;
  final Map<String, dynamic> types;

  int get _lowest => levels.keys.map(int.parse).reduce(min);
  int get _highest => levels.keys.map(int.parse).reduce(max);

  String levelLabel(int pLevel) => levels['$pLevel'] as String? ?? '';

  /// Niveau après une série : plus haut si elle est bonne, plus bas sinon.
  int nextLevel(int pLevel, int pScore) {
    if (pScore >= levelUp) {
      return min(pLevel + 1, _highest);
    }

    if (pScore <= levelDown) {
      return max(pLevel - 1, _lowest);
    }

    return pLevel;
  }

  /// Puzzles d'une série, du plus facile au plus dur : jamais vus, puis manqués, puis réussis.
  List<String> drawSeries(List<Map<String, dynamic>> pPuzzles, int pLevel,
      Map<String, dynamic> pStats, Random pRandom) {
    int rank(Map<String, dynamic> pPuzzle) {
      final vStat = pStats[pPuzzle['id']] as Map?;

      return vStat == null ? 0 : (vStat['last'] == true ? 2 : 1);
    }

    final vLevels = {
      for (final vPuzzle in pPuzzles) vPuzzle['id'] as String: vPuzzle['level'] as int
    };
    final vChosen = <String>[];

    for (final (vOffset, vCount) in plan) {
      final vLevel = min(max(pLevel + vOffset, _lowest), _highest);
      final vPool = [
        for (final vPuzzle in pPuzzles)
          if (vPuzzle['level'] == vLevel && !vChosen.contains(vPuzzle['id'])) vPuzzle,
      ]..shuffle(pRandom);

      vChosen
          .addAll(_stableSort(vPool, rank).take(vCount).map((pPuzzle) => pPuzzle['id'] as String));
    }

    final vRest = [
      for (final vId in vLevels.keys)
        if (!vChosen.contains(vId)) vId,
    ]..shuffle(pRandom);

    vChosen.addAll(_stableSort(vRest, (String pId) => (vLevels[pId]! - pLevel).abs())
        .take(seriesLength - vChosen.length));

    return _stableSort(vChosen, (String pId) => vLevels[pId]!);
  }

  static List<T> _stableSort<T>(List<T> pItems, int Function(T) pKey) {
    final vIndexed = [
      for (var vIndex = 0; vIndex < pItems.length; vIndex++) (vIndex, pItems[vIndex])
    ]..sort((pA, pB) {
        final vOrder = pKey(pA.$2).compareTo(pKey(pB.$2));

        return vOrder != 0 ? vOrder : pA.$1.compareTo(pB.$1);
      });

    return [for (final (_, vItem) in vIndexed) vItem];
  }
}
