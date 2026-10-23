// Appels à l'API de révision du serveur (web/api.py) : contenu, progression et
// envoi des réponses. Le jeton voyage dans l'en-tête Authorization.

import 'dart:async';
import 'dart:convert';
import 'dart:developer';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';

import 'revision_store.dart';

/// Erreur à montrer telle quelle à l'utilisateur.
class ApiException implements Exception {
  const ApiException(this.message, {this.unreachable = false});

  final String message;

  /// Vrai si le serveur n'a pas répondu : son adresse a peut-être changé.
  final bool unreachable;

  @override
  String toString() => message;
}

/// Indique si un certificat est celui épinglé, par son empreinte SHA-256.
bool isPinnedCertificate(List<int> pDer, String pFingerprint) {
  final rPinned = sha256.convert(pDer).toString() == pFingerprint.toLowerCase();

  return rPinned;
}

/// Client HTTP du serveur : en HTTPS auto-signé, seul le certificat épinglé passe.
http.Client buildServerClient(ServerSettings pSettings) {
  final vFingerprint = pSettings.certificateSha256;

  if (vFingerprint == null) {
    return http.Client();
  }

  // Appelé seulement pour un certificat qu'aucune autorité ne garantit, comme
  // celui créé sur le PC : il n'est accepté que s'il a l'empreinte du QR code.
  final vHttpClient = HttpClient()
    ..badCertificateCallback =
        (pCertificate, _, __) => isPinnedCertificate(pCertificate.der, vFingerprint);

  final rClient = IOClient(vHttpClient);

  return rClient;
}

class ApiClient {
  ApiClient(this.settings, {http.Client? pClient})
      : client = pClient ?? buildServerClient(settings);

  static const timeout = Duration(seconds: 30);

  final ServerSettings settings;
  final http.Client client;

  Uri buildUri(String pPath) {
    final rUri = Uri.parse('${settings.address}$pPath');

    return rUri;
  }

  Map<String, String> buildHeaders() {
    final rHeaders = {
      'Authorization': 'Bearer ${settings.token}',
      'Accept': 'application/json',
    };

    return rHeaders;
  }

  /// Envoie une requête et traduit les échecs en messages compréhensibles.
  Future<http.Response> send(String pName, Future<http.Response> Function() pRequest) async {
    final http.Response rResponse;

    try {
      rResponse = await pRequest().timeout(timeout);
    } on TimeoutException {
      log('$pName : délai dépassé', name: 'api');
      throw const ApiException(
        'Le serveur ne répond pas : réessayez plus tard.',
        unreachable: true,
      );
    } on http.ClientException catch (vException) {
      log('$pName : ${vException.message}', name: 'api');
      throw const ApiException(
        "Serveur injoignable : vérifiez l'adresse, le réseau et que le serveur web tourne.",
        unreachable: true,
      );
    }

    if (rResponse.statusCode == 401) {
      // Le jeton n'est jamais journalisé, même refusé.
      log('$pName : jeton refusé', name: 'api');
      throw const ApiException('Jeton refusé : recopiez-le depuis les Paramètres du PC.');
    }

    if (rResponse.statusCode >= 400) {
      log('$pName : erreur ${rResponse.statusCode}', name: 'api');
      throw ApiException('Erreur du serveur (${rResponse.statusCode}).');
    }

    return rResponse;
  }

  Map<String, dynamic> decode(http.Response pResponse) {
    // Décodé en UTF-8 : sans jeu de caractères précisé, les accents seraient
    // lus en Latin-1.
    final rData = jsonDecode(utf8.decode(pResponse.bodyBytes)) as Map<String, dynamic>;

    return rData;
  }

  /// Télécharge le contenu ; null s'il n'a pas changé depuis pVersion.
  Future<String?> downloadQuiz(String? pVersion) async {
    final vHeaders = buildHeaders();

    if (pVersion != null) {
      vHeaders['If-None-Match'] = '"$pVersion"';
    }

    final vResponse = await send(
      'Contenu',
      () => client.get(buildUri('/quiz'), headers: vHeaders),
    );

    final rContent = vResponse.statusCode == 304 ? null : utf8.decode(vResponse.bodyBytes);

    return rContent;
  }

  Future<Map<String, dynamic>> downloadProgress() async {
    final vResponse = await send(
      'Progression',
      () => client.get(buildUri('/progress'), headers: buildHeaders()),
    );

    final rProgress = decode(vResponse);

    return rProgress;
  }

  /// Télécharge les nouvelles offres de la semaine, les mieux notées en tête.
  Future<List<Map<String, dynamic>>> downloadOffers() async {
    final vResponse = await send(
      'Offres',
      () => client.get(buildUri('/offers'), headers: buildHeaders()),
    );

    final rOffers = [
      for (final vOffer in decode(vResponse)['offers'] as List? ?? const [])
        Map<String, dynamic>.from(vOffer as Map),
    ];

    return rOffers;
  }

  /// Envoie les statuts donnés aux offres sur le téléphone.
  Future<Map<String, dynamic>> uploadStatusChanges(List<Map<String, dynamic>> pChanges) async {
    final vResponse = await send(
      'Statuts',
      () => client.post(
        buildUri('/applications'),
        headers: {...buildHeaders(), 'Content-Type': 'application/json'},
        body: jsonEncode({'changes': pChanges}),
      ),
    );

    final rReport = decode(vResponse);

    return rReport;
  }

  /// Envoie les questions signalées comme fausses ou ambiguës.
  Future<Map<String, dynamic>> uploadFlags(List<String> pQuestionIds) async {
    final vResponse = await send(
      'Signalements',
      () => client.post(
        buildUri('/flags'),
        headers: {...buildHeaders(), 'Content-Type': 'application/json'},
        body: jsonEncode({'question_ids': pQuestionIds}),
      ),
    );

    final rReport = decode(vResponse);

    return rReport;
  }

  /// Envoie les notes des examens blancs ; le serveur ignore celles qu'il a déjà.
  Future<Map<String, dynamic>> uploadExams(List<Map<String, dynamic>> pExams) async {
    final vResponse = await send(
      'Examens',
      () => client.post(
        buildUri('/exams'),
        headers: {...buildHeaders(), 'Content-Type': 'application/json'},
        body: jsonEncode({'exams': pExams}),
      ),
    );

    final rReport = decode(vResponse);

    return rReport;
  }

  /// Envoie des réponses ; retourne le bilan du serveur et la progression à jour.
  Future<Map<String, dynamic>> uploadAnswers(List<Map<String, dynamic>> pAnswers) async {
    final vResponse = await send(
      'Réponses',
      () => client.post(
        buildUri('/answers'),
        headers: {...buildHeaders(), 'Content-Type': 'application/json'},
        body: jsonEncode({'answers': pAnswers}),
      ),
    );

    final rReport = decode(vResponse);

    return rReport;
  }
}
