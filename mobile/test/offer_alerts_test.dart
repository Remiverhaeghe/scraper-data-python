// Alerte des nouvelles offres bien notées, à la synchronisation.

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jobboard_revision/logic/offer_alerts.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/screens/offers_screen.dart';
import 'package:jobboard_revision/services/api_client.dart';
import 'package:jobboard_revision/services/revision_store.dart';

import 'support/fake_reminders.dart';
import 'support/sample_data.dart';

Map<String, dynamic> buildOffer(String pId, int? pScore) =>
    {'source': 'lever', 'source_id': pId, 'title': 'Offre $pId', 'match_score': pScore};

/// Serveur simulé : renvoie à chaque appel la liste d'offres suivante.
MockClient buildServer(List<List<Map<String, dynamic>>> pOfferLists) {
  var vCall = 0;

  final rClient = MockClient((pRequest) async {
    final vPath = pRequest.url.path;
    final http.Response rResponse;

    if (vPath.endsWith('/offers')) {
      rResponse = http.Response(jsonEncode({'offers': pOfferLists[vCall++]}), 200);
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
  testOfferCardShowsDistance();

  test('Seules les nouvelles offres assez proches du profil sont retenues', () {
    final vNew = findNewGoodOffers(
      [buildOffer('1', 90)],
      [buildOffer('1', 90), buildOffer('2', 50), buildOffer('3', 49), buildOffer('4', null)],
    );

    expect([for (final vOffer in vNew) vOffer['source_id']], ['2']);

    final vSimilar = findNewGoodOffers(const [], [
      {...buildOffer('5', 20), 'similar_to': 'Technicien de maintenance'},
    ]);

    expect(vSimilar, hasLength(1));

    final vPreferred = findNewGoodOffers(const [], [
      {...buildOffer('6', 10), 'preferred': true},
    ]);

    expect(vPreferred, hasLength(1));
  });

  test('Les nouvelles offres sont signalées une fois, alerte active', () async {
    final vReminders = FakeReminders();
    final vServer = buildServer([
      [buildOffer('1', 80)],
      [buildOffer('1', 80), buildOffer('2', 70)],
      [buildOffer('1', 80), buildOffer('2', 70), buildOffer('3', 90)],
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
    await vState.synchronize();

    expect(vReminders.shownOffers, isEmpty);

    expect(await vState.setOfferAlerts(true), isTrue);
    expect(vReminders.offerChecks, [true]);

    await vState.synchronize();

    expect([for (final vOffer in vReminders.shownOffers.single) vOffer['source_id']], ['2']);

    await vState.setOfferAlerts(false);
    await vState.synchronize();

    expect(vReminders.shownOffers, hasLength(1));
    expect(vReminders.offerChecks, [true, false]);
  });

  test('Une alerte refusée par le téléphone reste coupée', () async {
    final vReminders = FakeReminders(granted: false);
    final vState = RevisionState(MemoryRevisionStore(), reminders: vReminders);

    expect(await vState.setOfferAlerts(true), isFalse);
    expect(vState.offerAlertsEnabled, isFalse);
    expect(vReminders.offerChecks, [false]);
  });
}

void testOfferCardShowsDistance() {
  testWidgets('La fiche d\'une offre affiche sa distance au domicile', (pTester) async {
    final vState = RevisionState(MemoryRevisionStore());

    await pTester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: OfferCard(
            state: vState,
            offer: {
              ...buildOffer('1', 80),
              'company': 'Acme',
              'location': 'Roubaix',
              'distance_km': 12
            },
          ),
        ),
      ),
    );

    expect(find.text('Acme · Roubaix · 12 km'), findsOneWidget);
  });
}
