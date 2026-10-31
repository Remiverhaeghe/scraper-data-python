// Progression reçue du PC, fête de niveau et jeu « Contre la montre ».

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jobboard_revision/logic/time_attack.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/screens/time_attack_screen.dart';
import 'package:jobboard_revision/services/api_client.dart';
import 'package:jobboard_revision/services/revision_store.dart';
import 'package:jobboard_revision/widgets/celebration.dart';
import 'package:jobboard_revision/widgets/game_card.dart';

import 'support/sample_data.dart';

const settings = ServerSettings(address: 'http://pc/api/v1', token: 'secret');

Future<RevisionState> buildState() async {
  final rState = RevisionState(
    MemoryRevisionStore()
      ..settings = settings
      ..package = jsonEncode(buildPackageJson())
      ..progress = buildProgressJson(),
    pClientFactory: (pSettings) => ApiClient(
      pSettings,
      pClient: MockClient((_) async => http.Response('', 503)),
    ),
  );

  await rState.load();

  return rState;
}

ApiClient serveGame(int pLevel) {
  final rClient = ApiClient(
    settings,
    pClient: MockClient(
      (_) async => http.Response.bytes(
        utf8.encode(
          jsonEncode({
            'level': pLevel,
            'title': 'Technicien',
            'next_title': 'Technicien confirmé',
            'xp_in_level': 50,
            'xp_for_level': 300,
            'streak': 2,
            'quests': [
              {
                'label': 'Réviser 10 questions',
                'progress': 4,
                'target': 10,
                'done': false,
                'xp': 20
              },
            ],
            'achievements': [
              {'title': 'Premier pas', 'unlocked': true, 'unlocked_on': '2026-10-30'},
              {'title': 'Lancé', 'unlocked': false, 'unlocked_on': null},
            ],
          }),
        ),
        200,
      ),
    ),
  );

  return rClient;
}

void main() {
  test('Le multiplicateur grandit avec la série et retombe sur une erreur', () {
    final vScore = TimeAttackScore();

    for (var vIndex = 0; vIndex < 4; vIndex++) {
      vScore.record(true);
    }

    expect((vScore.points, vScore.multiplier, vScore.bestCombo), (50, 2, 4));
    expect(vScore.record(false), 0);
    expect((vScore.combo, vScore.multiplier, vScore.bestCombo), (0, 1, 4));
    expect(multiplierOf(100), timeAttackMaxMultiplier);
    expect(describeTimeAttack(vScore, 0, true), contains('Nouveau record'));
  });

  test('La première progression sert de référence, un niveau gagné se fête une fois', () async {
    final vState = await buildState();

    await vState.exchangeGame(serveGame(2));

    expect(vState.game?['title'], 'Technicien');
    expect(vState.levelToCelebrate, isNull);

    await vState.exchangeGame(serveGame(3));

    expect(vState.levelToCelebrate, 3);

    await vState.markLevelCelebrated();

    expect(vState.levelToCelebrate, isNull);
  });

  test('Seul un meilleur score devient le record', () async {
    final vState = await buildState();

    expect(await vState.recordTimeAttack(50), isTrue);
    expect(await vState.recordTimeAttack(30), isFalse);
    expect(vState.timeAttackBest, 50);
  });

  testWidgets('La carte affiche niveau, quêtes et trophées obtenus', (pTester) async {
    final vState = await buildState();
    await vState.exchangeGame(serveGame(3));

    await pTester.pumpWidget(MaterialApp(home: Scaffold(body: GameCard(state: vState))));

    expect(find.text('Technicien'), findsOneWidget);
    expect(find.text('Trophées : 1 / 2'), findsOneWidget);
    expect(find.text('Premier pas'), findsOneWidget);
  });

  testWidgets('Une partie : bonne réponse, fin du temps et record fêté', (pTester) async {
    final vState = await buildState();

    await pTester.pumpWidget(MaterialApp(home: TimeAttackScreen(state: vState)));
    await pTester.tap(find.text("L'image est le modèle"));
    await pTester.pump(const Duration(seconds: 1));

    expect(find.text('10 pts'), findsOneWidget);
    expect(vState.pending, hasLength(1));

    await pTester.pump(timeAttackDuration);
    await pTester.pump(const Duration(milliseconds: 400));

    expect(find.text('Temps écoulé'), findsOneWidget);
    expect(find.byType(CelebrationView), findsOneWidget);
    expect(vState.timeAttackBest, 10);

    await pTester.pump(celebrationDuration);
    await pTester.pumpAndSettle();

    expect(find.byType(CelebrationView), findsNothing);
  });
}
