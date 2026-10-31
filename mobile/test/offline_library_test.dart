// Téléphone hors ligne : guides et schémas sans réseau, offres retenues gardées.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/logic/library.dart';
import 'package:jobboard_revision/logic/offer_alerts.dart';
import 'package:jobboard_revision/models/quiz_package.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/screens/library_screen.dart';
import 'package:jobboard_revision/screens/offers_screen.dart';

import 'support/fake_reminders.dart';
import 'support/sample_data.dart';

/// Paquet d'exemple, la question de calcul illustrée par un schéma.
QuizPackage buildLibraryPackage() {
  final vJson = buildPackageJson();
  final vQuestion = (vJson['interactive_questions'] as List).first as Map<String, dynamic>;
  vQuestion['visual'] = {'asset': 'schema.svg', 'alt': "Loi d'Ohm sur une résistance"};
  (vJson['guides'] as List).add(
    {'name': 'securite.md', 'title': 'Sécurité électrique', 'content': 'Consignation'},
  );

  final rPackage = QuizPackage.fromJson(vJson);

  return rPackage;
}

void main() {
  test('La bibliothèque suit les thèmes, guides sans thème à la fin', () {
    final vEntries = buildLibrary(buildLibraryPackage());

    expect([for (final vEntry in vEntries) vEntry.label],
        ['Docker', 'Électricité', 'Sécurité électrique']);
    expect(vEntries[0].guide?.title, 'Guide Docker');
    expect(vEntries[1].guide, isNull);
    expect([for (final vSchema in vEntries[1].schemas) vSchema.description],
        ["Loi d'Ohm sur une résistance"]);
    expect(vEntries[2].domain, 'Autres');
  });

  test('La recherche porte sur le thème, le texte du guide et les schémas', () {
    final vEntries = buildLibrary(buildLibraryPackage());

    List<String> search(String pQuery) => [
          for (final vEntry in vEntries)
            if (vEntry.matches(pQuery)) vEntry.label,
        ];

    expect(search('  '), hasLength(3));
    expect(search('CONSIGNATION'), ['Sécurité électrique']);
    expect(search('ohm'), ['Électricité']);
    expect(search('# docker'), ['Docker']);
  });

  testWidgets('La page Guides et schémas ouvre un guide et filtre', (pTester) async {
    await pTester.pumpWidget(MaterialApp(home: LibraryScreen(package: buildLibraryPackage())));

    expect(find.text('Industrie'), findsOneWidget);
    expect(find.text('1 schéma'), findsOneWidget);

    await pTester.enterText(find.byType(TextField), 'introuvable');
    await pTester.pump();
    expect(find.text('Aucun résultat.'), findsOneWidget);

    await pTester.enterText(find.byType(TextField), 'docker');
    await pTester.pump();
    await pTester.tap(find.text('Docker'));
    await pTester.pumpAndSettle();
    await pTester.tap(find.text('Guide Docker'));
    await pTester.pumpAndSettle();

    expect(find.text('# Docker'), findsOneWidget);
  });

  test('Le filtre Retenues garde intéressé, postulé et entretien', () {
    final vOffers = [
      for (final vStatus in [null, 'INTERESTED', 'APPLIED', 'INTERVIEW', 'IGNORED'])
        {'source_id': '$vStatus', 'status': vStatus, 'near': vStatus == 'APPLIED'},
    ];

    expect(
      [for (final vOffer in filterOffers(vOffers, pRetainedOnly: true)) vOffer['status']],
      ['INTERESTED', 'APPLIED', 'INTERVIEW'],
    );
    expect(filterOffers(vOffers, pRetainedOnly: true, pNearOnly: true), hasLength(1));
    expect(filterOffers(vOffers), hasLength(5));
  });

  test("Une candidature retrouve la fiche de son offre, identifiant texte ou nombre", () {
    final vState = RevisionState(MemoryRevisionStore(), reminders: FakeReminders())
      ..offers = [
        {'source': 'lever', 'source_id': '42', 'title': 'Automaticien'},
      ];

    expect(vState.offerOf({'source': 'lever', 'source_id': 42})?['title'], 'Automaticien');
    expect(vState.offerOf({'source': 'indeed', 'source_id': '42'}), isNull);
  });

  test("Une offre retenue reçue pour la première fois n'est pas signalée", () {
    final vNew = findNewGoodOffers(const [], [
      {'source': 'lever', 'source_id': '1', 'match_score': 90, 'status': 'APPLIED'},
      {'source': 'lever', 'source_id': '2', 'match_score': 90},
    ]);

    expect([for (final vOffer in vNew) vOffer['source_id']], ['2']);
  });
}
