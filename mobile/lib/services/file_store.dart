// Stockage sur le téléphone : fichiers JSON dans le dossier de l'application,
// jeton dans le stockage chiffré du système.

import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:path_provider/path_provider.dart';

import 'revision_store.dart';

const addressKey = 'server_address';
const tokenKey = 'api_token';
const certificateKey = 'certificate_sha256';

const packageFile = 'package.json';
const progressFile = 'progress.json';
const pendingFile = 'pending.json';
const examsFile = 'exams.json';
const preferencesFile = 'preferences.json';
const offersFile = 'offers.json';
const syncLockFile = 'sync.lock';

/// Au-delà, le verrou vient d'une synchronisation interrompue (application
/// arrêtée net) : il est repris.
const staleSyncLock = Duration(minutes: 5);

/// Crée le fichier de verrou de façon exclusive ; retourne s'il est obtenu.
///
/// La création exclusive est atomique, même entre l'application et la tâche
/// d'arrière-plan qui tournent dans le même processus Android, où les verrous
/// de fichier classiques ne s'excluent pas.
Future<bool> acquireLockFile(File pFile, {DateTime? pNow}) async {
  var rAcquired = false;

  try {
    await pFile.create(exclusive: true);
    rAcquired = true;
  } on FileSystemException {
    try {
      final vAge = (pNow ?? DateTime.now()).difference(await pFile.lastModified());

      if (vAge > staleSyncLock) {
        await pFile.delete();
        await pFile.create(exclusive: true);
        rAcquired = true;
      }
    } on FileSystemException {
      // Repris entre-temps par l'autre synchronisation : elle garde la main.
      rAcquired = false;
    }
  }

  return rAcquired;
}

class FileRevisionStore implements RevisionStore {
  FileRevisionStore({FlutterSecureStorage? pSecureStorage})
      : secureStorage = pSecureStorage ?? const FlutterSecureStorage();

  final FlutterSecureStorage secureStorage;

  Future<File> getFile(String pName) async {
    final vDirectory = await getApplicationDocumentsDirectory();

    final rFile = File('${vDirectory.path}/$pName');

    return rFile;
  }

  Future<String?> readText(String pName) async {
    final vFile = await getFile(pName);

    final rText = await vFile.exists() ? await vFile.readAsString() : null;

    return rText;
  }

  /// Écrit dans un fichier temporaire puis le renomme : une coupure pendant
  /// l'écriture ne laisse jamais de fichier à moitié écrit.
  Future<void> writeText(String pName, String pText) async {
    final vFile = await getFile(pName);
    final vTemporary = File('${vFile.path}.tmp');

    await vTemporary.writeAsString(pText, flush: true);
    await vTemporary.rename(vFile.path);
  }

  @override
  Future<ServerSettings?> loadSettings() async {
    final vAddress = await secureStorage.read(key: addressKey);
    final vToken = await secureStorage.read(key: tokenKey);
    final vCertificate = await secureStorage.read(key: certificateKey);

    final rSettings = vAddress == null || vToken == null
        ? null
        : ServerSettings(address: vAddress, token: vToken, certificateSha256: vCertificate);

    return rSettings;
  }

  @override
  Future<void> saveSettings(ServerSettings pSettings) async {
    await secureStorage.write(key: addressKey, value: pSettings.address);
    await secureStorage.write(key: tokenKey, value: pSettings.token);

    if (pSettings.certificateSha256 == null) {
      await secureStorage.delete(key: certificateKey);
    } else {
      await secureStorage.write(key: certificateKey, value: pSettings.certificateSha256);
    }
  }

  @override
  Future<String?> loadPackage() => readText(packageFile);

  @override
  Future<void> savePackage(String pContent) => writeText(packageFile, pContent);

  @override
  Future<Map<String, dynamic>?> loadProgress() async {
    final vText = await readText(progressFile);

    final rProgress = vText == null ? null : jsonDecode(vText) as Map<String, dynamic>;

    return rProgress;
  }

  @override
  Future<void> saveProgress(Map<String, dynamic> pProgress) =>
      writeText(progressFile, jsonEncode(pProgress));

  Future<List<Map<String, dynamic>>> readList(String pName) async {
    final vText = await readText(pName);

    final rItems = vText == null
        ? <Map<String, dynamic>>[]
        : [
            for (final vItem in jsonDecode(vText) as List) Map<String, dynamic>.from(vItem as Map),
          ];

    return rItems;
  }

  @override
  Future<List<Map<String, dynamic>>> loadPending() => readList(pendingFile);

  @override
  Future<void> savePending(List<Map<String, dynamic>> pAnswers) =>
      writeText(pendingFile, jsonEncode(pAnswers));

  @override
  Future<List<Map<String, dynamic>>> loadExamResults() => readList(examsFile);

  @override
  Future<void> saveExamResults(List<Map<String, dynamic>> pResults) =>
      writeText(examsFile, jsonEncode(pResults));

  @override
  Future<List<Map<String, dynamic>>> loadOffers() => readList(offersFile);

  @override
  Future<void> saveOffers(List<Map<String, dynamic>> pOffers) =>
      writeText(offersFile, jsonEncode(pOffers));

  @override
  Future<Map<String, dynamic>> loadPreferences() async {
    final vText = await readText(preferencesFile);

    final rPreferences =
        vText == null ? <String, dynamic>{} : jsonDecode(vText) as Map<String, dynamic>;

    return rPreferences;
  }

  @override
  Future<void> savePreferences(Map<String, dynamic> pPreferences) =>
      writeText(preferencesFile, jsonEncode(pPreferences));

  @override
  Future<bool> acquireSyncLock() async => acquireLockFile(await getFile(syncLockFile));

  @override
  Future<void> releaseSyncLock() async {
    final vFile = await getFile(syncLockFile);

    if (await vFile.exists()) {
      await vFile.delete();
    }
  }
}
