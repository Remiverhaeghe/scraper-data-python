// Affichage des schémas : description visible et plein écran au toucher.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/widgets/question_parts.dart';

const wideSchema = '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="200" '
    'viewBox="0 0 900 200"><rect width="900" height="200" fill="#ffffff"/></svg>';

void main() {
  test('Un schéma large est reconnu à son viewBox', () {
    expect(isWideSchema(wideSchema), isTrue);
    expect(isWideSchema('<svg viewBox="0 0 400 400"></svg>'), isFalse);
    expect(isWideSchema('<svg></svg>'), isFalse);
  });

  testWidgets('Le schéma montre sa description et s ouvre en plein écran', (pTester) async {
    pTester.view.physicalSize = const Size(400, 800);
    pTester.view.devicePixelRatio = 1;
    addTearDown(pTester.view.reset);

    await pTester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SchemaView(content: wideSchema, description: 'Capteur, automate, vérin'),
        ),
      ),
    );

    expect(find.textContaining('Capteur, automate, vérin'), findsOneWidget);

    await pTester.tap(find.byType(SchemaView));
    await pTester.pumpAndSettle();

    expect(find.byType(SchemaScreen), findsOneWidget);
    expect(
      pTester.widget<RotatedBox>(find.byType(RotatedBox)).quarterTurns,
      1,
    );

    await pTester.tap(find.byTooltip('Tourner le schéma'));
    await pTester.pump();

    expect(pTester.widget<RotatedBox>(find.byType(RotatedBox)).quarterTurns, 0);
  });
}
