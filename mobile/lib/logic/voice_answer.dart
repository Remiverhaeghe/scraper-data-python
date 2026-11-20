// Révision à la voix : retrouver le choix d'un QCM dans ce que le téléphone a entendu.

/// Lettres des choix, dites et affichées.
const choiceLetters = ['A', 'B', 'C', 'D', 'E', 'F'];

const _ordinals = {
  'un': 0, 'une': 0, '1': 0, 'premier': 0, 'premiere': 0,
  'deux': 1, '2': 1, 'deuxieme': 1, 'second': 1, 'seconde': 1,
  'trois': 2, '3': 2, 'troisieme': 2,
  'quatre': 3, '4': 3, 'quatrieme': 3,
  'cinq': 4, '5': 4, 'cinquieme': 4,
  'six': 5, '6': 5, 'sixieme': 5,
};

/// Lettres telles que la reconnaissance vocale les écrit souvent : « b » devient « bé ».
const _letterSounds = {
  'a': 0, 'ah': 0,
  'b': 1, 'be': 1, 'bee': 1,
  'c': 2, 'ce': 2, 'ces': 2, 'cest': 2,
  'd': 3, 'de': 3, 'des': 3,
  'e': 4, 'euh': 4,
  'f': 5, 'effe': 5,
};

/// Mots qui annoncent un choix sans en être un : « réponse B », « la deux ».
const _fillers = {'reponse', 'la', 'le', 'lettre', 'choix', 'numero', 'cest', 'je', 'dis', 'pense'};

String _fold(String pText) {
  const vFrom = 'àâäéèêëîïôöùûüç';
  const vTo = 'aaaeeeeiioouuuc';
  final vBuffer = StringBuffer();
  for (final vChar in pText.toLowerCase().split('')) {
    final vIndex = vFrom.indexOf(vChar);
    vBuffer.write(vIndex < 0 ? vChar : vTo[vIndex]);
  }

  return vBuffer.toString().replaceAll(RegExp(r"[^a-z0-9 ]"), ' ');
}

List<String> _words(String pText) =>
    _fold(pText).split(' ').where((pWord) => pWord.isNotEmpty).toList();

/// Indice du choix entendu dans une des propositions de la reconnaissance, ou null.
///
/// Une phrase courte peut donner la lettre (« B », « réponse C ») ou le rang (« la deux ») ; une
/// phrase plus longue est comparée au texte des choix, mot à mot.
int? matchSpokenChoice(List<String> pHeard, List<String> pChoices) {
  for (final vHeard in pHeard) {
    final vWords = _words(vHeard).where((pWord) => !_fillers.contains(pWord)).toList();
    if (vWords.isEmpty) {
      continue;
    }
    if (vWords.length <= 2) {
      for (final vWord in vWords.reversed) {
        final vIndex = _ordinals[vWord] ?? _letterSounds[vWord];
        if (vIndex != null && vIndex < pChoices.length) {
          return vIndex;
        }
      }
    }
    final vText = byText(vWords.toSet(), pChoices);
    if (vText != null) {
      return vText;
    }
  }

  return null;
}

/// Choix dont au moins deux tiers des mots de plus de deux lettres ont été entendus ; le
/// mieux couvert gagne, une égalité ne décide rien.
int? byText(Set<String> pHeard, List<String> pChoices) {
  int? rBest;
  var vBestScore = 0.0;
  var vTie = false;
  for (final (vIndex, vChoice) in pChoices.indexed) {
    final vWords = _words(vChoice).where((pWord) => pWord.length > 2).toSet();
    if (vWords.isEmpty) {
      continue;
    }
    final vScore = vWords.where(pHeard.contains).length / vWords.length;
    if (vScore >= 2 / 3 && vScore > vBestScore) {
      rBest = vIndex;
      vBestScore = vScore;
      vTie = false;
    } else if (vScore >= 2 / 3 && vScore == vBestScore) {
      vTie = true;
    }
  }

  return vTie ? null : rBest;
}
