// Lecture du QR code de connexion produit par job/mobile_sync.py.

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/services/api_client.dart';
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

  test('L empreinte du certificat est lue et gardée avec la nouvelle adresse', () {
    final vSettings = parseConnectionCode(
      '{"address":"https://192.168.1.80:8000/api/v1","token":"secret",'
      '"certificate_sha256":"AB12"}',
    )!;

    expect(vSettings.certificateSha256, 'AB12');
    expect(vSettings.withAddress('https://192.168.1.81:8000/api/v1').certificateSha256, 'AB12');
  });

  test('Seul le certificat épinglé est accepté', () {
    final vDer = [1, 2, 3, 4];
    final vFingerprint = sha256.convert(vDer).toString();

    expect(isPinnedCertificate(vDer, vFingerprint.toUpperCase()), isTrue);
    expect(isPinnedCertificate([9, 9], vFingerprint), isFalse);
  });
}
