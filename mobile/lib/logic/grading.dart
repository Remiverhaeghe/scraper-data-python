// Correction des réponses, identique à job/quiz_types.py : le téléphone corrige
// hors ligne, puis le serveur recalcule chaque correction à l'envoi.

import 'dart:math';

import '../models/quiz_package.dart';

/// Une réponse de calcul plus longue est une erreur de saisie.
const maxTextAnswerLength = 200;

/// Préfixes d'unité acceptés : « 2,3 mA » vaut 0,0023 si l'unité est A.
const unitPrefixes = {
  'p': 1e-12,
  'n': 1e-9,
  'µ': 1e-6,
  'u': 1e-6,
  'm': 1e-3,
  'k': 1e3,
  'M': 1e6,
  'G': 1e9,
};

final numberPattern = RegExp(r'^([-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?)\s*(\S*)$');

/// Réponse impossible à corriger : elle est reposée sans être comptée.
class UnreadableAnswer implements Exception {
  const UnreadableAnswer(this.message);

  final String message;

  @override
  String toString() => message;
}

/// Résultat d'une correction : juste ou non, réponse donnée et réponse attendue.
class Grade {
  const Grade({required this.correct, required this.given, required this.expected});

  final bool correct;
  final String given;
  final String expected;
}

/// Écrit un nombre à la française, sans zéros inutiles, comme le format %.6g.
String formatNumber(double pValue) {
  String vText;

  if (pValue == 0) {
    vText = '0';
  } else {
    final vExponent = (log(pValue.abs()) / ln10).floor();

    if (vExponent < -4 || vExponent >= 6) {
      final vParts = pValue.toStringAsExponential(5).split('e');
      final vMantissa =
          vParts[0].contains('.') ? vParts[0].replaceFirst(RegExp(r'\.?0+$'), '') : vParts[0];
      final vPower = int.parse(vParts[1]);

      vText = '${vMantissa}e${vPower < 0 ? '-' : '+'}'
          '${vPower.abs().toString().padLeft(2, '0')}';
    } else {
      vText = pValue.toStringAsPrecision(6);

      if (vText.contains('.')) {
        vText = vText.replaceFirst(RegExp(r'\.?0+$'), '');
      }
    }
  }

  final rText = vText.replaceAll('.', ',');

  return rText;
}

/// Lit une valeur saisie, avec ou sans unité ; lève UnreadableAnswer si illisible.
double parseNumber(String pText, String pUnit) {
  final vExample = 'par exemple 2,5 $pUnit'.trimRight();
  final vMatch = numberPattern.firstMatch(pText.trim());

  if (vMatch == null) {
    throw UnreadableAnswer('Nombre attendu, $vExample.');
  }

  final vValue = double.parse(vMatch.group(1)!.replaceAll(',', '.'));
  final vSuffix = vMatch.group(2)!;

  final double rValue;

  if (vSuffix.isEmpty || vSuffix == pUnit) {
    rValue = vValue;
  } else if (pUnit.isNotEmpty &&
      vSuffix.substring(1) == pUnit &&
      unitPrefixes.containsKey(vSuffix[0])) {
    rValue = vValue * unitPrefixes[vSuffix[0]]!;
  } else {
    throw UnreadableAnswer(
      pUnit.isNotEmpty ? 'Unité attendue : $pUnit, $vExample.' : 'Nombre sans unité attendu.',
    );
  }

  return rValue;
}

/// Vérifie une liste d'indices compris entre 0 et pCount - 1.
List<int> checkIndexes(Object? pResponse, int pCount) {
  if (pResponse is! List<int> ||
      pResponse.length != pCount ||
      pResponse.any((vIndex) => vIndex < 0 || vIndex >= pCount)) {
    throw const UnreadableAnswer('Réponse incomplète.');
  }

  final rIndexes = pResponse;

  return rIndexes;
}

