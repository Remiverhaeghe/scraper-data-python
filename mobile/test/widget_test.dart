// Parcours à l'écran : thèmes de l'accueil, puis une question corrigée.

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/screens/home_screen.dart';
import 'package:jobboard_revision/services/revision_store.dart';

import 'support/sample_data.dart';

Future<RevisionState> buildState() async {
  final rState = RevisionState(
    MemoryRevisionStore()
      ..settings = const ServerSettings(address: 'http://pc/api/v1', token: 'secret')
      ..package = jsonEncode(buildPackageJson())
      ..progress = buildProgressJson(),
  );

  await rState.load();

  return rState;
}

void main() {
  testWidgets('Les thèmes sont rangés par domaine, avec leurs questions', (pTester) async {
    final vState = await buildState();

    await pTester.pumpWidget(MaterialApp(home: HomeScreen(state: vState)));

    expect(find.text('Informatique'), findsOneWidget);
    expect(find.text('Industrie'), findsOneWidget);
    expect(find.text('Docker'), findsOneWidget);
    expect(find.text('0 à revoir · 3 nouvelle(s) · 3 question(s)'), findsOneWidget);
  });

  testWidgets('Une question de QCM se corrige et se garde pour l envoi', (pTester) async {
    final vState = await buildState();

    await pTester.pumpWidget(MaterialApp(home: HomeScreen(state: vState)));
    await pTester.tap(find.text('Docker'));
    await pTester.pumpAndSettle();

    expect(find.text('Quelle différence entre une image et un conteneur ?'), findsOneWidget);

    await pTester.tap(find.text("L'image est le modèle"));
    await pTester.pump();
    await pTester.tap(find.text('Valider'));
    await pTester.pumpAndSettle();

    expect(find.text('Bonne réponse'), findsOneWidget);
    expect(vState.pending, hasLength(1));
  });
}
