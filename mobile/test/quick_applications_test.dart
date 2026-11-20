// Candidatures notées sur le téléphone, enregistrées sur le PC à la synchronisation.

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/screens/quick_application_screen.dart';
import 'package:jobboard_revision/services/api_client.dart';
import 'package:jobboard_revision/services/revision_store.dart';

import 'support/fake_reminders.dart';
import 'support/sample_data.dart';

/// État relié à un PC simulé ; [pQuickStatus] est la réponse à l'envoi des candidatures.
RevisionState buildState(List<List<dynamic>> pSent, {int pQuickStatus = 200}) {
  final vServer = MockClient((pRequest) async {
    final vPath = pRequest.url.path;

    if (vPath.endsWith('/quick-applications')) {
      pSent.add((jsonDecode(pRequest.body) as Map)['applications'] as List);

      return http.Response(
        jsonEncode({'added': 1, 'known': 0, 'rejected': []}),
        pQuickStatus,
      );
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

  return RevisionState(
    MemoryRevisionStore()
      ..settings = const ServerSettings(address: 'http://pc/api/v1', token: 'secret')
      ..package = jsonEncode(buildPackageJson())
      ..progress = buildProgressJson(),
    pClientFactory: (pSettings) => ApiClient(pSettings, pClient: vServer),
    reminders: FakeReminders(),
  );
}

void main() {
  test('Une candidature notée part au PC une fois, puis est oubliée', () async {
    final vSent = <List<dynamic>>[];
    final vState = buildState(vSent);

    await vState.load();
    expect(await vState.addQuickApplication(pCompany: '   '), isFalse);
    expect(
      await vState.addQuickApplication(
        pCompany: '  Exemple   Industrie ',
        pTitle: 'Technicien',
        pAppliedAt: DateTime(2026, 11, 18, 12),
      ),
      isTrue,
    );

    await vState.synchronize();
    await vState.synchronize();

    expect(vSent, hasLength(1));
    expect(vSent.single.single['company'], 'Exemple Industrie');
    expect(vSent.single.single['applied_at'], '2026-11-18T12:00:00');
    expect(vState.pendingQuickApplications, isEmpty);
  });

  test('Un PC qui ne connaît pas l envoi garde les candidatures pour plus tard', () async {
    final vSent = <List<dynamic>>[];
    final vState = buildState(vSent, pQuickStatus: 404);

    await vState.load();
    await vState.addQuickApplication(pCompany: 'Exemple');
    await vState.synchronize();

    expect(vSent, hasLength(1));
    expect(vState.pendingQuickApplications, hasLength(1));
    await vState.removeQuickApplication(0);
    expect(vState.pendingQuickApplications, isEmpty);
  });

  testWidgets('L écran demande l entreprise et liste ce qui attend le PC', (pTester) async {
    final vState = buildState([]);
    await vState.load();

    await pTester.pumpWidget(MaterialApp(home: QuickApplicationScreen(state: vState)));
    await pTester.tap(find.text('Garder pour le PC'));
    await pTester.pumpAndSettle();
    expect(find.text("Indiquez au moins l'entreprise"), findsOneWidget);

    await pTester.enterText(find.widgetWithText(TextField, 'Entreprise'), 'Exemple');
    await pTester.enterText(find.widgetWithText(TextField, 'Poste (facultatif)'), 'Technicien');
    await pTester.tap(find.text('Garder pour le PC'));
    await pTester.pumpAndSettle();

    expect(find.text("Indiquez au moins l'entreprise"), findsNothing);
    expect(find.text("1 candidature en attente d'envoi"), findsOneWidget);
    expect(find.text('Exemple'), findsOneWidget);
    expect(vState.pendingQuickApplications.single['title'], 'Technicien');
  });
}
