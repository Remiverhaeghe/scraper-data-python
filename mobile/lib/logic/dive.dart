// Univers de la piscine : la maîtrise d'un thème se lit comme une profondeur, une série de
// questions comme un plongeon, et la semaine comme un carnet de plongée.

import 'dart:math' show max, min;

import '../models/quiz_package.dart';
import '../models/review_state.dart';

/// Grand bassin : un thème maîtrisé descend à 3 m.
const poolDepthMetres = 3.0;

/// Repères peints sur le bord du bassin.
const depthMarkers = [1, 2, 3];

/// Boîte la plus haute de la répétition espacée.
const topBox = 5;

/// Profondeur d'un thème : la boîte moyenne de ses questions, une question jamais vue comptant
/// zéro, ramenée de 0 à 3 m.
double themeDepth(List<QuizQuestion> pQuestions, Map<String, ReviewState> pSchedule) {
  if (pQuestions.isEmpty) {
    return 0;
  }
  final vBoxes = pQuestions.fold<int>(
    0,
    (pSum, pQuestion) => pSum + min(max(pSchedule[pQuestion.id]?.box ?? 0, 0), topBox),
  );
  final rDepth = poolDepthMetres * vBoxes / (topBox * pQuestions.length);

  return rDepth;
}

/// Profondeur écrite au décimètre, avec une virgule : « 1,4 m ».
String formatDepth(double pMetres) => '${pMetres.toStringAsFixed(1).replaceAll('.', ',')} m';

/// Bilan d'un plongeon : réponses données, justes, et profondeur avant et après.
typedef DiveResult = ({int answered, int correct, double before, double after});

/// Part de réponses justes, de 0 à 1.
double diveAccuracy(DiveResult pDive) => pDive.answered == 0 ? 0 : pDive.correct / pDive.answered;

/// Façon dont le plongeon s'est passé, pour choisir le message du bilan.
enum DiveVerdict { deeper, steady, shallower, dry }

DiveVerdict diveVerdict(DiveResult pDive) {
  final vChange = pDive.after - pDive.before;
  final rVerdict = pDive.answered == 0
      ? DiveVerdict.dry
      : (vChange >= 0.05
          ? DiveVerdict.deeper
          : (vChange <= -0.05 ? DiveVerdict.shallower : DiveVerdict.steady));

  return rVerdict;
}

/// Jours gardés dans le carnet de plongée : huit semaines.
const diveLogDays = 56;

/// Ajoute une réponse au carnet, rangé par jour (« 2026-11-20 » → [réponses, justes]) ; les jours
/// trop anciens sont retirés.
Map<String, List<int>> logAnswer(Map<String, List<int>> pLog, DateTime pAt, bool pCorrect) {
  final vDay = _dayKey(pAt);
  final vLimit = _dayKey(pAt.subtract(const Duration(days: diveLogDays)));
  final vToday = pLog[vDay] ?? const [0, 0];
  final rLog = {
    for (final vEntry in pLog.entries)
      if (vEntry.key.compareTo(vLimit) > 0) vEntry.key: vEntry.value,
    vDay: [vToday[0] + 1, vToday[1] + (pCorrect ? 1 : 0)],
  };

  return rLog;
}

/// Une journée du carnet.
typedef DiveDay = ({DateTime day, int answered, int correct});

/// Semaine du carnet, du lundi au dimanche de la semaine de [pToday].
typedef DiveWeek = ({
  List<DiveDay> days,
  int answered,
  int correct,
  int activeDays,
  DiveDay? bestDay,
  int previousAnswered,
});

DiveWeek diveWeek(Map<String, List<int>> pLog, DateTime pToday) {
  final vMonday = DateTime(pToday.year, pToday.month, pToday.day - (pToday.weekday - 1));
  DiveDay vDay(DateTime pDay) {
    final vEntry = pLog[_dayKey(pDay)] ?? const [0, 0];

    return (day: pDay, answered: vEntry[0], correct: vEntry[1]);
  }

  final vDays = [for (var vIndex = 0; vIndex < 7; vIndex++) vDay(_addDays(vMonday, vIndex))];
  final vPrevious = [for (var vIndex = 1; vIndex <= 7; vIndex++) vDay(_addDays(vMonday, -vIndex))];
  final vActive = vDays.where((pDay) => pDay.answered > 0).toList();
  final DiveWeek rWeek = (
    days: vDays,
    answered: vDays.fold(0, (pSum, pDay) => pSum + pDay.answered),
    correct: vDays.fold(0, (pSum, pDay) => pSum + pDay.correct),
    activeDays: vActive.length,
    bestDay:
        vActive.isEmpty ? null : vActive.reduce((pA, pB) => pB.answered > pA.answered ? pB : pA),
    previousAnswered: vPrevious.fold(0, (pSum, pDay) => pSum + pDay.answered),
  );

  return rWeek;
}

/// Hauteur relative de chaque jour pour le graphique, de 0 à 1.
List<double> diveBars(DiveWeek pWeek) {
  final vMost = pWeek.days.fold<int>(0, (pMost, pDay) => max(pMost, pDay.answered));

  return [for (final vDay in pWeek.days) vMost == 0 ? 0 : vDay.answered / vMost];
}

// Jours ajoutés au calendrier, sans passer par les heures : le passage à l'heure d'hiver ne
// décale pas la date.
DateTime _addDays(DateTime pDay, int pDays) => DateTime(pDay.year, pDay.month, pDay.day + pDays);

String _dayKey(DateTime pDay) =>
    '${pDay.year.toString().padLeft(4, '0')}-${pDay.month.toString().padLeft(2, '0')}-'
    '${pDay.day.toString().padLeft(2, '0')}';
