// Niveaux de l'atelier Excel, hors ligne : vérification d'une formule identique
// à job/excel_levels.py, sur le contenu reçu du PC.

import 'excel_formula.dart';

const noReferenceMessage = "La formule doit s'appuyer sur les cellules de la feuille, pas sur des "
    'valeurs recopiées à la main.';
const circularMessage =
    'Référence circulaire : la formule dépend de la cellule où elle est écrite.';

/// Niveaux et règles de l'atelier, reçus du PC.
class ExcelLevels {
  ExcelLevels(Map<String, dynamic> pPackage)
      : rules = ExcelRules(Map<String, dynamic>.from(pPackage['rules'] as Map)),
        levels = {
          for (final vLevel in pPackage['levels'] as List)
            (vLevel as Map)['id'] as String: Map<String, dynamic>.from(vLevel),
        };

  final ExcelRules rules;
  final Map<String, Map<String, dynamic>> levels;

  /// Cellules à remplir : la plage de recopie, ou la seule cellule.
  List<(int, int)> targets(Map<String, dynamic> pLevel) {
    final vBounds = ((pLevel['fill'] ?? pLevel['cell']) as String).split(':');
    final (vTop, vLeft) = parseCell(vBounds.first);
    final (vBottom, vRight) = parseCell(vBounds.last);

    return [
      for (var vRow = vTop; vRow <= vBottom; vRow++)
        for (var vColumn = vLeft; vColumn <= vRight; vColumn++) (vRow, vColumn),
    ];
  }

  /// Formule recopiée dans chaque cellule cible, par adresse.
  Map<String, String> fillFormulas(Map<String, dynamic> pLevel, String pFormula) {
    final (vTop, vLeft) = parseCell(pLevel['cell'] as String);

    return {
      for (final (vRow, vColumn) in targets(pLevel))
        cellName(vRow, vColumn): shiftFormula(pFormula, vRow - vTop, vColumn - vLeft),
    };
  }

  /// Format d'affichage d'une colonne : date, euro, percent ou standard.
  String formatOf(Map<String, dynamic> pLevel, int pColumn) =>
      (pLevel['formats'] as Map?)?[columnLetters(pColumn)] as String? ?? '';

  /// Message qui refuse la formule, ou une chaîne vide.
  String checkFormula(Map<String, dynamic> pLevel, String pFormula) {
    final List<Object?> vTree;

    try {
      vTree = parseFormula(pFormula, rules);
    } on FormulaError catch (vError) {
      return vError.message;
    }

    final vFunctions = <String>{};

    if (collect(vTree, vFunctions) == 0) {
      return noReferenceMessage;
    }

    for (final vGroup in pLevel['requires'] as List? ?? const []) {
      final vNames = (vGroup as String).split('|');

      if (!vNames.any(vFunctions.contains)) {
        return vNames.length == 1
            ? 'Ce niveau attend la fonction ${vNames.first}.'
            : "Ce niveau attend l'une des fonctions ${vNames.join(', ')}.";
      }
    }

    return '';
  }

  /// Feuille du niveau, avec la formule recopiée si elle est fournie.
  Sheet buildSheet(Map<String, dynamic> pLevel, String pFormula) => Sheet(
        pLevel['rows'] as List,
        rules,
        pFormula.isEmpty ? null : fillFormulas(pLevel, pFormula),
      );

