// Candidatures et fiches d'entretien reçues du PC, lisibles hors ligne.

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/screens/tracking_screen.dart';
import 'package:jobboard_revision/services/api_client.dart';
import 'package:jobboard_revision/services/revision_store.dart';

import 'support/fake_reminders.dart';
import 'support/sample_data.dart';

void main() {
  test('Les candidatures et la fiche du prochain entretien sont gardées', () async {
    final vInterviewAt = DateTime.now().add(const Duration(hours: 5));
    final vTracking = {
      'applications': [
        {
          'source': 'lever',
          'source_id': '1',
          'title': 'Dev',
          'company': 'Acme',
          'status_label': 'Entretien',
          'interview_at': vInterviewAt.toIso8601String().substring(0, 16),
        },
        {
          'source': 'lever',
          'source_id': '2',
          'title': 'Data',
          'status_label': 'Postulé',
          'follow_up_date': '2026-11-03T00:00:00',
        },
      ],
      'sheets': {
        'lever/1': {
          'title': 'Dev',
          'header': ['Acme'],
          'sections': [
            [
              'Mon pitch',
              ['30 secondes : Bonjour'],
            ],
          ],
        },
      },
    };
    final vServer = MockClient((pRequest) async {
      final vPath = pRequest.url.path;

      if (vPath.endsWith('/tracking')) {
        // Accents compris : le serveur répond en UTF-8.
        return http.Response.bytes(utf8.encode(jsonEncode(vTracking)), 200);
      }

      if (vPath.endsWith('/offers') || vPath.endsWith('/withdrawn')) {
        return http.Response(jsonEncode({'offers': []}), 200);
      }

      if (vPath.endsWith('/replies') || vPath.endsWith('/interviews')) {
        return http.Response(jsonEncode({'replies': [], 'interviews': []}), 200);
      }

      if (vPath.endsWith('/progress')) {
        return http.Response(jsonEncode(buildProgressJson()), 200);
      }

      return http.Response('', 304);
    });
    final vState = RevisionState(
      MemoryRevisionStore()
        ..settings = const ServerSettings(address: 'http://pc/api/v1', token: 'secret')
        ..package = jsonEncode(buildPackageJson())
        ..progress = buildProgressJson(),
      pClientFactory: (pSettings) => ApiClient(pSettings, pClient: vServer),
      reminders: FakeReminders(),
    );

    await vState.load();
    await vState.synchronize();

    expect(vState.trackedApplications, hasLength(2));
    expect(vState.sheetOf(vState.trackedApplications[1]), isNull);
    expect(vState.nextInterview(DateTime.now())?['source_id'], '1');
    expect(vState.nextInterview(DateTime.now().add(const Duration(days: 2))), isNull);
    expect(describeTracking(vState.trackedApplications[1]), 'Postulé · relance le 03/11');
  });

  test('Une date se lit avec son heure quand elle en a une', () {
    expect(formatMoment('2026-10-27T14:30'), '27/10 à 14:30');
    expect(formatMoment('2026-10-27'), '27/10');
    expect(formatMoment(null), '');
  });
}
