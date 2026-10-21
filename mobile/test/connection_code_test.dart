// Lecture du QR code de connexion produit par job/mobile_sync.py.

import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/services/connection_code.dart';

void main() {
  test('Le QR code du PC donne l adresse et le jeton', () {
    final vSettings = parseConnectionCode(
      '{"address":"http://192.168.1.80:8000/api/v1","token":"secret"}',
    );

    expect(vSettings!.address, 'http://192.168.1.80:8000/api/v1');
    expect(vSettings.token, 'secret');
  });

  test('Une adresse sans préfixe d API est complétée', () {
    expect(
      parseConnectionCode('{"address":"192.168.1.80:8000","token":"secret"}')!.address,
      'http://192.168.1.80:8000/api/v1',
    );
  });

  test('Un autre QR code est ignoré', () {
    expect(parseConnectionCode('https://exemple.fr'), isNull);
    expect(parseConnectionCode('{"address":"http://pc","token":""}'), isNull);
    expect(parseConnectionCode('[1, 2]'), isNull);
    expect(parseConnectionCode(null), isNull);
  });
}
