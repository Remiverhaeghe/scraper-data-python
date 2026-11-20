// Recherche du serveur Tremplin sur le Wi-Fi : chaque adresse du réseau
// local est interrogée sur la route /api/v1/ping, qui ne demande pas de jeton.

import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';

import '../models/quiz_package.dart';
import 'api_client.dart';
import 'revision_store.dart';

/// Port du tableau de bord sur le PC (WEB_PORT de config.py).
const serverPort = 8000;

/// Un PC du réseau local répond en quelques millisecondes : au-delà, l'adresse
/// est considérée comme vide.
const probeTimeout = Duration(milliseconds: 800);

/// Adresses interrogées en même temps.
const probeBatch = 32;

/// Échange du code : une seule requête, le PC répond vite ou pas du tout.
const pairingTimeout = Duration(seconds: 10);

/// Identifiant renvoyé par le ping du serveur (SERVER_IDENTIFIER côté PC) : l'ancien
/// nom de l'application, gardé pour que téléphones et serveurs de versions différentes
/// se reconnaissent.
const applicationName = 'JobBoard Perso';

/// Indique si une adresse IPv4 appartient à un réseau privé (maison, entreprise).
bool isPrivateAddress(String pAddress) {
  final vParts = pAddress.split('.').map(int.tryParse).toList();

  final rPrivate = vParts.length == 4 &&
      !vParts.contains(null) &&
      (vParts[0] == 10 ||
          (vParts[0] == 192 && vParts[1] == 168) ||
          (vParts[0] == 172 && vParts[1]! >= 16 && vParts[1]! <= 31));

  return rPrivate;
}

/// Retourne le début commun des adresses d'un réseau /24, par exemple 192.168.1.
String getNetworkPrefix(String pAddress) {
  final rPrefix = pAddress.substring(0, pAddress.lastIndexOf('.'));

  return rPrefix;
}

/// Retourne l'hôte d'une adresse d'API, par exemple 192.168.1.80.
String? getHost(String? pAddress) {
  final rHost = pAddress == null ? null : Uri.tryParse(pAddress)?.host;

  return rHost;
}

/// Réseaux privés auxquels le téléphone est relié, en général celui du Wi-Fi.
Future<List<String>> findLocalPrefixes() async {
  final vInterfaces = await NetworkInterface.list(type: InternetAddressType.IPv4);

  final rPrefixes = {
    for (final vInterface in vInterfaces)
      for (final vAddress in vInterface.addresses)
        if (isPrivateAddress(vAddress.address)) getNetworkPrefix(vAddress.address),
  }.toList();

  return rPrefixes;
}

class ServerDiscovery {
  ServerDiscovery({http.Client? pClient, Future<List<String>> Function()? pFindPrefixes})
      : client = pClient ??
            IOClient(
              HttpClient()
                ..connectionTimeout = probeTimeout
                // Le ping est public et ne transmet aucun jeton : tout certificat
                // convient pour reconnaître le serveur. Les appels à l'API, eux,
                // n'acceptent que le certificat épinglé (api_client.dart).
                ..badCertificateCallback = (_, __, ___) => true,
            ),
        findPrefixes = pFindPrefixes ?? findLocalPrefixes;

  final http.Client client;
  final Future<List<String>> Function() findPrefixes;

  /// Indique si un serveur Tremplin répond à cette adresse.
  Future<bool> isServer(String pHost, {String pScheme = 'http'}) async {
    bool rServer;

    try {
      final vResponse = await client
          .get(Uri.parse('$pScheme://$pHost:$serverPort/api/v1/ping'))
          .timeout(probeTimeout);
      final vData = vResponse.statusCode == 200 ? jsonDecode(vResponse.body) : null;

      rServer = vData is Map &&
          vData['application'] == applicationName &&
          vData['api_version'] == apiVersion;
    } on Exception {
      // Personne à cette adresse, ou un autre service : on passe à la suivante.
      rServer = false;
    }

    return rServer;
  }

  /// Retourne l'adresse de l'API du premier serveur trouvé, ou null.
  ///
  /// pKnownHost, l'ancienne adresse, est essayée d'abord : rien n'a peut-être changé.
  ///
  /// pScheme, http ou https, est celui de l'adresse connue.
  Future<String?> discover({String? pKnownHost, String pScheme = 'http'}) async {
    final vHosts = <String>[
      if (pKnownHost != null) pKnownHost,
      for (final vPrefix in await findPrefixes())
        for (var vNumber = 1; vNumber < 255; vNumber++)
          if ('$vPrefix.$vNumber' != pKnownHost) '$vPrefix.$vNumber',
    ];

    String? rAddress;

    for (var vStart = 0; vStart < vHosts.length && rAddress == null; vStart += probeBatch) {
      final vBatch = vHosts.skip(vStart).take(probeBatch).toList();
      final vFound = await Future.wait(
        vBatch.map((vHost) => isServer(vHost, pScheme: pScheme)),
      );
      final vIndex = vFound.indexOf(true);

      if (vIndex >= 0) {
        rAddress = '$pScheme://${vBatch[vIndex]}:$serverPort/api/v1';
      }
    }

    return rAddress;
  }

  /// Échange le code à 6 chiffres affiché par le PC contre le jeton de l'appli.
  ///
  /// La demande passe par le même client que le ping : le certificat n'est pas
  /// encore connu, il arrive dans la réponse avec le jeton.
  Future<ServerSettings> pair(String pAddress, String pCode) async {
    final http.Response vResponse;

    try {
      vResponse = await client
          .post(
            Uri.parse('$pAddress/pairing'),
            headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
            body: jsonEncode({'code': pCode.replaceAll(RegExp(r'\D'), '')}),
          )
          .timeout(pairingTimeout);
    } on Exception {
      throw const ApiException(
        'Le PC ne répond plus : vérifiez que le téléphone est sur le même Wi-Fi.',
        unreachable: true,
      );
    }

    if (vResponse.statusCode == 403) {
      // Le code tapé n'est pas journalisé : il pourrait être presque juste.
      throw const ApiException(
        'Code refusé : affichez un nouveau code sur le PC et recommencez.',
      );
    }

    if (vResponse.statusCode != 200) {
      throw ApiException('Erreur du serveur (${vResponse.statusCode}).');
    }

    final vData = jsonDecode(utf8.decode(vResponse.bodyBytes)) as Map<String, dynamic>;
    final rSettings = ServerSettings(
      address: pAddress,
      token: vData['token'] as String,
      certificateSha256: vData['certificate_sha256'] as String?,
    );

    return rSettings;
  }
}
