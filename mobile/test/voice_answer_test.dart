// Choix d'un QCM reconnu dans ce que le téléphone a entendu.

import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/logic/voice_answer.dart';

const choices = ['Aucune', "L'image est le modèle", 'Le conteneur est sur Docker Hub'];

void main() {
  test('La lettre ou le rang suffit dans une phrase courte', () {
    expect(matchSpokenChoice(['B'], choices), 1);
    expect(matchSpokenChoice(['réponse C'], choices), 2);
    expect(matchSpokenChoice(['la deux'], choices), 1);
    expect(matchSpokenChoice(['bé'], choices), 1);
    expect(matchSpokenChoice(['première'], choices), 0);
    expect(matchSpokenChoice(['D'], choices), isNull);
    expect(matchSpokenChoice(['', '  '], choices), isNull);
  });

  test('Une phrase longue est comparée au texte des choix', () {
    expect(matchSpokenChoice(["je pense que l'image est le modèle"], choices), 1);
    expect(matchSpokenChoice(['le conteneur est sur docker hub'], choices), 2);
    expect(matchSpokenChoice(['aucune idée vraiment pas du tout'], choices), 0);
    expect(matchSpokenChoice(['il fait beau aujourd hui'], choices), isNull);
  });

  test('La première proposition comprise l emporte, une égalité ne décide rien', () {
    expect(matchSpokenChoice(['il fait beau', 'C'], choices), 2);
    expect(byText({'rouge', 'vert'}, ['rouge vif', 'vert vif']), isNull);
    expect(byText({'rouge'}, ['', 'rouge']), 1);
  });
}
