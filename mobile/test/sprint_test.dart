import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/logic/review.dart';

void main() {
  test('le temps restant se lit en minutes et secondes, jamais négatif', () {
    expect(formatRemaining(const Duration(minutes: 4, seconds: 5)), '4:05');
    expect(formatRemaining(sprintDuration), '5:00');
    expect(formatRemaining(const Duration(seconds: -3)), '0:00');
  });

  test('le bilan de la révision express compte les réponses justes', () {
    expect(describeSprint(7, 5), 'Temps écoulé : 7 réponse(s), 5 juste(s).');
    expect(describeSprint(0, 0), 'Temps écoulé : aucune réponse cette fois.');
  });
}
