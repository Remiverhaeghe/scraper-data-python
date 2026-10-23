// Signalements, examens envoyés au PC, objectif du jour et candidatures.

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jobboard_revision/logic/exam.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/services/api_client.dart';
import 'package:jobboard_revision/services/revision_store.dart';

import 'support/sample_data.dart';

/// Serveur simulé : note les envois ; pOldServer ignore les nouvelles routes.
MockClient buildServer(Map<String, List<Object?>> pSent, {bool pOldServer = false}) {
  final rClient = MockClient((pRequest) async {
    final vPath = pRequest.url.path;
    final http.Response rResponse;

    if (vPath.endsWith('/offers')) {
      rResponse = http.Response(
        jsonEncode({
          'offers': [
            {
              'source': 'lever',
              'source_id': '1',
              'title': 'Technicien de maintenance',
              'company': 'Acme',
              'status': null,
              'match_score': 80,
              'url': 'https://example.com/1',
            },
          ],
        }),
        200,
      );
    } else if (vPath.endsWith('/flags') ||
        vPath.endsWith('/exams') ||
        vPath.endsWith('/applications')) {
      pSent.putIfAbsent(vPath.split('/').last, () => []).add(jsonDecode(pRequest.body));
      rResponse = pOldServer ? http.Response('', 404) : http.Response('{}', 200);
    } else if (vPath.endsWith('/progress')) {
      rResponse = http.Response(
        jsonEncode({
          ...buildProgressJson(),
          'applications': [
            {
              'title': 'Technicien',
              'company': 'Acme',
              'status': 'Entretien',
              'themes': ['electricite'],
            },
          ],
        }),
        200,
      );
    } else {
      rResponse = http.Response('', 304);
    }

    return rResponse;
  });

  return rClient;
}

Future<RevisionState> buildState(MockClient pClient) async {
  final rState = RevisionState(
    MemoryRevisionStore()
      ..settings = const ServerSettings(address: 'http://pc/api/v1', token: 'secret')
      ..package = jsonEncode(buildPackageJson())
      ..progress = buildProgressJson(),
    pClientFactory: (pSettings) => ApiClient(pSettings, pClient: pClient),
  );

  await rState.load();

  return rState;
}

void main() {
  test('Une question signalée disparaît puis part au PC', () async {
    final vSent = <String, List<Object?>>{};
    final vState = await buildState(buildServer(vSent));

    await vState.flagQuestion('ohm-courant');

    expect(vState.package!.questions.any((vQuestion) => vQuestion.id == 'ohm-courant'), isFalse);

    await vState.recordExam(
      ExamResult(
        title: 'Examen',
        finishedAt: DateTime(2026, 10, 21, 18, 30),
        correct: 3,
        count: 4,
        seconds: 300,
      ),
    );
    await vState.synchronize();

    expect(vSent['flags'], [
      {
        'question_ids': ['ohm-courant'],
      },
    ]);
    expect(((vSent['exams']!.single as Map)['exams'] as List).single['correct'], 3);
    expect(vState.flaggedIds, isEmpty);
    expect(vState.applications.single['company'], 'Acme');
  });

  test('Un serveur plus ancien ne bloque pas la synchronisation', () async {
    final vSent = <String, List<Object?>>{};
    final vState = await buildState(buildServer(vSent, pOldServer: true));

    await vState.flagQuestion('ohm-courant');
    final vReport = await vState.synchronize();

    expect(vReport.sent, 0);
    // Gardé pour un prochain envoi, quand le PC sera à jour.
    expect(vState.flaggedIds, {'ohm-courant'});
  });

  test('Les réponses du jour comptent pour l objectif', () async {
    final vState = await buildState(buildServer({}));
    final vQuestion = vState.package!.questions.firstWhere((vItem) => vItem.type == 'qcm');

    expect(vState.answersToday, 0);
    expect(vState.dailyGoal, defaultDailyGoal);

    await vState.answer(vQuestion, 0);
    await vState.answer(vQuestion, 1);
    await vState.savePreference(dailyGoalPreference, 25);

    expect(vState.answersToday, 2);
    expect(vState.dailyGoal, 25);
    expect(vState.hapticsEnabled, isTrue);
  });

  test('Le statut d une offre s affiche tout de suite puis part au PC', () async {
    final vSent = <String, List<Object?>>{};
    final vState = await buildState(buildServer(vSent));

    await vState.synchronize();

    expect(vState.offers.single['title'], 'Technicien de maintenance');

    await vState.setOfferStatus(vState.offers.single, 'INTERESTED');
    await vState.setOfferStatus(vState.offers.single, 'APPLIED');

    expect(vState.offers.single['status'], 'APPLIED');
    // Seul le dernier statut est gardé pour l'envoi.
    expect(vState.pendingStatuses, [
      {'source': 'lever', 'source_id': '1', 'status': 'APPLIED'},
    ]);

    await vState.synchronize();

    expect(((vSent['applications']!.single as Map)['changes'] as List).single['status'], 'APPLIED');
    expect(vState.pendingStatuses, isEmpty);
  });
}
