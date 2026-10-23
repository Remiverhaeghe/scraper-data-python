// Contenu du QR code de connexion affiché dans les Paramètres du PC
// (job/mobile_sync.py) : {"address": "...", "token": "..."}.

import 'dart:convert';

import 'revision_store.dart';

/// Retourne l'adresse et le jeton lus dans un QR code, ou null s'il vient d'ailleurs.
ServerSettings? parseConnectionCode(String? pCode) {
  ServerSettings? rSettings;

  try {
    final vData = jsonDecode(pCode ?? '');

    if (vData is Map &&
        vData['address'] is String &&
        vData['token'] is String &&
        (vData['token'] as String).isNotEmpty) {
      rSettings = ServerSettings(
        address: normalizeAddress(vData['address'] as String),
        token: vData['token'] as String,
        certificateSha256: vData['certificate_sha256'] as String?,
      );
    }
  } on FormatException {
    // Un autre QR code (lien, texte) : il est simplement ignoré.
    rSettings = null;
  }

  return rSettings;
}
