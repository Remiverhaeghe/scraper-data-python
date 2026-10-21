// Statistiques de révision : réussite par thème et activité des derniers jours.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/logic/statistics.dart';
import 'package:jobboard_revision/models/quiz_package.dart';
import 'package:jobboard_revision/models/review_state.dart';
import 'package:jobboard_revision/screens/statistics_screen.dart';

import 'support/sample_data.dart';

void main() {
  final vToday = DateTime(2026, 10, 22);
  final vSchedule = {
    'docker-image': ReviewState(box: 2, due: DateTime(2026, 10, 25), lastCorrect: true),
    'ohm-courant': ReviewState(box: 1, due: DateTime(2026, 10, 22), lastCorrect: false),
  };

  test('Les thèmes les moins acquis viennent en premier', () {
    final vThemes = buildThemeStatistics(
      QuizPackage.fromJson(buildPackageJson()),
      vSchedule,
      vToday,
    );

    expect(vThemes.first.label, 'Électricité');
    expect(vThemes.first.acquired, 0);
    expect(vThemes.first.due, 1);
    expect(vThemes.last.label, 'Docker');
    expect(vThemes.last.share, 1);
  });

  test('L activité des jours est lue, même absente d un ancien serveur', () {
    final vDays = readDayActivity({
      'days': [
        {'date': '2026-10-21', 'answers': 4, 'correct': 3},
      ],
    });

    expect(vDays.single.answers, 4);
    expect(vDays.single.correct, 3);
    expect(readDayActivity({}), isEmpty);
  });

  testWidgets('Le graphique montre le nombre de réponses de chaque jour', (pTester) async {
    await pTester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ActivityChart(
            days: [
              DayActivity(date: DateTime(2026, 10, 21), answers: 4, correct: 3),
              DayActivity(date: DateTime(2026, 10, 22), answers: 0, correct: 0),
            ],
          ),
        ),
      ),
    );

    expect(find.text('4'), findsOneWidget);
    expect(find.text('21'), findsOneWidget);
    expect(find.text('22'), findsOneWidget);
  });
}
