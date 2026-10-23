// Nouvelles offres à signaler : arrivées depuis la dernière synchronisation,
// proches du profil d'après le score calculé par le PC, ou proches d'une offre
// retenue (similar_to).

/// Score minimal d'une offre signalée, en pourcentage.
const offerAlertScore = 50;

String offerKey(Map<String, dynamic> pOffer) => '${pOffer['source']}/${pOffer['source_id']}';

/// Retourne les offres absentes de la liste précédente, assez bien notées ou
/// proches d'une offre retenue.
List<Map<String, dynamic>> findNewGoodOffers(
  List<Map<String, dynamic>> pPrevious,
  List<Map<String, dynamic>> pCurrent,
) {
  final vKnown = {for (final vOffer in pPrevious) offerKey(vOffer)};

  final rOffers = [
    for (final vOffer in pCurrent)
      if (!vKnown.contains(offerKey(vOffer)) &&
          (((vOffer['match_score'] as num?) ?? 0) >= offerAlertScore ||
              vOffer['similar_to'] != null))
        vOffer,
  ];

  return rOffers;
}
