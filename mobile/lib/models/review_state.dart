// État de révision d'une question : boîte de Leitner et prochaine date.

/// Retourne la date seule, sans l'heure.
DateTime dateOnly(DateTime pDate) {
  final rDate = DateTime(pDate.year, pDate.month, pDate.day);

  return rDate;
}

/// Place d'une question dans la répétition espacée.
class ReviewState {
  const ReviewState({required this.box, required this.due, this.lastCorrect});

  /// Lit l'état envoyé par le serveur dans la progression.
  factory ReviewState.fromJson(Map<String, dynamic> pJson) {
    final rState = ReviewState(
      box: (pJson['box'] as num).toInt(),
      due: DateTime.parse(pJson['due'] as String),
      lastCorrect: pJson['last_correct'] as bool?,
    );

    return rState;
  }

  /// Boîte de 1 à 5 : plus elle est haute, plus la révision est espacée.
  final int box;

  /// Jour à partir duquel la question est de nouveau proposée.
  final DateTime due;

  /// Résultat de la dernière réponse, null si elle est inconnue.
  final bool? lastCorrect;
}
