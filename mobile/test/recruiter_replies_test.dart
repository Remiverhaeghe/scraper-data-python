// Réponses de recruteurs repérées par le PC, signalées une fois sur le téléphone.

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/services/api_client.dart';
import 'package:jobboard_revision/services/reminders.dart';
import 'package:jobboard_revision/services/revision_store.dart';

import 'support/fake_reminders.dart';
import 'support/sample_data.dart';

Map<String, dynamic> buildReply(String pId, String pStatus) =>
    {'id': pId, 'title': 'Dev Java', 'company': 'Kiabi', 'status': pStatus};

/// Serveur simulé : renvoie à chaque synchronisation la liste de réponses suivante.
MockClient buildServer(List<List<Map<String, dynamic>>> pReplyLists) {
  var vCall = 0;

  final rClient = MockClient((pRequest) async {
    final vPath = pRequest.url.path;
    final http.Response rResponse;

    if (vPath.endsWith('/replies')) {
      rResponse = http.Response(jsonEncode({'replies': pReplyLists[vCall++]}), 200);
    } else if (vPath.endsWith('/offers')) {
      rResponse = http.Response(jsonEncode({'offers': []}), 200);
    } else if (vPath.endsWith('/progress')) {
      rResponse = http.Response(jsonEncode(buildProgressJson()), 200);
    } else {
      rResponse = http.Response('', 304);
    }

    return rResponse;
  });

  return rClient;
}

void main() {
  test('Une réponse se résume en une ligne', () {
    expect(describeReply(buildReply('1', 'REJECTED')), 'Refus de Kiabi');
    expect(
      describeReply({...buildReply('2', 'INTERVIEW'), 'interview_at': '2026-11-05T14:00'}),
      'Entretien chez Kiabi le 05/11 à 14:00',
    );
  });

  test('Chaque réponse n\'est signalée qu\'une fois', () async {
    final vReminders = FakeReminders();
    final vServer = buildServer([
      [buildReply('a', 'REJECTED')],
      [buildReply('a', 'REJECTED')],
      [buildReply('a', 'REJECTED'), buildReply('b', 'INTERVIEW')],
    ]);
    final vState = RevisionState(
      MemoryRevisionStore()
        ..settings = const ServerSettings(address: 'http://pc/api/v1', token: 'secret')
        ..package = jsonEncode(buildPackageJson())
        ..progress = buildProgressJson(),
      pClientFactory: (pSettings) => ApiClient(pSettings, pClient: vServer),
      reminders: vReminders,
    );

    await vState.load();
    await vState.setOfferAlerts(true);
    await vState.synchronize();
    await vState.synchronize();
    await vState.synchronize();

    expect(vReminders.shownReplies, hasLength(2));
    expect(vReminders.shownReplies.last.single['id'], 'b');
  });
}
