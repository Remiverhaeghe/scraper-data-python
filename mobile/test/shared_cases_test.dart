// Cas communs au serveur et au téléphone (tests/fixtures/shared_quiz_cases.json) :
// la correction et la répétition espacée doivent donner les mêmes résultats
// qu'en Python, dans tests/job/test_shared_quiz_cases.py.

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/logic/grading.dart';
import 'package:jobboard_revision/logic/review.dart';
import 'package:jobboard_revision/models/quiz_package.dart';
import 'package:jobboard_revision/models/review_state.dart';

const intervals = [1, 3, 7, 21, 60];

/// Les listes lues en JSON deviennent des listes d'entiers, comme à l'écran.
Object? toResponse(Object? pValue) {
  final rResponse = pValue is List ? List<int>.from(pValue) : pValue;

  return rResponse;
}

void main() {
  // Les tests s'exécutent depuis mobile/ : le fichier est à la racine du dépôt.
  final vCases = jsonDecode(
    File('../tests/fixtures/shared_quiz_cases.json').readAsStringSync(),
  ) as Map<String, dynamic>;

  group('Correction', () {
    for (final vCase in vCases['grading'] as List) {
      test(vCase['name'] as String, () {
        final vQuestion = QuizQuestion(Map<String, dynamic>.from(vCase['question'] as Map));
        final vResponse = toResponse(vCase['response']);

        if (vCase['error'] == true) {
          expect(() => gradeAnswer(vQuestion, vResponse), throwsA(isA<UnreadableAnswer>()));
        } else {
          final vGrade = gradeAnswer(vQuestion, vResponse);

          expect((vGrade.correct, vGrade.expected), (vCase['correct'], vCase['expected']));
        }
      });
    }
  });

  group('Répétition espacée', () {
    for (final vCase in vCases['review'] as List) {
      test(vCase['name'] as String, () {
        ReviewState? vState;

        for (final vAnswer in vCase['answers'] as List) {
          vState = applyAnswer(
            vState,
            vAnswer[0] as bool,
            DateTime.parse(vAnswer[1] as String),
            intervals,
          );
        }

        expect(vState!.box, vCase['box']);
        expect(vState.due, DateTime.parse(vCase['due'] as String));
      });
    }
  });
}
