// Tri rapide des nouvelles offres, une à la fois.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/screens/triage_screen.dart';

import 'support/sample_data.dart';

Map<String, dynamic> buildOffer(String pId, {String? pStatus}) => {
      'source': 'lever',
      'source_id': pId,
      'title': 'Offre $pId',
      'status': pStatus,
    };

void main() {
  test('Seules les offres sans statut sont à trier', () {
    expect(
      [
        for (final vOffer in findUnsortedOffers([
          buildOffer('1'),
          buildOffer('2', pStatus: 'APPLIED'),
          buildOffer('3'),
        ]))
          vOffer['source_id'],
      ],
      ['1', '3'],
    );
  });

  testWidgets('Les boutons et le glissement trient une offre après l\'autre', (pTester) async {
    final vState = RevisionState(MemoryRevisionStore());
    vState.offers = [buildOffer('1'), buildOffer('2'), buildOffer('3')];

    await pTester.pumpWidget(MaterialApp(home: TriageScreen(state: vState)));

    expect(find.text('3 offre(s) à trier'), findsOneWidget);

    await pTester.tap(find.text('Intéressé'));
    await pTester.pumpAndSettle();

    expect(find.text('Offre 2'), findsOneWidget);

    await pTester.drag(find.text('Offre 2'), const Offset(-600, 0));
    await pTester.pumpAndSettle();
    await pTester.tap(find.text('Ignorer'));
    await pTester.pumpAndSettle();

    expect([for (final vOffer in vState.offers) vOffer['status']],
        ['INTERESTED', 'IGNORED', 'IGNORED']);
    expect(vState.pendingStatuses, hasLength(3));
    expect(find.textContaining('Toutes les offres sont triées'), findsOneWidget);
  });
}
