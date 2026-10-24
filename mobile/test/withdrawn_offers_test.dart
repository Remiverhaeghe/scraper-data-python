// Offres suivies retirées par leur site, signalées une fois sur le téléphone.

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/services/api_client.dart';
import 'package:jobboard_revision/services/revision_store.dart';

import 'support/fake_reminders.dart';
import 'support/sample_data.dart';

Map<String, dynamic> buildOffer(String pId) =>
    {'source': 'lever', 'source_id': pId, 'title': 'Offre $pId', 'status': 'APPLIED'};

void main() {
  test('Chaque offre retirée n\'est signalée qu\'une fois', () async {
    final vLists = [
      [buildOffer('1')],
      [buildOffer('1')],
      [buildOffer('1'), buildOffer('2')],
    ];
    var vCall = 0;
    final vServer = MockClient((pRequest) async {
      final vPath = pRequest.url.path;

      if (vPath.endsWith('/withdrawn')) {
        return http.Response(jsonEncode({'offers': vLists[vCall++]}), 200);
      }

      if (vPath.endsWith('/offers')) {
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
    final vReminders = FakeReminders();
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

    for (var vIndex = 0; vIndex < 3; vIndex++) {
      await vState.synchronize();
    }

    expect(vReminders.shownWithdrawn, hasLength(2));
    expect(vReminders.shownWithdrawn.last.single['source_id'], '2');
  });
}
