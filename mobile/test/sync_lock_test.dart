// Verrou de synchronisation entre l'application et la tâche d'arrière-plan.

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/services/api_client.dart';
import 'package:jobboard_revision/services/file_store.dart';
import 'package:jobboard_revision/services/revision_store.dart';

import 'support/sample_data.dart';

void main() {
  test('Le verrou est exclusif, puis repris quand il est trop ancien', () async {
    final vDirectory = await Directory.systemTemp.createTemp('verrou');
    final vFile = File('${vDirectory.path}/sync.lock');

    expect(await acquireLockFile(vFile), isTrue);
    expect(await acquireLockFile(vFile), isFalse);
    expect(
      await acquireLockFile(vFile, pNow: DateTime.now().add(const Duration(minutes: 10))),
      isTrue,
    );

    await vDirectory.delete(recursive: true);
  });

  test('Une synchronisation déjà en cours est refusée, sans bloquer la suivante', () async {
    final vStore = MemoryRevisionStore()
      ..settings = const ServerSettings(address: 'http://pc/api/v1', token: 'secret')
      ..package = jsonEncode(buildPackageJson())
      ..progress = buildProgressJson();
    final vState = RevisionState(vStore);

    await vState.load();
    await vStore.acquireSyncLock();

    await expectLater(
      vState.synchronize(),
      throwsA(isA<ApiException>().having((e) => e.message, 'message', contains('en cours'))),
    );

    await vStore.releaseSyncLock();

    expect(await vStore.acquireSyncLock(), isTrue);
  });
}
