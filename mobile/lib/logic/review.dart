// Répétition espacée hors ligne, identique à build_review_schedule et
// pick_question de job/quiz.py.

import 'dart:math';

import '../models/quiz_package.dart';
import '../models/review_state.dart';

/// Nouvelle place d'une question après une réponse : boîte suivante si elle est
/// juste, retour à la première sinon.
ReviewState applyAnswer(
  ReviewState? pState,
  bool pCorrect,
  DateTime pAnsweredAt,
  List<int> pIntervals,
) {
  final vBox = pCorrect ? min((pState?.box ?? 0) + 1, pIntervals.length) : 1;

  // Ajout en jours du calendrier : un changement d'heure ne décale pas la date.
  final rState = ReviewState(
    box: vBox,
    due: DateTime(
      pAnsweredAt.year,
      pAnsweredAt.month,
      pAnsweredAt.day + pIntervals[vBox - 1],
    ),
    lastCorrect: pCorrect,
  );

  return rState;
}

/// Indique si une question déjà vue est à revoir à cette date.
bool isDue(ReviewState pState, DateTime pToday) {
  final rDue = !pState.due.isAfter(dateOnly(pToday));

  return rDue;
}

/// Choisit une question : d'abord celles à revoir, puis les nouvelles ; null sinon.
QuizQuestion? pickQuestion(
  List<QuizQuestion> pQuestions,
  Map<String, ReviewState> pSchedule,
  DateTime pToday,
  Random pRandom,
) {
  final vDue = [
    for (final vQuestion in pQuestions)
      if (pSchedule[vQuestion.id] != null && isDue(pSchedule[vQuestion.id]!, pToday)) vQuestion,
  ];
  final vCandidates = vDue.isNotEmpty
      ? vDue
      : [
          for (final vQuestion in pQuestions)
            if (!pSchedule.containsKey(vQuestion.id)) vQuestion,
        ];

  final rQuestion = vCandidates.isEmpty ? null : vCandidates[pRandom.nextInt(vCandidates.length)];

  return rQuestion;
}

/// Compte les questions déjà vues et à revoir à cette date.
int countDue(List<QuizQuestion> pQuestions, Map<String, ReviewState> pSchedule, DateTime pToday) {
  final rCount = pQuestions
      .where(
          (vQuestion) => pSchedule[vQuestion.id] != null && isDue(pSchedule[vQuestion.id]!, pToday))
      .length;

  return rCount;
}

/// Compte les questions jamais répondues.
int countNew(List<QuizQuestion> pQuestions, Map<String, ReviewState> pSchedule) {
  final rCount = pQuestions.where((vQuestion) => !pSchedule.containsKey(vQuestion.id)).length;

  return rCount;
}

/// Retourne la prochaine date de révision d'un thème, ou null.
DateTime? nextReview(List<QuizQuestion> pQuestions, Map<String, ReviewState> pSchedule) {
  DateTime? rDate;

  for (final vQuestion in pQuestions) {
    final vDue = pSchedule[vQuestion.id]?.due;

    if (vDue != null && (rDate == null || vDue.isBefore(rDate))) {
      rDate = vDue;
    }
  }

  return rDate;
}

/// Durée de la révision express, pour les temps morts de la journée.
const sprintDuration = Duration(minutes: 5);

/// Retourne le temps restant au format « 4:05 », jamais négatif.
String formatRemaining(Duration pRemaining) {
  final vSeconds = pRemaining.isNegative ? 0 : pRemaining.inSeconds;

  final rText = '${vSeconds ~/ 60}:${(vSeconds % 60).toString().padLeft(2, '0')}';

  return rText;
}

/// Résume une révision express terminée.
String describeSprint(int pAnswered, int pCorrect) {
  final rText = pAnswered == 0
      ? 'Temps écoulé : aucune réponse cette fois.'
      : 'Temps écoulé : $pAnswered réponse(s), $pCorrect juste(s).';

  return rText;
}

/// Mélange les indices 0 à pCount - 1 ; une remise en ordre ne part jamais
/// déjà dans l'ordre, sinon il n'y aurait rien à faire.
List<int> shuffledIndexes(int pCount, Random pRandom, {bool pAvoidIdentity = false}) {
  final rIndexes = List.generate(pCount, (vIndex) => vIndex)..shuffle(pRandom);

  if (pAvoidIdentity &&
      pCount > 1 &&
      rIndexes.asMap().entries.every((vEntry) => vEntry.key == vEntry.value)) {
    rIndexes.setAll(0, rIndexes.reversed.toList());
  }

  return rIndexes;
}
