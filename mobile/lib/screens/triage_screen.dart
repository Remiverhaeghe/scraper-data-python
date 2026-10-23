// Tri rapide des nouvelles offres, une à la fois : glisser vers la droite pour
// « Intéressé », vers la gauche pour « Ignorée ». Le statut part au PC à la
// synchronisation suivante.

import 'package:flutter/material.dart';

import '../revision_state.dart';
import '../theme.dart';

/// Offres encore sans statut, dans l'ordre reçu du PC (les mieux notées en tête).
List<Map<String, dynamic>> findUnsortedOffers(List<Map<String, dynamic>> pOffers) => [
      for (final vOffer in pOffers)
        if (vOffer['status'] == null) vOffer,
    ];

class TriageScreen extends StatelessWidget {
  const TriageScreen({super.key, required this.state});

  final RevisionState state;

  Future<void> sort(Map<String, dynamic> pOffer, String pStatus) =>
      state.setOfferStatus(pOffer, pStatus);

  @override
  Widget build(BuildContext context) {
    final rScreen = Scaffold(
      appBar: AppBar(title: const Text('Tri rapide')),
      body: ListenableBuilder(
        listenable: state,
        builder: (_, __) {
          final vUnsorted = findUnsortedOffers(state.offers);

          if (vUnsorted.isEmpty) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text(
                  'Toutes les offres sont triées : leur statut partira au PC à la '
                  'prochaine synchronisation.',
                  textAlign: TextAlign.center,
                ),
              ),
            );
          }

          final vOffer = vUnsorted.first;

          return Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                Text('${vUnsorted.length} offre(s) à trier'),
                const SizedBox(height: 12),
                Expanded(
                  child: Dismissible(
                    key: ValueKey('${vOffer['source']}/${vOffer['source_id']}'),
                    background: buildSwipeHint(context, true),
                    secondaryBackground: buildSwipeHint(context, false),
                    onDismissed: (pDirection) => sort(
                      vOffer,
                      pDirection == DismissDirection.startToEnd ? 'INTERESTED' : 'IGNORED',
                    ),
                    child: TriageCard(offer: vOffer),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => sort(vOffer, 'IGNORED'),
                        icon: const Icon(Icons.close),
                        label: const Text('Ignorer'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: FilledButton.icon(
                        onPressed: () => sort(vOffer, 'INTERESTED'),
                        icon: const Icon(Icons.star_outline),
                        label: const Text('Intéressé'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );

    return rScreen;
  }

  /// Fond révélé en glissant : vert pour garder l'offre, rouge pour l'ignorer.
  Widget buildSwipeHint(BuildContext pContext, bool pKeep) {
    final rHint = Container(
      alignment: pKeep ? Alignment.centerLeft : Alignment.centerRight,
      padding: const EdgeInsets.symmetric(horizontal: 24),
      color: (pKeep ? successColorOf(pContext) : dangerColorOf(pContext)).withValues(alpha: 0.15),
      child: Text(pKeep ? 'Intéressé' : 'Ignorer'),
    );

    return rHint;
  }
}

/// Une offre en grand : intitulé, entreprise, lieu, salaire et correspondance.
class TriageCard extends StatelessWidget {
  const TriageCard({super.key, required this.offer});

  final Map<String, dynamic> offer;

  @override
  Widget build(BuildContext context) {
    final vTheme = Theme.of(context);
    final vDetails = [
      offer['company'],
      offer['location'],
      if (offer['distance_km'] != null) '${offer['distance_km']} km',
      offer['contract'],
      offer['salary'],
    ].where((vValue) => vValue != null && '$vValue'.isNotEmpty).join(' · ');
    final vDescription = '${offer['description'] ?? ''}'.trim();

    final rCard = Card(
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('${offer['title'] ?? 'Offre sans titre'}', style: vTheme.textTheme.titleLarge),
          if (vDetails.isNotEmpty) Text(vDetails),
          if (offer['match_score'] != null)
            Text('${offer['match_score']} % de correspondance avec votre profil'),
          const SizedBox(height: 12),
          if (vDescription.isNotEmpty)
            Text(vDescription, maxLines: 12, overflow: TextOverflow.ellipsis),
        ],
      ),
    );

    return rCard;
  }
}
