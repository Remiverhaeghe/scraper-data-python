// Connexion au PC par le code à 6 chiffres, avec un réseau simulé.

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/screens/connect_screen.dart';
import 'package:jobboard_revision/services/api_client.dart';
import 'package:jobboard_revision/services/discovery.dart';
import 'package:jobboard_revision/services/revision_store.dart';

import 'support/sample_data.dart';

/// PC fictif à 192.168.1.80 : il répond au ping et n'accepte que le code 482913.
MockClient buildPc({List<String>? pCodes}) => MockClient((pRequest) async {
      final http.Response rResponse;

      if (pRequest.url.host != '192.168.1.80') {
        throw http.ClientException('Aucun appareil');
      } else if (pRequest.url.path.endsWith('/ping')) {
        rResponse =
            http.Response(jsonEncode({'application': 'JobBoard Perso', 'api_version': 1}), 200);
      } else if (pRequest.url.path.endsWith('/pairing')) {
        final vCode = (jsonDecode(pRequest.body) as Map)['code'] as String;
        pCodes?.add(vCode);
        rResponse = vCode == '482913'
            ? http.Response(jsonEncode({'token': 'jeton-du-pc', 'certificate_sha256': null}), 200)
            : http.Response('{}', 403);
      } else if (pRequest.url.path.endsWith('/progress')) {
        rResponse = http.Response(jsonEncode(buildProgressJson()), 200);
      } else {
        rResponse = http.Response('', 304);
      }

      return rResponse;
    });

void main() {
  test('Le code est échangé contre le jeton, chiffres seuls', () async {
    final vCodes = <String>[];
    final vDiscovery =
        ServerDiscovery(pClient: buildPc(pCodes: vCodes), pFindPrefixes: () async => []);

    final vSettings = await vDiscovery.pair('http://192.168.1.80:8000/api/v1', '482 913');

    expect(vSettings.token, 'jeton-du-pc');
    expect(vSettings.address, 'http://192.168.1.80:8000/api/v1');
    expect(vCodes, ['482913']);
    await expectLater(
      vDiscovery.pair('http://192.168.1.80:8000/api/v1', '111111'),
      throwsA(isA<ApiException>()
          .having((pError) => pError.message, 'message', contains('Code refusé'))),
    );
  });

  testWidgets('Le PC est trouvé tout seul, six chiffres tapés suffisent', (pTester) async {
    final vPc = buildPc();
    final vStore = MemoryRevisionStore()..package = jsonEncode(buildPackageJson());
    final vState = RevisionState(
      vStore,
      pClientFactory: (pSettings) => ApiClient(pSettings, pClient: vPc),
      pDiscovery: ServerDiscovery(pClient: vPc, pFindPrefixes: () async => ['192.168.1']),
    );
    await vState.load();

    await pTester.pumpWidget(MaterialApp(home: ConnectScreen(state: vState)));
    await pTester.pumpAndSettle();

    expect(find.text('PC trouvé'), findsOneWidget);
    expect(find.text('192.168.1.80'), findsOneWidget);

    await pTester.enterText(find.widgetWithText(TextField, 'Code à 6 chiffres'), '482 913');
    await pTester.pumpAndSettle();

    expect(vStore.settings!.token, 'jeton-du-pc');
    expect(find.text('Réviser'), findsWidgets);
  });

  testWidgets('PC introuvable : le QR code reste proposé', (pTester) async {
    final vNetwork = MockClient((_) async => throw http.ClientException('Aucun appareil'));
    final vState = RevisionState(
      MemoryRevisionStore(),
      pDiscovery: ServerDiscovery(pClient: vNetwork, pFindPrefixes: () async => ['10.0.0']),
    );
    await vState.load();

    await pTester.pumpWidget(MaterialApp(home: ConnectScreen(state: vState)));
    await pTester.pumpAndSettle();

    expect(find.text('PC introuvable sur ce Wi-Fi'), findsOneWidget);
    expect(find.text('Scanner le QR code du PC'), findsOneWidget);
    expect(find.widgetWithText(TextField, 'Code à 6 chiffres'), findsNothing);
  });
}
