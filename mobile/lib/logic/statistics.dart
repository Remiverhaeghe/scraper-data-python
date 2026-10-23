// Statistiques de révision : réussite par thème, calculée sur le téléphone, et
// activité des derniers jours, reçue du serveur à la synchronisation.

import '../models/quiz_package.dart';
import '../models/review_state.dart';
import 'review.dart';

/// Avancement d'un thème : questions acquises (dernière réponse juste) et à revoir.
class ThemeStatistics {
  const ThemeStatistics({
    required this.label,
    required this.total,
    required this.answered,
    required this.acquired,
    required this.due,
  });

  final String label;
  final int total;
  final int answered;
  final int acquired;
  final int due;

  /// Part des questions acquises, de 0 à 1.
  double get share => total == 0 ? 0 : acquired / total;
}

/// Activité d'un jour : réponses données et réponses justes.
class DayActivity {
  const DayActivity({required this.date, required this.answers, required this.correct});

  factory DayActivity.fromJson(Map<String, dynamic> pJson) {
    final rActivity = DayActivity(
      date: DateTime.parse(pJson['date'] as String),
      answers: (pJson['answers'] as num).toInt(),
      correct: (pJson['correct'] as num).toInt(),
    );

    return rActivity;
  }

  final DateTime date;
  final int answers;
  final int correct;
}

/// Retourne l'avancement de chaque thème, les moins acquis en premier.
List<ThemeStatistics> buildThemeStatistics(
  QuizPackage pPackage,
  Map<String, ReviewState> pSchedule,
  DateTime pToday,
) {
  final rStatistics = [
    for (final vTheme in pPackage.themes)
      () {
        final vQuestions = pPackage.questionsOf(vTheme.key);
        final vStates = [
          for (final vQuestion in vQuestions)
            if (pSchedule[vQuestion.id] != null) pSchedule[vQuestion.id]!,
        ];

        return ThemeStatistics(
          label: vTheme.label,
          total: vQuestions.length,
          answered: vStates.length,
          acquired: vStates.where((vState) => vState.lastCorrect == true).length,
          due: countDue(vQuestions, pSchedule, pToday),
        );
      }(),
  ]..sort((pFirst, pSecond) => pFirst.share.compareTo(pSecond.share));

  return rStatistics;
}

/// Lit l'activité des derniers jours dans les statistiques reçues du serveur.
List<DayActivity> readDayActivity(Map<String, dynamic> pStatistics) {
  final rDays = [
    for (final vDay in pStatistics['days'] as List? ?? const [])
      DayActivity.fromJson(Map<String, dynamic>.from(vDay as Map)),
  ];

  return rDays;
}