  /// Feuille en texte, ligne par ligne, avec ses formats.
  Map<String, dynamic> buildGrid(Map<String, dynamic> pLevel, Sheet pSheet) {
    final vTargets = targets(pLevel);
    final vLevelRows = pLevel['rows'] as List;
    var vRows = vLevelRows.length;
    var vColumns = 0;

    for (final vRow in vLevelRows) {
      vColumns = vColumns < (vRow as List).length ? vRow.length : vColumns;
    }

    for (final (vRow, vColumn) in vTargets) {
      vRows = vRows < vRow ? vRow : vRows;
      vColumns = vColumns < vColumn ? vColumn : vColumns;
    }

    return {
      'columns': [for (var vColumn = 1; vColumn <= vColumns; vColumn++) columnLetters(vColumn)],
      'rows': [
        for (var vRow = 1; vRow <= vRows; vRow++)
          [
            for (var vColumn = 1; vColumn <= vColumns; vColumn++)
              formatValue(pSheet.value(vRow, vColumn), vRow == 1 ? '' : formatOf(pLevel, vColumn)),
          ],
      ],
      'targets': [for (final (vRow, vColumn) in vTargets) cellName(vRow, vColumn)],
    };
  }

  /// Genre d'une valeur, pour un écart invisible à l'affichage.
  String describeType(Object? pValue) {
    if (pValue is ExcelError) {
      return 'une erreur';
    }

    if (pValue is bool) {
      return 'une valeur logique';
    }

    return pValue is double ? 'un nombre' : 'un texte';
  }

  /// Conseils des erreurs classiques reconnues dans la formule.
  List<String> findPitfalls(Map<String, dynamic> pLevel, String pFormula) => [
        for (final vPitfall in pLevel['pitfalls'] as List? ?? const [])
          if (RegExp((vPitfall as List)[0] as String, caseSensitive: false).hasMatch(pFormula))
            vPitfall[1] as String,
      ];

  /// Compare chaque cellule cible à l'attendu : (cellules, message).
  (List<Map<String, dynamic>>, String) compareCells(
      Map<String, dynamic> pLevel, Sheet pSheet, Sheet pExpected) {
    final vCells = <Map<String, dynamic>>[];
    final vWrong = <(Map<String, dynamic>, Object?, Object?)>[];

    for (final (vRow, vColumn) in targets(pLevel)) {
      final vValue = pSheet.value(vRow, vColumn);
      final vExpected = pExpected.value(vRow, vColumn);
      final vFormat = formatOf(pLevel, vColumn);
      final vCell = <String, dynamic>{
        'cell': cellName(vRow, vColumn),
        'value': formatValue(vValue, vFormat),
        'expected': formatValue(vExpected, vFormat),
        'ok': sameValue(vValue, vExpected),
      };
      vCells.add(vCell);

      if (vCell['ok'] != true) {
        vWrong.add((vCell, vValue, vExpected));
      }
    }

    if (vWrong.isEmpty) {
      return (vCells, '');
    }

    final (vCell, vValue, vExpected) = vWrong.first;
    final vGap = vCell['value'] == vCell['expected']
        ? '${vCell['cell']} : ${vCell['value']} obtenu (${describeType(vValue)}), '
            '${describeType(vExpected)} attendu.'
        : '${vCell['cell']} : ${vCell['value']} obtenu, ${vCell['expected']} attendu.';

    return (
      vCells,
      vWrong.length > 1
          ? "${vWrong.length} cellules sur ${vCells.length} diffèrent de l'attendu. $vGap"
          : vGap,
    );
  }

  /// Recopie la formule sur la plage du niveau et la compare à la solution.
  Map<String, dynamic> runLevel(Map<String, dynamic> pLevel, String pFormula) {
    final vFormula = pFormula.trim();
    var vMessage = checkFormula(pLevel, vFormula);
    var vCells = <Map<String, dynamic>>[];
    var vSheet = buildSheet(pLevel, '');

    if (vMessage.isEmpty) {
      vSheet = buildSheet(pLevel, vFormula);
      (vCells, vMessage) =
          compareCells(pLevel, vSheet, buildSheet(pLevel, pLevel['solution'] as String));

      if (vSheet.circular) {
        vMessage = circularMessage;
      }
    }

    final vPassed = vMessage.isEmpty;

    return {
      'passed': vPassed,
      'message': vMessage,
      'advice': vPassed ? <String>[] : findPitfalls(pLevel, vFormula),
      'cells': vCells,
      'grid': buildGrid(pLevel, vSheet),
    };
  }
}
