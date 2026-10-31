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
