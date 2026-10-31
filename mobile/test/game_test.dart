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

import 'support/fake_reminders.dart';
import 'support/sample_data.dart';

const settings = ServerSettings(address: 'http://pc/api/v1', token: 'secret');

Future<RevisionState> buildState({FakeReminders? pReminders}) async {
  final rState = RevisionState(
    MemoryRevisionStore()
      ..settings = settings
      ..package = jsonEncode(buildPackageJson())
      ..progress = buildProgressJson(),
    pClientFactory: (pSettings) => ApiClient(
      pSettings,
      pClient: MockClient((_) async => http.Response('', 503)),
    ),
    reminders: pReminders,
  );

  await rState.load();

  return rState;
}

ApiClient serveGame(int pLevel, {Map<String, dynamic>? pSeason}) {
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
            'cosmetics': {'frame': 'bronze', 'frame_color': '#B45309', 'frame_width': 3},
            if (pSeason != null) 'season': pSeason,
            'mascot': {
              'mood': 'focused',
              'text': "Plus que 6 pour « Réviser 10 questions ». On s'y met ?",
              'svg': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">'
                  '<rect width="120" height="120" fill="#f59e0b"/></svg>',
            },
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
    expect(find.textContaining('Plus que 6 pour'), findsOneWidget);
    expect(GameCard.frameBorder({'frame_color': '#B45309', 'frame_width': 3})?.top.width, 3);
    expect(GameCard.frameBorder({'frame_width': 0}), isNull);
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

  testWidgets('Le bilan de la semaine est affiché et annoncé une fois par saison', (pTester) async {
    final vReminders = FakeReminders();
    final vState = await buildState(pReminders: vReminders);
    const vSeason = {
      'key': '2026-W44',
      'title': 'Saison 44',
      'summary': '310 XP, +210 par rapport à la semaine précédente',
      'medal': {'label': "Médaille d'or : 17 quêtes sur 22", 'color': '#EAB308'},
    };

    await vState.savePreference(reminderPreference, true);
    await vState.exchangeGame(serveGame(3, pSeason: vSeason));
    await vState.exchangeGame(serveGame(3, pSeason: vSeason));
    await vState.exchangeGame(serveGame(3, pSeason: {...vSeason, 'key': '2026-W45'}));

    expect([for (final vItem in vReminders.shownSeasons) vItem['key']], ['2026-W44', '2026-W45']);

    await pTester.pumpWidget(MaterialApp(home: Scaffold(body: GameCard(state: vState))));

    expect(find.text('Bilan de la Saison 44'), findsOneWidget);
    expect(find.textContaining("Médaille d'or"), findsOneWidget);
    expect(GameCard.parseColor('#EAB308'), const Color(0xFFEAB308));
    expect(GameCard.parseColor('rouge'), isNull);
  });

  test('Sans rappels actifs, le bilan est noté sans notification', () async {
    final vReminders = FakeReminders();
    final vState = await buildState(pReminders: vReminders);

    await vState.exchangeGame(serveGame(3, pSeason: {'key': '2026-W44', 'title': 'Saison 44'}));

    expect(vReminders.shownSeasons, isEmpty);
    expect(vState.preferences[notifiedSeasonPreference], '2026-W44');
  });
}
