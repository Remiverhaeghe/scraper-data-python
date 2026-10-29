// Jeu « Contre la montre » : un maximum de bonnes réponses en 60 secondes, avec
// un multiplicateur qui grandit à chaque série de bonnes réponses enchaînées.

const timeAttackDuration = Duration(seconds: 60);

/// Points d'une bonne réponse sans multiplicateur
const timeAttackBasePoints = 10;

/// Bonnes réponses d'affilée pour gagner un cran, jusqu'à x5
const timeAttackComboStep = 3;
const timeAttackMaxMultiplier = 5;

/// Multiplicateur atteint après pCombo bonnes réponses d'affilée.
int multiplierOf(int pCombo) {
  final rMultiplier = (1 + pCombo ~/ timeAttackComboStep).clamp(1, timeAttackMaxMultiplier);

  return rMultiplier;
}

/// Score d'une partie : points, série en cours et meilleure série.
class TimeAttackScore {
  int points = 0;
  int combo = 0;
  int bestCombo = 0;
  int right = 0;
  int answered = 0;

  int get multiplier => multiplierOf(combo);

  /// Compte une réponse ; retourne les points gagnés, 0 si elle est fausse.
  int record(bool pCorrect) {
    var rPoints = 0;

    answered++;

    if (pCorrect) {
      rPoints = timeAttackBasePoints * multiplier;
      points += rPoints;
      right++;
      combo++;
      bestCombo = combo > bestCombo ? combo : bestCombo;
    } else {
      combo = 0;
    }

    return rPoints;
  }
}

/// Bilan de fin de partie.
String describeTimeAttack(TimeAttackScore pScore, int pBest, bool pRecord) {
  final vRecord = pRecord
      ? 'Nouveau record !'
      : pBest > 0
          ? 'Record à battre : $pBest points.'
          : '';

  final rText = '${pScore.points} points · ${pScore.right} bonne(s) réponse(s) sur '
      '${pScore.answered}, meilleure série ${pScore.bestCombo}. $vRecord';

  return rText.trim();
}
