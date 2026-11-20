// Révision sans le PC : paquet livré avec l'application, installé au premier lancement.

import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jobboard_revision/models/quiz_package.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/screens/connect_screen.dart';
import 'package:jobboard_revision/services/discovery.dart';
import 'package:jobboard_revision/services/starter_package.dart';

import 'support/sample_data.dart';

/// Fichiers livrés simulés : le paquet compressé de l'exemple.
class SampleBundle extends CachingAssetBundle {
  @override
  Future<ByteData> load(String pKey) async => ByteData.sublistView(
        Uint8List.fromList(gzip.encode(utf8.encode(jsonEncode(buildPackageJson())))),
      );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('Le paquet livré se lit et contient des questions', () async {
    final vPackage = QuizPackage.fromJson(
      jsonDecode(await loadStarterPackage()) as Map<String, dynamic>,
    );

    expect(vPackage.themes, isNotEmpty);
    expect(vPackage.questions, isNotEmpty);
  });

  testWidgets('Premier lancement : « Réviser sans le PC » installe le paquet livré', (
    pTester,
  ) async {
    final vNetwork = MockClient((_) async => throw http.ClientException('Aucun appareil'));
    final vStore = MemoryRevisionStore();
    final vState = RevisionState(
      vStore,
      pDiscovery: ServerDiscovery(pClient: vNetwork, pFindPrefixes: () async => []),
    );
    await vState.load();

    await pTester.pumpWidget(
      MaterialApp(home: ConnectScreen(state: vState, bundle: SampleBundle())),
    );
    await pTester.pumpAndSettle();
    await pTester.tap(find.text('Réviser sans le PC'));
    await pTester.pumpAndSettle();

    expect(vState.package, isNotNull);
    expect(vState.settings, isNull);
    expect(vStore.package, isNotNull);
  });
}
