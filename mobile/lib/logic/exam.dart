// Examen blanc hors ligne : tirage des questions, durée conseillée et note,
// comme job/quiz_exam.py sur le serveur.

import 'dart:math';

import '../models/quiz_package.dart';

/// Questions d'un examen, au plus.
const examQuestionCount = 20;

/// Durée conseillée : une minute par question.
const secondsPerQuestion = 60;

/// Résultats d'examen gardés sur le téléphone, les plus récents d'abord.
const maxExamResults = 50;

/// Résultat d'un examen terminé.
class ExamResult {
  const ExamResult({
    required this.title,
    required this.finishedAt,
    required this.correct,
    required this.count,
    required this.seconds,
  });

  factory ExamResult.fromJson(Map<String, dynamic> pJson) {
    final rResult = ExamResult(
      title: pJson['title'] as String,
      finishedAt: DateTime.parse(pJson['finished_at'] as String),
      correct: (pJson['correct'] as num).toInt(),
      count: (pJson['count'] as num).toInt(),
      seconds: (pJson['seconds'] as num).toInt(),
    );

    return rResult;
  }

  final String title;
  final DateTime finishedAt;
  final int correct;
  final int count;
  final int seconds;

  int get score => count == 0 ? 0 : (100 * correct / count).round();

  /// Vrai si l'examen a dépassé la durée conseillée.
  bool get overtime => seconds > count * secondsPerQuestion;

  Map<String, dynamic> toJson() {
    final rJson = {
      'title': title,
      'finished_at': finishedAt.toIso8601String().split('.').first,
      'correct': correct,
      'count': count,
      'seconds': seconds,
    };

    return rJson;
  }
}

/// Tire au hasard les questions d'un examen, sans doublon.
List<QuizQuestion> drawExam(
  List<QuizQuestion> pQuestions,
  Random pRandom, {
  int pCount = examQuestionCount,
}) {
  final rQuestions = ([...pQuestions]..shuffle(pRandom)).take(pCount).toList();

  return rQuestions;
}

/// Décrit le temps restant, ou le dépassement, en minutes et secondes.
String formatCountdown(int pRemainingSeconds) {
  final vSeconds = pRemainingSeconds.abs();
  final vText = '${(vSeconds ~/ 60).toString().padLeft(2, '0')}:'
      '${(vSeconds % 60).toString().padLeft(2, '0')}';

  final rText =
      pRemainingSeconds >= 0 ? 'Temps restant : $vText' : 'Temps dépassé de $vText';

  return rText;
}
