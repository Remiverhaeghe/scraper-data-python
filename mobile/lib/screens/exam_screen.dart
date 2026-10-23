// Examen blanc hors ligne : questions tirées au hasard, chronométrées, notées.
// Les réponses comptent aussi dans la répétition espacée, comme sur le PC.

import 'dart:async';

import 'package:flutter/material.dart';

import '../logic/exam.dart';
import '../logic/grading.dart';
import '../models/quiz_package.dart';
import '../revision_state.dart';
import '../widgets/question_input.dart';
import '../widgets/question_parts.dart';

class ExamScreen extends StatefulWidget {
  const ExamScreen({super.key, required this.state, required this.title, required this.questions});

  final RevisionState state;
  final String title;

  /// Questions parmi lesquelles l'examen est tiré.
  final List<QuizQuestion> questions;

  @override
  State<ExamScreen> createState() => _ExamScreenState();
}

class _ExamScreenState extends State<ExamScreen> {
  late final List<QuizQuestion> questions = drawExam(widget.questions, widget.state.random);
  final startedAt = DateTime.now();
  final wrong = <(QuizQuestion, Grade)>[];

  late final Timer timer;
  int index = 0;
  int correct = 0;
  Object? response;
  Grade? grade;
  ExamResult? result;

  @override
  void initState() {
    super.initState();
    timer = Timer.periodic(const Duration(seconds: 1), (_) => setState(() {}));
  }

  @override
  void dispose() {
    timer.cancel();
    super.dispose();
  }

  int get elapsedSeconds => DateTime.now().difference(startedAt).inSeconds;

  Future<void> validate() async {
    final vMessenger = ScaffoldMessenger.of(context);
    final vQuestion = questions[index];

    try {
      final vGrade = await widget.state.answer(vQuestion, response);

      if (!mounted) {
        return;
      }

      setState(() {
        grade = vGrade;

        if (vGrade.correct) {
          correct++;
        } else {
          wrong.add((vQuestion, vGrade));
        }
      });
    } on UnreadableAnswer catch (vException) {
      vMessenger.showSnackBar(SnackBar(content: Text(vException.message)));
    }
  }

  Future<void> next() async {
    if (index + 1 < questions.length) {
      setState(() {
        index++;
        response = null;
        grade = null;
      });
      return;
    }

    timer.cancel();

    final vResult = ExamResult(
      title: widget.title,
      finishedAt: DateTime.now(),
      correct: correct,
      count: questions.length,
      seconds: elapsedSeconds,
    );

    await widget.state.recordExam(vResult);

    if (mounted) {
      setState(() => result = vResult);
    }
  }

  Widget buildSummary(ExamResult pResult) {
    final vTextTheme = Theme.of(context).textTheme;

    final rSummary = ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('${pResult.score} %', style: vTextTheme.displaySmall),
        Text(
          '${pResult.correct} / ${pResult.count} bonnes réponses en '
          '${pResult.seconds ~/ 60} min ${(pResult.seconds % 60).toString().padLeft(2, '0')} s'
          '${pResult.overtime ? ', au-delà de la durée conseillée' : ''}.',
        ),
        const SizedBox(height: 16),
        if (wrong.isEmpty)
          const Text('Aucune erreur.')
        else ...[
          Text('À revoir', style: vTextTheme.titleMedium),
          for (final (vQuestion, vGrade) in wrong)
            Card(
              child: ListTile(
                title: Text(vQuestion.text),
                subtitle: Text('Réponse : ${vGrade.expected}'),
              ),
            ),
        ],
        const SizedBox(height: 16),
        FilledButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text("Terminer l'examen"),
        ),
      ],
    );

    return rSummary;
  }

  Widget buildQuestion() {
    final vQuestion = questions[index];
    final vGrade = grade;
    final vRemaining = questions.length * secondsPerQuestion - elapsedSeconds;

    final rView = ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          formatCountdown(vRemaining),
          style: TextStyle(
            fontWeight: FontWeight.w600,
            color: vRemaining < 0 ? Theme.of(context).colorScheme.error : null,
          ),
        ),
        const SizedBox(height: 4),
        LinearProgressIndicator(value: (index + 1) / questions.length),
        const SizedBox(height: 12),
        Text(
          'Question ${index + 1} / ${questions.length}',
          style: Theme.of(context).textTheme.labelLarge,
        ),
        const SizedBox(height: 8),
        Text(vQuestion.text, style: Theme.of(context).textTheme.titleMedium),
        if (vQuestion.code != null) ...[
          const SizedBox(height: 12),
          CodeBlock(code: vQuestion.code!),
        ],
        const SizedBox(height: 16),
        QuestionInput(
          key: ValueKey<int>(index),
          question: vQuestion,
          random: widget.state.random,
          enabled: vGrade == null,
          onChanged: (pResponse) => setState(() => response = pResponse),
        ),
        const SizedBox(height: 16),
        if (vGrade == null)
          FilledButton(
            onPressed: response == null ? null : validate,
            child: const Text('Valider'),
          )
        else ...[
          ResultPanel(grade: vGrade, explanation: vQuestion.explanation),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: next,
            icon: const Icon(Icons.arrow_forward),
            label: Text(index + 1 < questions.length ? 'Question suivante' : 'Voir la note'),
          ),
        ],
      ],
    );

    return rView;
  }

  @override
  Widget build(BuildContext context) {
    final vResult = result;

    final rScreen = Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: questions.isEmpty
          ? const Center(child: Text('Aucune question pour cet examen.'))
          : vResult == null
              ? buildQuestion()
              : buildSummary(vResult),
    );

    return rScreen;
  }
}
