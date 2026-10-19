// État de l'application : lecture du contenu, réponses hors ligne et
// synchronisation avec un serveur simulé.

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jobboard_revision/logic/grading.dart';
import 'package:jobboard_revision/models/quiz_package.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/services/api_client.dart';
import 'package:jobboard_revision/services/revision_store.dart';

import 'support/sample_data.dart';

const settings = ServerSettings(address: 'http://pc:8000/api/v1', token: 'secret');

void main() {
  test('Le contenu ignore les types de questions inconnus', () {
    final vPackage = QuizPackage.fromJson(buildPackageJson());

    expect(vPackage.questions.map((vQuestion) => vQuestion.id), isNot(contains('futur-type')));
    expect(vPackage.questionsOf('electricite'), hasLength(3));
    expect(vPackage.guides['docker.md']!.title, 'Guide Docker');
    expect(
      () => QuizPackage.fromJson({...buildPackageJson(), 'api_version': 2}),
      throwsFormatException,
    );
  });

  test('Adresse complétée avec le schéma et le préfixe de l API', () {
    expect(normalizeAddress('192.168.1.20:8000'), 'http://192.168.1.20:8000/api/v1');
    expect(normalizeAddress('https://pc/api/v1/'), 'https://pc/api/v1');
  });

  test('Réponse hors ligne gardée, puis envoyée sans la correction locale', () async {
    final vStore = MemoryRevisionStore()
      ..settings = settings
      ..package = jsonEncode(buildPackageJson())
      ..progress = buildProgressJson();
    final vRequests = <http.Request>[];
    final vClient = MockClient((pRequest) async {
      vRequests.add(pRequest);

      final http.Response rResponse;

      if (pRequest.url.path.endsWith('/answers')) {
        rResponse = http.Response(
          jsonEncode({
            'received': 1,
            'added': 1,
            'duplicates': 0,
            'rejected': [],
            'progress': buildProgressJson(),
          }),
          200,
        );
      } else if (pRequest.url.path.endsWith('/progress')) {
        rResponse = http.Response(
          jsonEncode(
            buildProgressJson(
              pQuestions: {
                'docker-image': {'last_correct': true, 'box': 1, 'due': '2026-10-20'},
              },
            ),
          ),
          200,
        );
      } else {
        rResponse = http.Response('', 304);
      }

      return rResponse;
    });
    final vState = RevisionState(
      vStore,
      pClientFactory: (pSettings) => ApiClient(pSettings, pClient: vClient),
    );

    await vState.load();

    final vQuestion = vState.package!.questions.first;
    final vGrade = await vState.answer(vQuestion, 1);

    expect(vGrade.correct, isTrue);
    expect(vStore.pending, hasLength(1));
    expect(vState.schedule['docker-image']!.box, 1);
    await expectLater(vState.answer(vQuestion, null), throwsA(isA<UnreadableAnswer>()));
    expect(vStore.pending, hasLength(1));

    final vReport = await vState.synchronize();
    final vSent = jsonDecode(vRequests.first.body)['answers'][0] as Map<String, dynamic>;

    expect(vReport.sent, 1);
    expect(vReport.contentUpdated, isFalse);
    expect(vStore.pending, isEmpty);
    expect(vSent['choice'], 1);
    expect(vSent.containsKey('correct'), isFalse);
    expect(vRequests.first.headers['Authorization'], 'Bearer secret');
    expect(vRequests.last.headers['If-None-Match'], '"v1"');
    expect(vState.schedule['docker-image']!.due, DateTime(2026, 10, 20));
  });

  test('Jeton refusé : message clair, réglages précédents conservés', () async {
    final vState = RevisionState(
      MemoryRevisionStore(),
      pClientFactory: (pSettings) => ApiClient(
        pSettings,
        pClient: MockClient((_) async => http.Response('', 401)),
      ),
    );

    await vState.load();

    await expectLater(
      vState.configure(settings),
      throwsA(
        isA<ApiException>().having(
          (vException) => vException.message,
          'message',
          contains('Jeton refusé'),
        ),
      ),
    );
    expect(vState.settings, isNull);
  });
}
