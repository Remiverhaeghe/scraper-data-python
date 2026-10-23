// Simulation d'entretien, auto-évaluation et fiche d'offre hors ligne.

import 'dart:convert';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/screens/interview_screen.dart';
import 'package:jobboard_revision/screens/offer_detail_screen.dart';
import 'package:jobboard_revision/screens/offers_screen.dart';
import 'package:jobboard_revision/screens/skills_screen.dart';
import 'package:jobboard_revision/services/api_client.dart';
import 'package:jobboard_revision/services/revision_store.dart';

import 'support/sample_data.dart';

final interviewContent = {
  'themes': ['Tous les thèmes', 'Java'],
  'questions': [
    for (var vIndex = 1; vIndex <= 6; vIndex++)
      {
        'id': 'sim-$vIndex',
        'theme': 'Java',
        'question': 'Question $vIndex ?',
        'answer': 'Réponse $vIndex',
        'points': ['Point A', 'Point B'],
      },
  ],
};

/// Réponse JSON en UTF-8, comme celle du vrai serveur (http.Response seul code en latin-1).
http.Response jsonResponse(Object pBody) => http.Response.bytes(
      utf8.encode(jsonEncode(pBody)),
      200,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

/// Serveur simulé : note les envois et répond aux routes de simulation et de grille.
MockClient buildServer(Map<String, List<Object?>> pSent, {bool pOldServer = false}) {
  final rClient = MockClient((pRequest) async {
    final vPath = pRequest.url.path;
    final http.Response rResponse;

    if (pOldServer && (vPath.endsWith('/interview') || vPath.endsWith('/skills'))) {
      rResponse = http.Response('', 404);
    } else if (pRequest.method == 'POST' &&
        (vPath.endsWith('/interview') || vPath.endsWith('/skills'))) {
      pSent.putIfAbsent(vPath.split('/').last, () => []).add(jsonDecode(pRequest.body));
      rResponse = http.Response('{}', 200);
    } else if (vPath.endsWith('/interview')) {
      rResponse = jsonResponse(interviewContent);
    } else if (vPath.endsWith('/skills')) {
      rResponse = http.Response(
        jsonEncode({
          'grid': [
            {'skill': 'Java', 'level': 6},
            {'skill': 'Linux', 'level': 0},
          ],
        }),
        200,
      );
    } else if (vPath.endsWith('/progress')) {
      rResponse = http.Response(jsonEncode(buildProgressJson()), 200);
    } else if (vPath.endsWith('/offers')) {
      rResponse = http.Response(jsonEncode({'offers': []}), 200);
    } else {
      rResponse = http.Response('', 304);
    }

    return rResponse;
  });

  return rClient;
}

Future<RevisionState> buildState(MockClient pServer) async {
  final rState = RevisionState(
    MemoryRevisionStore()
      ..settings = const ServerSettings(address: 'http://pc/api/v1', token: 'secret')
      ..package = jsonEncode(buildPackageJson())
      ..progress = buildProgressJson(),
    pClientFactory: (pSettings) => ApiClient(pSettings, pClient: pServer),
  );

  await rState.load();

  return rState;
}

void main() {
  test('Questions, grille et envois échangés avec le PC', () async {
    final vSent = <String, List<Object?>>{};
    final vState = await buildState(buildServer(vSent));

    await vState.synchronize();

    expect(vState.interviewQuestions, hasLength(6));
    expect(vState.skillGrid.first, {'skill': 'Java', 'level': 6});

    await vState.recordInterviewSeries('Java', [
      {
        'question_id': 'sim-1',
        'checked': [0],
      },
    ]);
    await vState.saveSkillLevels({'Java': 8, 'Linux': 3});
    await vState.synchronize();

    expect((vSent['interview']!.single as Map)['series'], hasLength(1));
    expect((vSent['skills']!.single as Map)['levels'], {'Java': 8, 'Linux': 3});
    expect(vState.pendingInterview, isEmpty);
  });

  test("Un serveur sans simulation n'empêche pas la synchronisation", () async {
    final vState = await buildState(buildServer({}, pOldServer: true));

    await vState.synchronize();

    expect(vState.interviewQuestions, isEmpty);
  });

  testWidgets('Une série se joue jusqu\'au bilan et part en attente', (pTester) async {
    final vState = await buildState(buildServer({}));
    await pTester.runAsync(vState.synchronize);

    await pTester.pumpWidget(
      MaterialApp(home: InterviewScreen(state: vState, random: Random(1))),
    );
    await pTester.tap(find.text('Commencer'));
    await pTester.pump();

    for (var vIndex = 0; vIndex < simulationSize; vIndex++) {
      expect(find.textContaining('question ${vIndex + 1} sur 5'), findsOneWidget);

      await pTester.tap(find.text('Voir la réponse attendue'));
      await pTester.pump();

      // Première question ratée, les autres à moitié
      if (vIndex > 0) {
        await pTester.tap(find.text('Point A'));
        await pTester.pump();
      }

      await pTester.ensureVisible(find.text('Valider et continuer'));
      await pTester.tap(find.text('Valider et continuer'));
      await pTester.pumpAndSettle();
    }

    expect(find.text('Série terminée : 40 % des points clés cités.'), findsOneWidget);
    expect(vState.pendingInterview.single['results'], hasLength(5));
  });

  testWidgets('Les niveaux réglés sont enregistrés pour le PC', (pTester) async {
    final vState = await buildState(buildServer({}));
    await pTester.runAsync(vState.synchronize);

    await pTester.pumpWidget(MaterialApp(home: SkillsScreen(state: vState)));

    expect(find.text('6/10'), findsOneWidget);
    expect(find.text('—'), findsOneWidget);

    await pTester.tap(find.byTooltip('Enregistrer'));
    await pTester.pump();

    expect(vState.preferences[pendingSkillsPreference], {'Java': 6, 'Linux': 0});
  });

  testWidgets("La fiche d'une offre se lit hors ligne", (pTester) async {
    var vOpened = false;

    await pTester.pumpWidget(
      MaterialApp(
        home: OfferDetailScreen(
          offer: const {
            'title': 'Développeur Java',
            'company': 'Acme',
            'salary': '2 600 €',
            'covered': ['Java'],
            'missing': ['Kafka'],
            'description': 'Équipe de dix personnes.',
            'match_score': 50,
          },
          onOpen: () => vOpened = true,
        ),
      ),
    );

    expect(find.text('Acme · 2 600 €'), findsOneWidget);
    expect(find.text('Kafka'), findsOneWidget);
    expect(find.text('Équipe de dix personnes.'), findsOneWidget);

    await pTester.tap(find.text("Ouvrir l'annonce"));

    expect(vOpened, isTrue);
    expect(find.text('Voir sur la carte'), findsNothing);
  });

  test("La carte s'ouvre sur la position de l'offre", () {
    final vUri = buildMapUri(const {'latitude': 50.63, 'longitude': 3.06});

    expect(
        vUri.toString(), 'https://www.openstreetmap.org/?mlat=50.63&mlon=3.06#map=14/50.63/3.06');
    expect(buildMapUri(const {'latitude': null, 'longitude': 3.06}), isNull);
  });

  testWidgets('Le filtre Près de chez moi garde les offres du rayon', (pTester) async {
    final vState = await buildState(buildServer({}));
    vState.offers = [
      {'source': 'lever', 'source_id': '1', 'title': 'Développeur Lille', 'near': true},
      {'source': 'lever', 'source_id': '2', 'title': 'Développeur Lyon', 'near': false},
    ];

    await pTester.pumpWidget(MaterialApp(home: OffersScreen(state: vState)));

    expect(find.text('Développeur Lyon'), findsOneWidget);

    await pTester.tap(find.text('Près de chez moi'));
    await pTester.pump();

    expect(find.text('Développeur Lille'), findsOneWidget);
    expect(find.text('Développeur Lyon'), findsNothing);
  });
}
