// Lecture à voix haute par le moteur vocal d'Android (MainActivity.kt), sans
// paquet ajouté. Sans moteur, ou dans les tests, la lecture rend la main aussitôt.

import 'package:flutter/services.dart';

class Speech {
  const Speech();

  static const _channel = MethodChannel('fr.jobboard/speech');

  /// Lit pText ; répond vrai une fois la phrase dite jusqu'au bout.
  Future<bool> speak(String pText) async {
    try {
      return await _channel.invokeMethod<bool>('speak', {'text': pText}) ?? false;
    } on MissingPluginException {
      return false;
    } on PlatformException {
      return false;
    }
  }

  /// Ouvre la reconnaissance vocale du téléphone ; répond par les phrases comprises, de la
  /// plus probable à la moins probable, ou rien si personne n'a parlé.
  Future<List<String>> listen() async {
    try {
      final vHeard = await _channel.invokeMethod<List<Object?>>('listen');

      return [for (final vItem in vHeard ?? const []) '$vItem'];
    } on MissingPluginException {
      return const [];
    } on PlatformException {
      return const [];
    }
  }

  Future<void> stop() async {
    try {
      await _channel.invokeMethod<void>('stop');
    } on MissingPluginException {
      return;
    } on PlatformException {
      return;
    }
  }
}
