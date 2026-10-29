// Examen blanc, synchronisation automatique et rappel quotidien.

import 'dart:convert';
import 'dart:math';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jobboard_revision/logic/exam.dart';
import 'package:jobboard_revision/models/quiz_package.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/services/api_client.dart';
import 'package:jobboard_revision/services/discovery.dart';
import 'package:jobboard_revision/services/reminders.dart';
import 'package:jobboard_revision/services/revision_store.dart';

import 'support/fake_reminders.dart';
import 'support/sample_data.dart';

Future<RevisionState> buildState(
  http.Client pClient, {
  Reminders? pReminders,
}) async {
  final rState = RevisionState(
    MemoryRevisionStore()
      ..settings = const ServerSettings(address: 'http://pc/api/v1', token: 'secret')
      ..package = jsonEncode(buildPackageJson())
      ..progress = buildProgressJson(),
    pClientFactory: (pSettings) => ApiClient(pSettings, pClient: pClient),
    pRandom: Random(3),
    reminders: pReminders,
    // Aucun réseau local parcouru : le test ne dépend pas du Wi-Fi de la machine.
    pDiscovery: ServerDiscovery(pClient: pClient, pFindPrefixes: () async => []),
  );

  await rState.load();

  return rState;
}

void main() {
  test('Examen : tirage sans doublon, note et minuteur', () {
    final vQuestions = QuizPackage.fromJson(buildPackageJson()).questions;
    final vExam = drawExam(vQuestions, Random(1), pCount: 3);
    final vResult = ExamResult(
      title: 'Examen',
      finishedAt: DateTime(2026, 10, 19, 10),
      correct: 3,
      count: 4,
      seconds: 300,
    );

    expect(vExam.map((vQuestion) => vQuestion.id).toSet(), hasLength(3));
    expect(drawExam(vQuestions, Random(1)), hasLength(vQuestions.length));
    expect((vResult.score, vResult.overtime), (75, true));
    expect(ExamResult.fromJson(vResult.toJson()).score, 75);
    expect(formatCountdown(65), 'Temps restant : 01:05');
    expect(formatCountdown(-5), 'Temps dépassé de 00:05');
  });

  test('Sans réseau, la synchronisation automatique ne dérange pas', () async {
    final vState = await buildState(
      MockClient((_) async => throw http.ClientException('pas de réseau')),
    );

    expect(await vState.synchronizeQuietly(), isNull);
    expect(vState.syncing, isFalse);
  });

  test('Les réponses partent seules toutes les dix', () async {
    var vUploads = 0;
    final vState = await buildState(
      MockClient((pRequest) async {
        final http.Response rResponse;

        if (pRequest.url.path.endsWith('/answers')) {
          vUploads++;
          rResponse = http.Response(
            jsonEncode({'rejected': [], 'progress': buildProgressJson()}),
            200,
          );
        } else if (pRequest.url.path.endsWith('/progress')) {
          rResponse = http.Response(jsonEncode(buildProgressJson()), 200);
        } else {
          rResponse = http.Response('', 304);
        }

        return rResponse;
      }),
    );
    final vQuestion = vState.package!.questions.first;

    for (var vIndex = 0; vIndex < autoSyncEvery; vIndex++) {
      await vState.answer(vQuestion, 1);
    }

    await pumpEventQueue();

    expect(vUploads, 1);
    expect(vState.pending, isEmpty);
  });

  test('Examen terminé gardé, le plus récent en tête', () async {
    final vState = await buildState(MockClient((_) async => http.Response('', 500)));

    for (final vCorrect in [1, 2]) {
      await vState.recordExam(
        ExamResult(
          title: 'Examen',
          finishedAt: DateTime(2026, 10, 19),
          correct: vCorrect,
          count: 2,
          seconds: 60,
        ),
      );
    }

    expect(vState.examResults.map((vResult) => vResult.score), [100, 50]);
    expect((vState.store as MemoryRevisionStore).examResults, hasLength(2));
  });

  test('Rappel planifié avec les questions à revoir, puis annulé', () async {
    final vReminders = FakeReminders();
    final vState = await buildState(
      MockClient((_) async => http.Response('', 500)),
      pReminders: vReminders,
    );

    expect(await vState.setReminder(true), isTrue);
    expect(vReminders.scheduled.last, 0);
    expect(vState.reminderEnabled, isTrue);

    await vState.setReminder(false);

    expect(vReminders.cancelled, greaterThan(0));
    expect(vState.reminderEnabled, isFalse);
  });

  test('Apparence et taille du texte gardées, valeur inconnue ignorée', () async {
    final vState = await buildState(MockClient((_) async => http.Response('', 500)));

    expect(vState.appearance, 'system');
    expect(vState.textScale, 1.0);

    await vState.setDisplay(pAppearance: 'dark', pTextScale: 1.3);

    expect(vState.appearance, 'dark');
    expect(vState.textScale, 1.3);
    expect((vState.store as MemoryRevisionStore).preferences[appearancePreference], 'dark');

    vState.preferences = {appearancePreference: 'violet', textScalePreference: 9};

    expect(vState.appearance, 'system');
    expect(vState.textScale, 1.0);
  });

  test('Notifications refusées : le rappel reste coupé', () async {
    final vState = await buildState(
      MockClient((_) async => http.Response('', 500)),
      pReminders: FakeReminders(granted: false),
    );

    expect(await vState.setReminder(true), isFalse);
    expect(vState.reminderEnabled, isFalse);
  });
}
