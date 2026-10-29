// Lignes du widget de l'écran d'accueil et mise à jour après synchronisation.

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/services/api_client.dart';
import 'package:jobboard_revision/services/home_widget_service.dart';
import 'package:jobboard_revision/services/revision_store.dart';

import 'support/fake_reminders.dart';
import 'support/sample_data.dart';

/// Widget simulé : garde les lignes reçues.
class FakeHomeWidget implements HomeWidgetUpdater {
  final shown = <(String, String)>[];

  @override
  Future<void> show((String, String) pLines) async => shown.add(pLines);
}

void main() {
  test('Les lignes résument la révision et le prochain entretien', () {
    final vNow = DateTime(2026, 10, 25, 9);

    expect(buildWidgetLines(0, const [], vNow),
        ("Rien à revoir aujourd'hui", 'Aucun entretien prévu'));
    expect(
      buildWidgetLines(
        12,
        [
          {'company': 'Globex', 'interview_at': '2026-10-30T10:00'},
          {'company': 'Acme', 'interview_at': '2026-10-27T14:30'},
          {'company': 'Ancien', 'interview_at': '2026-10-01T14:30'},
        ],
        vNow,
      ),
      ('12 questions à revoir', 'Entretien le 27/10 à 14:30 · Acme'),
    );
    expect(buildWidgetLines(1, const [], vNow).$1, '1 question à revoir');
  });

  test('Le widget est mis à jour après la synchronisation', () async {
    final vServer = MockClient((pRequest) async {
      final vPath = pRequest.url.path;

      if (vPath.endsWith('/offers') || vPath.endsWith('/withdrawn')) {
        return http.Response(jsonEncode({'offers': []}), 200);
      }

      if (vPath.endsWith('/replies') || vPath.endsWith('/interviews')) {
        return http.Response(jsonEncode({'replies': [], 'interviews': []}), 200);
      }

      if (vPath.endsWith('/tracking')) {
        return http.Response(jsonEncode({'applications': [], 'sheets': {}}), 200);
      }

      if (vPath.endsWith('/progress')) {
        return http.Response(jsonEncode(buildProgressJson()), 200);
      }

      return http.Response('', 304);
    });
    final vWidget = FakeHomeWidget();
    final vState = RevisionState(
      MemoryRevisionStore()
        ..settings = const ServerSettings(address: 'http://pc/api/v1', token: 'secret')
        ..package = jsonEncode(buildPackageJson())
        ..progress = buildProgressJson(),
      pClientFactory: (pSettings) => ApiClient(pSettings, pClient: vServer),
      reminders: FakeReminders(),
      homeWidget: vWidget,
    );

    await vState.load();
    await vState.synchronize();
    await Future<void>.delayed(Duration.zero);

    expect(vWidget.shown, hasLength(1));
    expect(vWidget.shown.single.$2, 'Aucun entretien prévu');
  });
}