Grade gradeChoice(QuizQuestion pQuestion, Object? pResponse) {
  final vChoices = pQuestion.choices;

  if (pResponse is! int || pResponse < 0 || pResponse >= vChoices.length) {
    throw const UnreadableAnswer('Choisissez une réponse.');
  }

  final rGrade = Grade(
    correct: pResponse == pQuestion.answer,
    given: vChoices[pResponse],
    expected: vChoices[pQuestion.answer],
  );

  return rGrade;
}

Grade gradeNumeric(QuizQuestion pQuestion, Object? pResponse) {
  if (pResponse is! String || pResponse.length > maxTextAnswerLength) {
    throw const UnreadableAnswer('Saisissez une valeur.');
  }

  final vExpected = pQuestion.value;
  final vValue = parseNumber(pResponse, pQuestion.unit);
  final vMargin = max(vExpected.abs() * pQuestion.tolerance / 100, 1e-12);

  final rGrade = Grade(
    correct: (vValue - vExpected).abs() <= vMargin,
    given: pResponse.trim(),
    expected: '${formatNumber(vExpected)} ${pQuestion.unit}'.trimRight(),
  );

  return rGrade;
}

Grade gradeOrder(QuizQuestion pQuestion, Object? pResponse) {
  final vItems = pQuestion.items;
  final vIndexes = checkIndexes(pResponse, vItems.length);

  if (vIndexes.toSet().length != vItems.length) {
    throw const UnreadableAnswer('Chaque élément doit avoir sa propre place.');
  }

  final rGrade = Grade(
    correct: List.generate(vItems.length, (vIndex) => vIndex).join(',') == vIndexes.join(','),
    given: vIndexes.map((vIndex) => vItems[vIndex]).join(' → '),
    expected: vItems.join(' → '),
  );

  return rGrade;
}

Grade gradePairs(QuizQuestion pQuestion, Object? pResponse) {
  final vPairs = pQuestion.pairs;
  final vIndexes = checkIndexes(pResponse, vPairs.length);

  final rGrade = Grade(
    correct: [
      for (var vIndex = 0; vIndex < vPairs.length; vIndex++) vIndexes[vIndex] == vIndex,
    ].every((vMatch) => vMatch),
    given: [
      for (var vIndex = 0; vIndex < vPairs.length; vIndex++)
        '${vPairs[vIndex][0]} → ${vPairs[vIndexes[vIndex]][1]}',
    ].join(' ; '),
    expected: vPairs.map((vPair) => '${vPair[0]} → ${vPair[1]}').join(' ; '),
  );

  return rGrade;
}

/// Revue de code : juste seulement si tous les défauts réels sont cochés, et eux seuls.
Grade gradeReview(QuizQuestion pQuestion, Object? pResponse) {
  final vChoices = pQuestion.choices;

  if (pResponse is! List<int> ||
      pResponse.isEmpty ||
      pResponse.any((vIndex) => vIndex < 0 || vIndex >= vChoices.length)) {
    throw const UnreadableAnswer('Cochez au moins un constat.');
  }

  final vGiven = pResponse.toSet().toList()..sort();
  final vExpected = [...pQuestion.answers]..sort();

  final rGrade = Grade(
    correct: vGiven.join(',') == vExpected.join(','),
    given: vGiven.map((vIndex) => vChoices[vIndex]).join(' ; '),
    expected: vExpected.map((vIndex) => vChoices[vIndex]).join(' ; '),
  );

  return rGrade;
}

/// Corrige une réponse selon le type de la question ; lève UnreadableAnswer si illisible.
Grade gradeAnswer(QuizQuestion pQuestion, Object? pResponse) {
  final Grade rGrade;

  switch (pQuestion.type) {
    case 'qcm':
      rGrade = gradeChoice(pQuestion, pResponse);
    case 'numerique':
      rGrade = gradeNumeric(pQuestion, pResponse);
    case 'ordre':
      rGrade = gradeOrder(pQuestion, pResponse);
    case 'association':
      rGrade = gradePairs(pQuestion, pResponse);
    case 'revue':
      rGrade = gradeReview(pQuestion, pResponse);
    default:
      throw const UnreadableAnswer('Type de question non pris en charge.');
  }

  return rGrade;
}
