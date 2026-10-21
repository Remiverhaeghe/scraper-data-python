// Recherche du serveur sur le Wi-Fi, avec un réseau simulé.

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/services/api_client.dart';
import 'package:jobboard_revision/services/discovery.dart';
import 'package:jobboard_revision/services/revision_store.dart';

import 'support/sample_data.dart';

/// Réseau simulé : seul le PC à l'adresse pHost répond comme serveur JobBoard.
MockClient buildNetwork(String pHost, {List<String>? pVisited}) {
  final rClient = MockClient((pRequest) async {
    pVisited?.add(pRequest.url.host);

    final http.Response rResponse;

    if (pRequest.url.host != pHost) {
      throw http.ClientException('Aucun appareil');
    } else if (pRequest.url.path.endsWith('/ping')) {
      rResponse = http.Response(
        jsonEncode({'application': 'JobBoard Perso', 'api_version': 1}),
        200,
      );
    } else if (pRequest.url.path.endsWith('/progress')) {
      rResponse = http.Response(jsonEncode(buildProgressJson()), 200);
    } else {
      rResponse = http.Response('', 304);
    }

    return rResponse;
  });

  return rClient;
}

void main() {
  test('Adresses privées et réseau à parcourir', () {
    expect(isPrivateAddress('192.168.1.80'), isTrue);
    expect(isPrivateAddress('10.0.0.4'), isTrue);
    expect(isPrivateAddress('172.20.1.1'), isTrue);
    expect(isPrivateAddress('172.32.1.1'), isFalse);
    expect(isPrivateAddress('8.8.8.8'), isFalse);
    expect(getNetworkPrefix('192.168.1.80'), '192.168.1');
    expect(getHost('http://192.168.1.80:8000/api/v1'), '192.168.1.80');
  });

  test('Le serveur est trouvé sur le réseau, l ancienne adresse essayée d abord', () async {
    final vVisited = <String>[];
    final vDiscovery = ServerDiscovery(
      pClient: buildNetwork('192.168.1.80', pVisited: vVisited),
      pFindPrefixes: () async => ['192.168.1'],
    );

    expect(
      await vDiscovery.discover(pKnownHost: '192.168.1.50'),
      'http://192.168.1.80:8000/api/v1',
    );
    expect(vVisited.first, '192.168.1.50');
    expect(await vDiscovery.discover(pKnownHost: '192.168.1.80'), isNotNull);
  });

  test('Un autre service web n est pas pris pour le serveur', () async {
    final vDiscovery = ServerDiscovery(
      pClient: MockClient((_) async => http.Response('<html></html>', 200)),
      pFindPrefixes: () async => ['10.0.0'],
    );

    expect(await vDiscovery.discover(), isNull);
  });

  test('Adresse changée : le serveur est retrouvé et la synchronisation réussit', () async {
    final vNetwork = buildNetwork('192.168.1.80');
    final vStore = MemoryRevisionStore()
      ..settings = const ServerSettings(
        address: 'http://192.168.1.50:8000/api/v1',
        token: 'secret',
      )
      ..package = jsonEncode(buildPackageJson())
      ..progress = buildProgressJson();
    final vState = RevisionState(
      vStore,
      pClientFactory: (pSettings) => ApiClient(pSettings, pClient: vNetwork),
      pDiscovery: ServerDiscovery(pClient: vNetwork, pFindPrefixes: () async => ['192.168.1']),
    );

    await vState.load();

    final vReport = await vState.synchronizeOrRelocate();

    expect(vReport.contentUpdated, isFalse);
    expect(vState.settings!.address, 'http://192.168.1.80:8000/api/v1');
    expect(vStore.settings!.token, 'secret');
  });

  test('Serveur introuvable : l erreur d origine est conservée', () async {
    final vNetwork = buildNetwork('aucun');
    final vState = RevisionState(
      MemoryRevisionStore()
        ..settings = const ServerSettings(
          address: 'http://192.168.1.50:8000/api/v1',
          token: 'secret',
        ),
      pClientFactory: (pSettings) => ApiClient(pSettings, pClient: vNetwork),
      pDiscovery: ServerDiscovery(pClient: vNetwork, pFindPrefixes: () async => ['192.168.1']),
    );

    await vState.load();

    await expectLater(
      vState.synchronizeOrRelocate(),
      throwsA(isA<ApiException>().having((vError) => vError.unreachable, 'unreachable', isTrue)),
    );
    expect(vState.settings!.address, 'http://192.168.1.50:8000/api/v1');
  });
}
