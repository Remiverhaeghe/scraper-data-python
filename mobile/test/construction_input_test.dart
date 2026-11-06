// Saisie d'un schéma à construire : palette, réponse remontée et schéma attendu
// affiché à la correction.

import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/logic/grading.dart';
import 'package:jobboard_revision/models/quiz_package.dart';
import 'package:jobboard_revision/widgets/question_input.dart';

// Grille du PC (job/schema_drawing.py), symboles réduits à un trait
const grid = {
  'columns': 4,
  'rows': 6,
  'cellWidth': 240,
  'cellHeight': 150,
  'margin': 36,
  'symbolOffset': 24,
  'corridorOffset': 8,
  'labelGap': 12,
  'labelLineHeight': 14,
  'labelWidth': 17,
  'wireExit': 14,
  'laneStep': 5,
  'laneCount': 4,
  'facingLimit': 80,
  'width': 80,
  'height': 100,
  'wireColor': '#2563eb',
};

Map<String, dynamic> symbol(String pLabel, List<List<Object>> pPorts, {bool pSymmetric = false}) =>
    {
      'label': pLabel,
      'lines': [pLabel],
      'drawing': '<line x1="40" y1="0" x2="40" y2="100" stroke="#0f172a"/>',
      'ports': pPorts,
      'symmetric': pSymmetric,
      'node': false,
    };

QuizQuestion buildQuestion() {
  final vPackage = QuizPackage.fromJson({
    'api_version': 1,
    'version': 'v1',
    'themes': [
      {'key': 'electricite', 'label': 'Électricité'},
    ],
    'interactive_questions': [
      {
        'id': 'c1',
        'theme': 'electricite',
        'type': 'construction',
        'question': 'Protégez le point lumineux par un fusible.',
        'components': [
          {'type': 'reseau', 'x': 0, 'y': 0},
          {'type': 'fusible', 'x': 0, 'y': 1},
          {'type': 'lampe', 'x': 0, 'y': 2},
        ],
        'connections': [
          ['reseau', 'sortie', 'fusible', '1'],
          ['fusible', '2', 'lampe', 'entrée'],
        ],
      },
    ],
    'schema_library': {
      'grid': grid,
      'limits': {'reseau': 1, 'fusible': 1, 'lampe': 1},
      'components': {
        'reseau': symbol('Réseau', [
          ['sortie', 40, 100],
        ]),
        'fusible': symbol(
          'Fusible',
          [
            ['1', 40, 0],
            ['2', 40, 100],
          ],
          pSymmetric: true,
        ),
        'lampe': symbol('Point lumineux', [
          ['entrée', 40, 0],
        ]),
      },
    },
  });

  final rQuestion = vPackage.questions.single;

  return rQuestion;
}

Widget wrap(QuizQuestion pQuestion, bool pEnabled, ValueChanged<Object?> pOnChanged) => MaterialApp(
      home: Scaffold(
        body: SingleChildScrollView(
          child: QuestionInput(
            question: pQuestion,
            random: Random(1),
            enabled: pEnabled,
            onChanged: pOnChanged,
          ),
        ),
      ),
    );

void main() {
  testWidgets('Les composants posés remontent un schéma corrigeable', (pTester) async {
    final vQuestion = buildQuestion();
    final vResponses = <Object?>[];

    await pTester.pumpWidget(wrap(vQuestion, true, vResponses.add));
    await pTester.tap(find.text('Fusible'));
    await pTester.tap(find.text('Point lumineux'));
    await pTester.pump();

    final vSchema = vResponses.last as Map<String, dynamic>;

    expect([for (final vItem in vSchema['components'] as List) (vItem as Map)['id']],
        ['fusible', 'lampe']);
    // Un exemplaire seulement : le bouton du fusible est désactivé.
    expect(
      pTester.widget<ActionChip>(find.widgetWithText(ActionChip, 'Fusible')).onPressed,
      isNull,
    );

    final vGrade = gradeAnswer(vQuestion, vSchema);

    expect(vGrade.correct, isFalse);
    expect(vGrade.given, startsWith('composants manquants : Réseau'));
    expect(vGrade.expected, 'Réseau – Fusible ; Fusible – Point lumineux');
  });

  testWidgets('Le schéma attendu s\'affiche une fois la réponse corrigée', (pTester) async {
    await pTester.pumpWidget(wrap(buildQuestion(), false, (_) {}));

    expect(find.text('Schéma attendu'), findsOneWidget);
    expect(
      pTester.widget<ActionChip>(find.widgetWithText(ActionChip, 'Réseau')).onPressed,
      isNull,
    );
  });
}
