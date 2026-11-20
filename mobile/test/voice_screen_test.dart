// Révision à la voix : question lue, réponse dite, correction lue.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/screens/voice_screen.dart';
import 'package:jobboard_revision/services/speech.dart';

import 'widget_test.dart' show buildState;

/// Voix simulée : garde ce qui est lu et répond par les phrases prévues, une par écoute.
class ScriptedSpeech extends Speech {
  ScriptedSpeech(this.answers);

  final List<List<String>> answers;
  final said = <String>[];

  @override
  Future<bool> speak(String pText) async {
    said.add(pText);

    return true;
  }

  @override
  Future<List<String>> listen() async => answers.isEmpty ? const [] : answers.removeAt(0);

  @override
  Future<void> stop() async {}
}

void main() {
  testWidgets('Une réponse dite est corrigée et lue, une phrase sans choix est redemandée', (
    pTester,
  ) async {
    final vState = await buildState();
    final vSpeech = ScriptedSpeech([
      ['il fait beau'],
      ["l'image est le modèle"],
    ]);

    await pTester.pumpWidget(MaterialApp(home: VoiceScreen(state: vState, speech: vSpeech)));
    await pTester.pumpAndSettle();

    expect(vSpeech.said.single, contains('Réponse A : '));
    final vAsked = vSpeech.said.single;

    await pTester.tap(find.text('Répondre à voix haute'));
    await pTester.pumpAndSettle();
    expect(find.text('Compris « il fait beau », sans y trouver de choix.'), findsOneWidget);
    expect(vSpeech.said.last, "Je n'ai pas compris. Dites la lettre de votre réponse.");
    expect(vState.pending, isEmpty);

    await pTester.tap(find.text('Répondre à voix haute'));
    await pTester.pumpAndSettle();
    if (vAsked.contains("L'image est le modèle")) {
      expect(vState.pending, hasLength(1));
      expect(find.text('Question suivante'), findsOneWidget);
      expect(
          find.text('1 réponse, ' '${vState.pending.single['correct'] == true ? 1 : 0} juste(s)'),
          findsOneWidget);
    }
  });

  testWidgets('Un choix se touche aussi, sans parler', (pTester) async {
    final vState = await buildState();
    final vSpeech = ScriptedSpeech([]);

    await pTester.pumpWidget(MaterialApp(home: VoiceScreen(state: vState, speech: vSpeech)));
    await pTester.pumpAndSettle();
    await pTester.tap(find.text('A'));
    await pTester.pumpAndSettle();

    expect(vState.pending, hasLength(1));
    expect(find.text('Réponse A.'), findsOneWidget);
    expect(vSpeech.said.last, anyOf('Bonne réponse.', startsWith('Raté. La bonne réponse était ')));
  });
}
