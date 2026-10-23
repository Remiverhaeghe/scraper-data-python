// Saisie d'une revue de code : cases cochées et réponse remontée.

import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/models/quiz_package.dart';
import 'package:jobboard_revision/widgets/question_input.dart';

void main() {
  testWidgets('Les constats cochés remontent leurs indices d\'origine', (pTester) async {
    final vResponses = <Object?>[];
    const vQuestion = QuizQuestion({
      'id': 'r1',
      'theme': 'java',
      'type': 'revue',
      'question': 'Défauts ?',
      'code': 'Session s = open();',
      'choices': ['Session jamais fermée', 'Nom trop court', 'Exception non traitée'],
      'answers': [0, 2],
    });

    await pTester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: QuestionInput(
            question: vQuestion,
            random: Random(1),
            enabled: true,
            onChanged: vResponses.add,
          ),
        ),
      ),
    );

    await pTester.tap(find.text('Session jamais fermée'));
    await pTester.tap(find.text('Exception non traitée'));
    await pTester.pump();

    expect((vResponses.last as List<int>)..sort(), [0, 2]);

    await pTester.tap(find.text('Session jamais fermée'));
    await pTester.tap(find.text('Exception non traitée'));
    await pTester.pump();

    expect(vResponses.last, isNull);
    expect(vQuestion.answers, [0, 2]);
  });
}
