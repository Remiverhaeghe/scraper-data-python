// Entretien oral simulé, réécrit depuis job/oral_interview.py : note d'une réponse
// d'après la grille et le temps mesuré. Questions et règles viennent du PC.

import 'python_compat.dart';

/// Note de durée : 0 trop courte, 1 au-delà du temps, 2 dans le temps.
int rateDuration(int pSeconds, int pDuration, int pMinSeconds) {
  if (pSeconds < pMinSeconds) {
    return 0;
  }

  return pSeconds <= pDuration ? 2 : 1;
}

/// Réponse notée, ou null si une note ou le temps est illisible.
Map<String, dynamic>? gradeOralAnswer(
    Object? pSeconds, int pDuration, Object? pStructure, Object? pExample, int pMinSeconds) {
  final vValid =
      [pStructure, pExample].every((pRating) => pRating is int && pRating >= 0 && pRating <= 2);

  if (!vValid || pSeconds is! num || pSeconds < 0 || pSeconds > 3600) {
    return null;
  }

  final vSeconds = roundHalfEven(pSeconds.toDouble());
  final vDuration = rateDuration(vSeconds, pDuration, pMinSeconds);
  final vTotal = (pStructure as int) + (pExample as int) + vDuration;

  return {
    'seconds': vSeconds,
    'structure': pStructure,
    'example': pExample,
    'duration': vDuration,
    'score': roundHalfEven(100 * vTotal / 6),
  };
}
