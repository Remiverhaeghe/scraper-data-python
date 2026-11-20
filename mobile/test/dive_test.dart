// Univers de la piscine : profondeur d'un thème, bilan d'un plongeon et carnet de la semaine.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/logic/dive.dart';
import 'package:jobboard_revision/models/quiz_package.dart';
import 'package:jobboard_revision/models/review_state.dart';
import 'package:jobboard_revision/screens/dive_log_screen.dart';
import 'package:jobboard_revision/screens/dive_result_screen.dart';
import 'package:jobboard_revision/screens/home_screen.dart';

import 'support/sample_data.dart';
import 'widget_test.dart' show buildState;

void main() {
  test('La profondeur suit la boîte moyenne des questions, jusqu à 3 m', () {
    final vQuestions = QuizPackage.fromJson(buildPackageJson()).questionsOf('electricite');
    final vDue = DateTime(2026, 11, 20);

    expect(themeDepth(vQuestions, const {}), 0);
    expect(themeDepth(const [], const {}), 0);
    expect(
      themeDepth(vQuestions, {for (final vQuestion in vQuestions) vQuestion.id: ReviewState(box: 5, due: vDue)}),
      poolDepthMetres,
    );
    expect(
      themeDepth(vQuestions, {vQuestions.first.id: ReviewState(box: 9, due: vDue)}),
      closeTo(poolDepthMetres / vQuestions.length, 1e-9),
    );
    expect(formatDepth(1.25), '1,3 m');
  });

  test('Le bilan dit si le thème est descendu, resté ou remonté', () {
    expect(diveVerdict((answered: 4, correct: 4, before: 0.4, after: 1.0)), DiveVerdict.deeper);
    expect(diveVerdict((answered: 4, correct: 2, before: 1.0, after: 1.02)), DiveVerdict.steady);
    expect(diveVerdict((answered: 4, correct: 0, before: 1.0, after: 0.4)), DiveVerdict.shallower);
    expect(diveVerdict((answered: 0, correct: 0, before: 1.0, after: 1.0)), DiveVerdict.dry);
    expect(diveAccuracy((answered: 4, correct: 3, before: 0, after: 0)), 0.75);
    expect(diveAccuracy((answered: 0, correct: 0, before: 0, after: 0)), 0);
  });

  test('Le carnet compte la semaine du lundi au dimanche et garde huit semaines', () {
    var vLog = <String, List<int>>{'2026-09-01': [5, 5]};
    vLog = logAnswer(vLog, DateTime(2026, 11, 16, 9), true);
    vLog = logAnswer(vLog, DateTime(2026, 11, 16, 21), false);
    vLog = logAnswer(vLog, DateTime(2026, 11, 18, 8), true);
    vLog = logAnswer(vLog, DateTime(2026, 11, 12, 8), true);

    expect(vLog.containsKey('2026-09-01'), isFalse);
    final vWeek = diveWeek(vLog, DateTime(2026, 11, 20));
    expect(vWeek.days.first.day, DateTime(2026, 11, 16));
    expect(vWeek.days.last.day, DateTime(2026, 11, 22));
    expect((vWeek.answered, vWeek.correct, vWeek.activeDays), (3, 2, 2));
    expect(vWeek.bestDay!.day, DateTime(2026, 11, 16));
    expect(vWeek.previousAnswered, 1);
    expect(diveBars(vWeek).take(3), [1.0, 0.0, 0.5]);
    expect(diveBars(diveWeek(const {}, DateTime(2026, 11, 20))), everyElement(0));
    expect(diveWeek(const {}, DateTime(2026, 11, 20)).bestDay, isNull);
  });

  testWidgets('Une réponse remplit le carnet ; sortir de l eau ouvre le bilan', (pTester) async {
    final vState = await buildState();

    await pTester.pumpWidget(MaterialApp(home: HomeScreen(state: vState)));
    await pTester.scrollUntilVisible(find.text('Docker'), 200);
    await pTester.pumpAndSettle();
    await pTester.tap(find.text('Docker'));
    await pTester.pumpAndSettle();
    await pTester.tap(find.text("L'image est le modèle"));
    await pTester.pump();
    await pTester.tap(find.text('Valider'));
    await pTester.pumpAndSettle();

    final vToday = DateTime.now();
    expect(diveWeek(vState.diveLog, vToday).answered, 1);

    await pTester.scrollUntilVisible(find.text("Sortir de l'eau"), 200);
    await pTester.tap(find.text("Sortir de l'eau"));
    await pTester.pumpAndSettle();
    expect(find.byType(DiveResultScreen), findsOneWidget);
    expect(find.text('Beau plongeon !'), findsOneWidget);
    expect(find.text('1 réponse, 1 juste(s) : 100 %'), findsOneWidget);
    expect(find.textContaining('Profondeur du thème : '), findsOneWidget);
  });

  testWidgets('Le carnet montre la semaine et la précédente', (pTester) async {
    final vState = await buildState();
    await vState.recordDive(true, pAt: DateTime(2026, 11, 17, 9));
    await vState.recordDive(false, pAt: DateTime(2026, 11, 17, 10));
    await vState.recordDive(true, pAt: DateTime(2026, 11, 10, 9));

    await pTester.pumpWidget(
      MaterialApp(home: DiveLogScreen(state: vState, today: DateTime(2026, 11, 20))),
    );
    await pTester.pumpAndSettle();

    expect(find.text('2 réponses cette semaine'), findsOneWidget);
    expect(find.text("1 juste(s), 1 jour(s) dans l'eau, 50 % de réussite"), findsOneWidget);
    expect(find.text('Meilleur jour : Mar, 2 réponse(s)'), findsOneWidget);
    expect(find.text('Semaine dernière : 1 réponse(s)'), findsOneWidget);
  });
}
