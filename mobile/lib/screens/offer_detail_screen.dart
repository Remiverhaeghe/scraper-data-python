// Fiche d'une offre lisible hors ligne : salaire, compétences couvertes et
// manquantes, description, et lien vers l'annonce.

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../revision_state.dart';
import '../theme.dart';

/// Adresse OpenStreetMap centrée sur l'offre, ou null sans position connue.
Uri? buildMapUri(Map<String, dynamic> pOffer) {
  final vLatitude = pOffer['latitude'];
  final vLongitude = pOffer['longitude'];

  final rUri = vLatitude is num && vLongitude is num
      ? Uri.https('www.openstreetmap.org', '/', {
          'mlat': '$vLatitude',
          'mlon': '$vLongitude',
        }).replace(fragment: 'map=14/$vLatitude/$vLongitude')
      : null;

  return rUri;
}

class OfferDetailScreen extends StatelessWidget {
  const OfferDetailScreen({super.key, required this.offer, required this.onOpen, this.onNote});

  final Map<String, dynamic> offer;

  /// Ouvre l'annonce d'origine dans le navigateur.
  final VoidCallback onOpen;

  /// Garde une note rapide sur l'offre, ajoutée à la candidature sur le PC.
  final Future<void> Function(String)? onNote;

  Future<void> writeNote(BuildContext pContext) async {
    final vMessenger = ScaffoldMessenger.of(pContext);
    final vController = TextEditingController();
    final vText = await showDialog<String>(
      context: pContext,
      builder: (pDialogContext) => AlertDialog(
        title: const Text('Note rapide'),
        content: TextField(
          controller: vController,
          autofocus: true,
          minLines: 3,
          maxLines: 6,
          maxLength: maxNoteLength,
          decoration: const InputDecoration(hintText: 'Appel du recruteur, impression, à faire…'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(pDialogContext).pop(),
            child: const Text('Annuler'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(pDialogContext).pop(vController.text),
            child: const Text('Garder'),
          ),
        ],
      ),
    );

    vController.dispose();

    if (vText == null || vText.trim().isEmpty) {
      return;
    }

    await onNote!(vText);
    vMessenger.showSnackBar(
      const SnackBar(
          content: Text('Note gardée : elle rejoint la candidature à la synchronisation.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final vTheme = Theme.of(context);
    final vCovered = List<String>.from(offer['covered'] as List? ?? const []);
    final vMissing = List<String>.from(offer['missing'] as List? ?? const []);
    final vDetails = [
      offer['company'],
      offer['location'],
      if (offer['distance_km'] != null) '${offer['distance_km']} km',
      offer['contract'],
      offer['salary'],
    ].where((vValue) => vValue != null && '$vValue'.isNotEmpty).join(' · ');
    final vDescription = '${offer['description'] ?? ''}'.trim();
    final vMapUri = buildMapUri(offer);

    final rScreen = Scaffold(
      appBar: AppBar(title: const Text('Offre')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('${offer['title'] ?? ''}', style: vTheme.textTheme.titleLarge),
          if (vDetails.isNotEmpty) Text(vDetails, style: vTheme.textTheme.bodyMedium),
          if (offer['match_score'] != null)
            Text('${offer['match_score']} % de correspondance avec votre profil'),
          const SizedBox(height: 12),
          if (vCovered.isNotEmpty || vMissing.isNotEmpty)
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final vSkill in vCovered)
                  Chip(
                    avatar: Icon(Icons.check, size: 16, color: successColorOf(context)),
                    label: Text(vSkill),
                    visualDensity: VisualDensity.compact,
                  ),
                for (final vSkill in vMissing)
                  Chip(
                    avatar: Icon(Icons.close, size: 16, color: vTheme.colorScheme.error),
                    label: Text(vSkill),
                    visualDensity: VisualDensity.compact,
                  ),
              ],
            ),
          const SizedBox(height: 12),
          SelectableText(
            vDescription.isEmpty ? 'Description non transmise par la source.' : vDescription,
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: onOpen,
            icon: const Icon(Icons.open_in_new),
            label: const Text("Ouvrir l'annonce"),
          ),
          if (onNote != null) ...[
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () => writeNote(context),
              icon: const Icon(Icons.edit_note),
              label: const Text('Note rapide'),
            ),
          ],
          if (vMapUri != null) ...[
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () => launchUrl(vMapUri, mode: LaunchMode.externalApplication),
              icon: const Icon(Icons.map_outlined),
              label: const Text('Voir sur la carte'),
            ),
          ],
        ],
      ),
    );

    return rScreen;
  }
}
