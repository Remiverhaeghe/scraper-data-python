part of '../revision_state.dart';

/// Candidatures envoyées hors de Tremplin (site d'entreprise, salon, courrier), notées sur le
/// téléphone puis enregistrées sur le PC à la synchronisation suivante.
mixin QuickApplications on ChangeNotifier {
  Map<String, dynamic> get preferences;

  Future<void> savePreference(String pKey, Object pValue);

  List<Map<String, dynamic>> get pendingQuickApplications => [
        for (final vItem in preferences[pendingQuickApplicationsPreference] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  /// Garde une candidature pour le PC ; refuse une entreprise vide.
  Future<bool> addQuickApplication({
    required String pCompany,
    String pTitle = '',
    String pUrl = '',
    String pNote = '',
    DateTime? pAppliedAt,
  }) async {
    String vClean(String pText, int pMax) {
      final vText = pText.trim().replaceAll(RegExp(r'\s+'), ' ');

      return vText.length > pMax ? vText.substring(0, pMax) : vText;
    }

    final vCompany = vClean(pCompany, 200);
    final rAdded = vCompany.isNotEmpty;

    if (rAdded) {
      await savePreference(pendingQuickApplicationsPreference, [
        ...pendingQuickApplications,
        {
          'company': vCompany,
          'title': vClean(pTitle, 300),
          'url': vClean(pUrl, 1000),
          'note': vClean(pNote, maxNoteLength),
          'applied_at': (pAppliedAt ?? DateTime.now()).toIso8601String().split('.').first,
        },
      ]);
    }

    return rAdded;
  }

  /// Retire une candidature pas encore envoyée, notée par erreur.
  Future<void> removeQuickApplication(int pIndex) async {
    final vItems = pendingQuickApplications..removeAt(pIndex);

    await savePreference(pendingQuickApplicationsPreference, vItems);
  }

  /// Envoie les candidatures en attente ; un serveur plus ancien qui ne connaît pas l'envoi
  /// les garde sur le téléphone pour la fois suivante.
  Future<void> sendQuickApplications(ApiClient pClient) async {
    if (pendingQuickApplications.isEmpty) {
      return;
    }

    try {
      await pClient.uploadQuickApplications(pendingQuickApplications);
      await savePreference(pendingQuickApplicationsPreference, <Map<String, dynamic>>[]);
    } on ApiException catch (vException) {
      if (vException.unreachable) {
        rethrow;
      }

      log('Candidatures du téléphone non reçues : ${vException.message}', name: 'sync');
    }
  }
}
