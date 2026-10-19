// Correction locale : mêmes résultats que job/quiz_types.py sur le serveur.

import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/logic/grading.dart';
import 'package:jobboard_revision/models/quiz_package.dart';

import 'support/sample_data.dart';

QuizQuestion findQuestion(String pId) {
  final vPackage = QuizPackage.fromJson(buildPackageJson());

  final rQuestion = vPackage.questions.firstWhere((vQuestion) => vQuestion.id == pId);

  return rQuestion;
}

void main() {
  test('QCM : indice du choix, juste ou non', () {
    final vQuestion = findQuestion('docker-image');

    expect(gradeAnswer(vQuestion, 1).correct, isTrue);
    expect(gradeAnswer(vQuestion, 0).correct, isFalse);
    expect(gradeAnswer(vQuestion, 0).expected, "L'image est le modèle");
    expect(() => gradeAnswer(vQuestion, 9), throwsA(isA<UnreadableAnswer>()));
  });

  test('Calcul : unité, préfixe et tolérance', () {
    final vQuestion = findQuestion('ohm-courant');

    expect(gradeAnswer(vQuestion, '2,3 mA').correct, isTrue);
    expect(gradeAnswer(vQuestion, '0.00231').correct, isTrue);
    expect(gradeAnswer(vQuestion, '0,003 A').correct, isFalse);
    expect(gradeAnswer(vQuestion, '2,3 mA').expected, '0,0023 A');
    expect(() => gradeAnswer(vQuestion, '2,3 V'), throwsA(isA<UnreadableAnswer>()));
    expect(() => gradeAnswer(vQuestion, 'beaucoup'), throwsA(isA<UnreadableAnswer>()));
  });

  test('Remise en ordre : indices d origine dans l ordre choisi', () {
    final vQuestion = findQuestion('consignation');

    expect(gradeAnswer(vQuestion, [0, 1, 2, 3]).correct, isTrue);
    expect(gradeAnswer(vQuestion, [1, 0, 2, 3]).correct, isFalse);
    expect(() => gradeAnswer(vQuestion, [0, 0, 1, 2]), throwsA(isA<UnreadableAnswer>()));
    expect(() => gradeAnswer(vQuestion, [0, 1]), throwsA(isA<UnreadableAnswer>()));
  });

  test('Association : correspondance choisie pour chaque élément', () {
    final vQuestion = findQuestion('unites');

    expect(gradeAnswer(vQuestion, [0, 1]).correct, isTrue);
    expect(gradeAnswer(vQuestion, [1, 0]).given, 'Tension → A ; Courant → V');
  });

  test('Nombres écrits à la française, comme %.6g', () {
    expect(formatNumber(0.0023), '0,0023');
    expect(formatNumber(12.5), '12,5');
    expect(formatNumber(1500000), '1,5e+06');
    expect(formatNumber(0), '0');
  });
}
