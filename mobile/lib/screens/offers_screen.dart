// Nouvelles offres de la semaine, les mieux notées en tête, puis offres retenues
// gardées hors ligne : lecture, ouverture de l'annonce et statut envoyé au PC à
// la synchronisation.

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../revision_state.dart';
import '../theme.dart';
import 'offer_detail_screen.dart';
import 'triage_screen.dart';

/// Ouvre l'annonce dans le navigateur ; seules les adresses web sont ouvertes.
Future<void> openOfferUrl(BuildContext pContext, Map<String, dynamic> pOffer) async {
  final vMessenger = ScaffoldMessenger.of(pContext);
  final vUri = Uri.tryParse('${pOffer['url'] ?? ''}');

  final vOpened = vUri != null &&
      (vUri.scheme == 'https' || vUri.scheme == 'http') &&
      await launchUrl(vUri, mode: LaunchMode.externalApplication);

  if (!vOpened) {
    vMessenger.showSnackBar(const SnackBar(content: Text("L'annonce n'a pas pu être ouverte.")));
  }
}

/// Offres affichées selon les filtres : près de chez moi, retenues.
List<Map<String, dynamic>> filterOffers(
  List<Map<String, dynamic>> pOffers, {
  bool pNearOnly = false,
  bool pRetainedOnly = false,
}) =>
    [
      for (final vOffer in pOffers)
        if ((!pNearOnly || vOffer['near'] == true) &&
            (!pRetainedOnly || retainedStatuses.contains(vOffer['status'])))
          vOffer,
    ];

class OffersScreen extends StatefulWidget {
  const OffersScreen({super.key, required this.state});

  final RevisionState state;

  @override
  State<OffersScreen> createState() => _OffersScreenState();
}

class _OffersScreenState extends State<OffersScreen> {
  /// Seules les offres dans le rayon des alertes réglé sur le PC.
  bool nearOnly = false;

  /// Seules les offres retenues, lisibles même sans réseau.
  bool retainedOnly = false;

  @override
  Widget build(BuildContext context) {
    final vState = widget.state;

    final rScreen = Scaffold(
      appBar: AppBar(
        title: const Text('Offres'),
        actions: [
          IconButton(
            tooltip: 'Tri rapide',
            icon: const Icon(Icons.swipe),
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(builder: (_) => TriageScreen(state: vState)),
            ),
          ),
        ],
      ),
      body: ListenableBuilder(
        listenable: vState,
        builder: (_, __) {
          final vHasNear = vState.offers.any((vOffer) => vOffer['near'] == true);
          final vOffers = filterOffers(
            vState.offers,
            pNearOnly: nearOnly,
            pRetainedOnly: retainedOnly,
          );

          if (vState.offers.isEmpty) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text(
                  "Aucune offre reçue : synchronisez depuis l'accueil.",
                  textAlign: TextAlign.center,
                ),
              ),
            );
          }

          return ListView(
            padding: const EdgeInsets.all(12),
            children: [
              Wrap(
                spacing: 8,
                children: [
                  FilterChip(
                    avatar: const Icon(Icons.bookmark_outline, size: 18),
                    label: const Text('Retenues'),
                    selected: retainedOnly,
                    onSelected: (pSelected) => setState(() => retainedOnly = pSelected),
                  ),
                  // Ce filtre n'apparaît qu'avec un domicile et un rayon réglés sur le PC.
                  if (vHasNear)
                    FilterChip(
                      avatar: const Icon(Icons.place_outlined, size: 18),
                      label: const Text('Près de chez moi'),
                      selected: nearOnly,
                      onSelected: (pSelected) => setState(() => nearOnly = pSelected),
                    ),
                ],
              ),
              if (vOffers.isEmpty)
                const Padding(
                  padding: EdgeInsets.all(24),
                  child: Text('Aucune offre pour ces filtres.', textAlign: TextAlign.center),
                ),
              for (final vOffer in vOffers) OfferCard(state: vState, offer: vOffer),
            ],
          );
        },
      ),
    );

    return rScreen;
  }
}

/// Une offre : poste, entreprise, lieu, correspondance et statut à choisir.
class OfferCard extends StatelessWidget {
  const OfferCard({super.key, required this.state, required this.offer});

  final RevisionState state;
  final Map<String, dynamic> offer;

  Future<void> open(BuildContext pContext) => openOfferUrl(pContext, offer);

  @override
  Widget build(BuildContext context) {
    final vTheme = Theme.of(context);
    final vScore = offer['match_score'];
    final vStatus = offer['status'] as String?;
    final vDistance = offer['distance_km'];
    final vSimilarTo = offer['similar_to'];
    // Un entretien se décide sur le PC : le statut s'affiche sans menu.
    final vLocked = vStatus != null && !offerStatuses.containsKey(vStatus);
    final vStatusLabel = Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: Text(
        offerStatusLabels[vStatus] ?? 'Statut',
        style: TextStyle(
          color: vStatus == 'APPLIED' || vLocked
              ? successColorOf(context)
              : vTheme.colorScheme.primary,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
    final vDetails = [
      offer['company'],
      offer['location'],
      if (vDistance != null) '$vDistance km',
      offer['contract'],
      if (vSimilarTo != null) 'proche de « $vSimilarTo »',
    ].where((vValue) => vValue != null && '$vValue'.isNotEmpty).join(' · ');

    final rCard = Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => OfferDetailScreen(
              offer: offer,
              onOpen: () => open(context),
              onNote: (pText) => state.addOfferNote(offer, pText),
            ),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 8, 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('${offer['title'] ?? ''}', style: vTheme.textTheme.titleMedium),
              if (vDetails.isNotEmpty) Text(vDetails, style: vTheme.textTheme.bodySmall),
              const SizedBox(height: 8),
              Row(
                children: [
                  if (vScore != null)
                    Chip(
                      label: Text('$vScore % de correspondance'),
                      visualDensity: VisualDensity.compact,
                    ),
                  const Spacer(),
                  TextButton.icon(
                    onPressed: () => open(context),
                    icon: const Icon(Icons.open_in_new, size: 18),
                    label: const Text('Ouvrir'),
                  ),
                  if (vLocked)
                    vStatusLabel
                  else
                    PopupMenuButton<String>(
                      tooltip: 'Changer le statut',
                      onSelected: (pStatus) => state.setOfferStatus(offer, pStatus),
                      itemBuilder: (_) => [
                        for (final vEntry in offerStatuses.entries)
                          CheckedPopupMenuItem(
                            value: vEntry.key,
                            checked: vEntry.key == vStatus,
                            child: Text(vEntry.value),
                          ),
                      ],
                      child: vStatusLabel,
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );

    return rCard;
  }
}
