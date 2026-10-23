// Révision d'un thème : questions à revoir puis nouvelles, correction
// immédiate, réponse gardée pour l'envoi au prochain passage en réseau.

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../logic/grading.dart';
import '../logic/review.dart';
import '../models/quiz_package.dart';
import '../revision_state.dart';
import '../widgets/question_input.dart';
import '../widgets/question_parts.dart';
import 'exam_screen.dart';
import 'guide_screen.dart';

const typeLabels = {
  'qcm': 'QCM',
  'numerique': 'Calcul',
  'ordre': 'Remise en ordre',
  'association': 'Association',
};

class QuestionScreen extends StatefulWidget {
  const QuestionScreen({super.key, required this.state, required this.theme});

  final RevisionState state;
  final QuizTheme theme;

  @override
  State<QuestionScreen> createState() => _QuestionScreenState();
}

class _QuestionScreenState extends State<QuestionScreen> {
  QuizQuestion? question;
  Object? response;
  Grade? grade;

  /// Change à chaque question : la saisie précédente est remise à zéro.
  int round = 0;

  @override
  void initState() {
    super.initState();
    pickNext();
  }

  void pickNext() {
    setState(() {
      question = pickQuestion(
        widget.state.package!.questionsOf(widget.theme.key),
        widget.state.schedule,
        DateTime.now(),
        widget.state.random,
      );
      response = null;
      grade = null;
      round++;
    });
  }

  Future<void> validate() async {
    final vMessenger = ScaffoldMessenger.of(context);

    try {
      final vGrade = await widget.state.answer(question!, response);

      if (widget.state.hapticsEnabled) {
        // Courte si juste, appuyée si faux : la correction se sent sans regarder.
        unawaited(
          vGrade.correct ? HapticFeedback.lightImpact() : HapticFeedback.heavyImpact(),
        );
      }

      if (mounted) {
        setState(() => grade = vGrade);
      }
    } on UnreadableAnswer catch (vException) {
      vMessenger.showSnackBar(SnackBar(content: Text(vException.message)));
    }
  }

  /// Retire la question des tirages après confirmation, puis passe à la suivante.
  Future<void> flag() async {
    final vMessenger = ScaffoldMessenger.of(context);
    final vConfirmed = await showDialog<bool>(
      context: context,
      builder: (pContext) => AlertDialog(
        title: const Text('Signaler cette question ?'),
        content: const Text(
          "Énoncé faux, ambigu ou réponse discutable : elle n'est plus proposée, "
          'et le PC la retire aussi à la prochaine synchronisation.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(pContext).pop(false),
            child: const Text('Annuler'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(pContext).pop(true),
            child: const Text('Signaler'),
          ),
        ],
      ),
    );

    if (vConfirmed != true || !mounted) {
      return;
    }

    await widget.state.flagQuestion(question!.id);
    vMessenger.showSnackBar(const SnackBar(content: Text('Question signalée.')));
    pickNext();
  }

  Widget buildSchema(QuizQuestion pQuestion) {
    final vVisual = pQuestion.visual!;
    final vContent = widget.state.package!.assets[vVisual['asset']];

    final rSchema = vContent == null
        ? const SizedBox.shrink()
        : SchemaView(
            content: vContent,
            description: (vVisual['alt'] as String?) ?? 'Schéma de la question',
          );

    return rSchema;
  }

  Widget buildEmpty() {
    final vNext = nextReview(
      widget.state.package!.questionsOf(widget.theme.key),
      widget.state.schedule,
    );

    final rEmpty = Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.task_alt, size: 48),
            const SizedBox(height: 12),
            Text(
              vNext == null
                  ? 'Aucune question dans ce thème.'
                  : "Rien à revoir aujourd'hui dans ce thème : prochaine révision le "
                      '${vNext.day.toString().padLeft(2, '0')}/'
                      '${vNext.month.toString().padLeft(2, '0')}/${vNext.year}.',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Retour aux thèmes'),
            ),
          ],
        ),
      ),
    );

    return rEmpty;
  }

  Widget buildQuestion(QuizQuestion pQuestion) {
    final vGrade = grade;

    final rView = ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Wrap(
          spacing: 8,
          children: [
            Chip(label: Text(typeLabels[pQuestion.type] ?? pQuestion.type)),
            if (pQuestion.level.isNotEmpty) Chip(label: Text(pQuestion.level)),
          ],
        ),
        const SizedBox(height: 8),
        Text(pQuestion.text, style: Theme.of(context).textTheme.titleMedium),
        if (pQuestion.code != null) ...[
          const SizedBox(height: 12),
          CodeBlock(code: pQuestion.code!),
        ],
        if (pQuestion.visual != null && pQuestion.visualOnQuestion) ...[
          const SizedBox(height: 12),
          buildSchema(pQuestion),
        ],
        const SizedBox(height: 16),
        QuestionInput(
          key: ValueKey<int>(round),
          question: pQuestion,
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
          ResultPanel(grade: vGrade, explanation: pQuestion.explanation),
          if (pQuestion.visual != null && !pQuestion.visualOnQuestion) buildSchema(pQuestion),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: pickNext,
            icon: const Icon(Icons.arrow_forward),
            label: const Text('Question suivante'),
          ),
        ],
      ],
    );

    return rView;
  }

  @override
  Widget build(BuildContext context) {
    final vGuide = widget.state.package!.guides[widget.theme.guide];
    final vQuestion = question;

    final rScreen = Scaffold(
      appBar: AppBar(
        title: Text(widget.theme.label),
        actions: [
          if (vQuestion != null)
            IconButton(
              tooltip: 'Signaler une question fausse ou ambiguë',
              icon: const Icon(Icons.flag_outlined),
              onPressed: flag,
            ),
          IconButton(
            tooltip: 'Examen blanc sur ce thème',
            icon: const Icon(Icons.timer_outlined),
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => ExamScreen(
                  state: widget.state,
                  title: 'Examen : ${widget.theme.label}',
                  questions: widget.state.package!.questionsOf(widget.theme.key),
                ),
              ),
            ),
          ),
          if (vGuide != null)
            IconButton(
              tooltip: 'Guide pratique',
              icon: const Icon(Icons.menu_book_outlined),
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute<void>(builder: (_) => GuideScreen(guide: vGuide)),
              ),
            ),
        ],
      ),
      body: vQuestion == null ? buildEmpty() : buildQuestion(vQuestion),
    );

    return rScreen;
  }
}
