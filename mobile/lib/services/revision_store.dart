// Stockage local de l'application : réglages, contenu, progression et réponses
// en attente d'envoi. L'interface permet de le remplacer par une version en
// mémoire dans les tests.

/// Adresse du serveur et jeton de l'API, saisis au premier lancement.
class ServerSettings {
  const ServerSettings({
    required this.address,
    required this.token,
    this.certificateSha256,
  });

  /// Adresse de l'API, par exemple http://192.168.1.20:8000/api/v1.
  final String address;

  /// Jeton secret créé dans les Paramètres du PC : jamais journalisé.
  final String token;

  /// En HTTPS, empreinte du seul certificat accepté, reçue par le QR code.
  final String? certificateSha256;

  /// Même serveur à une autre adresse : jeton et certificat sont gardés.
  ServerSettings withAddress(String pAddress) {
    final rSettings = ServerSettings(
      address: pAddress,
      token: token,
      certificateSha256: certificateSha256,
    );

    return rSettings;
  }
}

/// Complète l'adresse saisie : schéma http par défaut et préfixe de l'API.
String normalizeAddress(String pAddress) {
  var vAddress = pAddress.trim().replaceFirst(RegExp(r'/+$'), '');

  if (!vAddress.contains('://')) {
    vAddress = 'http://$vAddress';
  }

  if (!vAddress.endsWith('/api/v1')) {
    vAddress = '$vAddress/api/v1';
  }

  final rAddress = vAddress;

  return rAddress;
}

abstract class RevisionStore {
  Future<ServerSettings?> loadSettings();

  Future<void> saveSettings(ServerSettings pSettings);

  /// Contenu de révision, tel que reçu du serveur (JSON).
  Future<String?> loadPackage();

  Future<void> savePackage(String pContent);

  /// Dernière progression reçue du serveur.
  Future<Map<String, dynamic>?> loadProgress();

  Future<void> saveProgress(Map<String, dynamic> pProgress);

  /// Réponses faites hors ligne, pas encore envoyées.
  Future<List<Map<String, dynamic>>> loadPending();

  Future<void> savePending(List<Map<String, dynamic>> pAnswers);

  /// Résultats des examens blancs passés sur le téléphone, les plus récents d'abord.
  Future<List<Map<String, dynamic>>> loadExamResults();

  Future<void> saveExamResults(List<Map<String, dynamic>> pResults);

  /// Préférences de l'application, comme le rappel quotidien.
  /// Nouvelles offres de la semaine, lues hors ligne.
  Future<List<Map<String, dynamic>>> loadOffers();

  Future<void> saveOffers(List<Map<String, dynamic>> pOffers);

  Future<Map<String, dynamic>> loadPreferences();

  Future<void> savePreferences(Map<String, dynamic> pPreferences);
}
