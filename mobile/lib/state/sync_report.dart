part of '../revision_state.dart';

/// Bilan d'une synchronisation, montré à l'utilisateur.
class SyncReport {
  const SyncReport({required this.sent, required this.rejected, required this.contentUpdated});

  final int sent;
  final int rejected;
  final bool contentUpdated;

  String describe() {
    final rText = [
      if (sent > 0) '$sent réponse(s) envoyée(s)',
      if (rejected > 0) '$rejected refusée(s) par le serveur',
      contentUpdated ? 'questions mises à jour' : 'questions déjà à jour',
    ].join(', ');

    return rText;
  }
}
