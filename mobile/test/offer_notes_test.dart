// Notes rapides prises sur une offre, envoyées une fois au PC.

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/services/api_client.dart';
import 'package:jobboard_revision/services/revision_store.dart';

import 'support/fake_reminders.dart';
import 'support/sample_data.dart';

void main() {
  test('Une note rapide part au PC à la synchronisation, puis est oubliée', () async {
    final vSent = <List<dynamic>>[];
    final vServer = MockClient((pRequest) async {
      final vPath = pRequest.url.path;

      if (vPath.endsWith('/notes')) {
        vSent.add((jsonDecode(pRequest.body) as Map)['notes'] as List);

        return http.Response(jsonEncode({'applied': 1, 'rejected': []}), 200);
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
    final vOffer = {'source': 'lever', 'source_id': '1', 'title': 'Dev'};

    await vState.load();
    await vState.addOfferNote(vOffer, '   ');
    await vState.addOfferNote(vOffer, ' Rappel du recruteur ');

    expect(vState.pendingNotes, hasLength(1));

    await vState.synchronize();
    await vState.synchronize();

    expect(vSent, hasLength(1));
    expect(vSent.single.single['text'], 'Rappel du recruteur');
    expect(vSent.single.single['source_id'], '1');
    expect(vState.pendingNotes, isEmpty);
  });
}
