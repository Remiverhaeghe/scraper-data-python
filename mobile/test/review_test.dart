// Répétition espacée hors ligne : mêmes boîtes et mêmes dates que le serveur.

import 'dart:math';

import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/logic/review.dart';
import 'package:jobboard_revision/models/quiz_package.dart';
import 'package:jobboard_revision/models/review_state.dart';

import 'support/sample_data.dart';

const intervals = [1, 3, 7, 21, 60];

void main() {
  test('Une réponse juste monte d une boîte, une fausse revient à la première', () {
    final vFirst = applyAnswer(null, true, DateTime(2026, 10, 19, 22, 30), intervals);
    final vSecond = applyAnswer(vFirst, true, DateTime(2026, 10, 20, 8), intervals);
    final vWrong = applyAnswer(vSecond, false, DateTime(2026, 10, 23, 8), intervals);

    expect((vFirst.box, vFirst.due), (1, DateTime(2026, 10, 20)));
    expect((vSecond.box, vSecond.due), (2, DateTime(2026, 10, 23)));
    expect((vWrong.box, vWrong.due), (1, DateTime(2026, 10, 24)));
  });

  test('Les questions à revoir passent avant les nouvelles', () {
    final vQuestions = QuizPackage.fromJson(buildPackageJson()).questionsOf('electricite');
    final vToday = DateTime(2026, 10, 19);
    final vSchedule = {
      'ohm-courant': ReviewState(box: 1, due: DateTime(2026, 10, 19)),
      'consignation': ReviewState(box: 2, due: DateTime(2026, 10, 25)),
    };

    expect(pickQuestion(vQuestions, vSchedule, vToday, Random(1))!.id, 'ohm-courant');
    expect(countDue(vQuestions, vSchedule, vToday), 1);
    expect(countNew(vQuestions, vSchedule), 1);
    expect(nextReview(vQuestions, vSchedule), DateTime(2026, 10, 19));

    vSchedule['ohm-courant'] = ReviewState(box: 2, due: DateTime(2026, 10, 22));

    expect(pickQuestion(vQuestions, vSchedule, vToday, Random(1))!.id, 'unites');

    vSchedule['unites'] = ReviewState(box: 1, due: DateTime(2026, 10, 20));

    expect(pickQuestion(vQuestions, vSchedule, vToday, Random(1)), isNull);
  });

  test('Une remise en ordre ne commence jamais déjà dans l ordre', () {
    for (var vSeed = 0; vSeed < 50; vSeed++) {
      final vIndexes = shuffledIndexes(2, Random(vSeed), pAvoidIdentity: true);

      expect(vIndexes, [1, 0]);
    }
  });
}
