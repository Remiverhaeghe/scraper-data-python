// Jeu « Contre la montre » : QCM enchaînés pendant 60 secondes, correction
// instantanée, multiplicateur de série et record gardé sur le téléphone. Chaque
// réponse rejoint la révision comme les autres, et rapporte des points sur le PC.

import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../logic/time_attack.dart';
import '../models/quiz_package.dart';
import '../revision_state.dart';
import '../theme.dart';
import '../widgets/celebration.dart';
import '../widgets/question_parts.dart';

/// Pause avant la question suivante : courte si juste, le temps de voir la
/// bonne réponse si faux.
const rightPause = Duration(milliseconds: 450);
const wrongPause = Duration(milliseconds: 1100);

class TimeAttackScreen extends StatefulWidget {
  const TimeAttackScreen({super.key, required this.state});

  final RevisionState state;

  @override
  State<TimeAttackScreen> createState() => _TimeAttackScreenState();
}

class _TimeAttackScreenState extends State<TimeAttackScreen> with TickerProviderStateMixin {
  late final AnimationController clock =
      AnimationController(vsync: this, duration: timeAttackDuration);
  late final AnimationController shake =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 350));

  late final List<QuizQuestion> deck = [
    for (final vQuestion in widget.state.package!.questions)
      if (vQuestion.type == 'qcm' && vQuestion.choices.length > 1) vQuestion,
  ]..shuffle(widget.state.random);

  TimeAttackScore score = TimeAttackScore();
  int position = 0;

  /// Ordre d'affichage des choix : indices d'origine mélangés.
  List<int> order = [];

  int? chosen;
  int lastGain = 0;
  bool finished = false;
  bool record = false;

  QuizQuestion get question => deck[position % deck.length];

  @override
  void initState() {
    super.initState();

    clock.addStatusListener((pStatus) {
      if (pStatus == AnimationStatus.completed) {
        finish();
      }
    });
    start();
  }

  @override
  void dispose() {
    clock.dispose();
    shake.dispose();
    super.dispose();
  }

  void start() {
    setState(() {
      score = TimeAttackScore();
      finished = false;
      record = false;
      position = 0;
      deck.shuffle(widget.state.random);
      prepare();
    });
    clock.forward(from: 0);
  }

  void prepare() {
    order = List.generate(question.choices.length, (pIndex) => pIndex)
      ..shuffle(widget.state.random);
    chosen = null;
  }

  Future<void> choose(int pChoice) async {
    if (chosen != null || finished) {
      return;
    }

    setState(() => chosen = pChoice);

    final vGrade = await widget.state.answer(question, pChoice);
    final vGain = score.record(vGrade.correct);

    if (widget.state.hapticsEnabled) {
      unawaited(vGrade.correct ? HapticFeedback.lightImpact() : HapticFeedback.heavyImpact());
    }

    if (!vGrade.correct) {
      unawaited(shake.forward(from: 0));
    }

    if (!mounted) {
      return;
    }

    setState(() => lastGain = vGain);

    await Future<void>.delayed(vGrade.correct ? rightPause : wrongPause);

    if (mounted && !finished) {
      setState(() {
        position++;
        prepare();
      });
    }
  }

  Future<void> finish() async {
    if (finished) {
      return;
    }

    final vBest = widget.state.timeAttackBest;
    final vRecord = await widget.state.recordTimeAttack(score.points);

    if (!mounted) {
      return;
    }

    setState(() {
      finished = true;
      record = vRecord;
    });

    if (vRecord && score.points > 0) {
      unawaited(
        showCelebration(
          context,
          title: 'Record !',
          subtitle: '${score.points} points',
          detail: vBest > 0 ? 'Ancien record : $vBest points' : 'Premier record établi',
        ),
      );
    }
  }

  Color? colorOf(int pChoice) {
    final vChosen = chosen;
    Color? rColor;

    if (vChosen != null && pChoice == question.answer) {
      rColor = successColorOf(context);
    } else if (vChosen == pChoice) {
      rColor = dangerColorOf(context);
    }

    return rColor;
  }

  Widget buildHeader() {
    final vTheme = Theme.of(context);

    final rHeader = Column(
      children: [
        AnimatedBuilder(
          animation: clock,
          builder: (_, __) => LinearProgressIndicator(
            value: 1 - clock.value,
            minHeight: 8,
            borderRadius: BorderRadius.circular(4),
            color: clock.value > 0.8 ? dangerColorOf(context) : vTheme.colorScheme.primary,
          ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            // Le score grossit un instant à chaque gain.
            TweenAnimationBuilder<double>(
              key: ValueKey<int>(score.points),
              tween: Tween(begin: 1.3, end: 1),
              duration: const Duration(milliseconds: 300),
              curve: Curves.easeOutBack,
              builder: (_, pScale, pChild) => Transform.scale(scale: pScale, child: pChild),
              child: Text(
                '${score.points} pts',
                style: vTheme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
              ),
            ),
            const SizedBox(width: 8),
            AnimatedOpacity(
              opacity: chosen != null && lastGain > 0 ? 1 : 0,
              duration: const Duration(milliseconds: 200),
              child: Text(
                '+$lastGain',
                style: TextStyle(color: successColorOf(context), fontWeight: FontWeight.w700),
              ),
            ),
            const Spacer(),
            AnimatedScale(
              scale: score.multiplier > 1 ? 1.15 : 1,
              duration: const Duration(milliseconds: 250),
              child: Chip(
                avatar: Icon(Icons.local_fire_department, color: Colors.orange.shade700),
                label: Text('x${score.multiplier} · série ${score.combo}'),
              ),
            ),
          ],
        ),
      ],
    );

    return rHeader;
  }

  Widget buildQuestion() {
    final vQuestion = question;

    final rView = AnimatedBuilder(
      animation: shake,
      builder: (_, pChild) => Transform.translate(
        offset: Offset(sin(shake.value * pi * 6) * 10 * (1 - shake.value), 0),
        child: pChild,
      ),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          buildHeader(),
          const SizedBox(height: 16),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 250),
            child: Column(
              key: ValueKey<int>(position),
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(vQuestion.text, style: Theme.of(context).textTheme.titleMedium),
                if (vQuestion.code != null) ...[
                  const SizedBox(height: 12),
                  CodeBlock(code: vQuestion.code!),
                ],
                const SizedBox(height: 16),
                for (final vChoice in order)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 200),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(12),
                        color: colorOf(vChoice)?.withValues(alpha: 0.18),
                      ),
                      child: OutlinedButton(
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.all(14),
                          alignment: Alignment.centerLeft,
                          side: colorOf(vChoice) == null
                              ? null
                              : BorderSide(color: colorOf(vChoice)!, width: 2),
                        ),
                        onPressed: chosen == null ? () => choose(vChoice) : null,
                        child: Text(vQuestion.choices[vChoice]),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );

    return rView;
  }

  Widget buildResult() {
    final vTheme = Theme.of(context);

    final rView = Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              record ? Icons.emoji_events : Icons.timer_off_outlined,
              size: 56,
              color: record ? Colors.amber.shade700 : vTheme.colorScheme.primary,
            ),
            const SizedBox(height: 12),
            Text('Temps écoulé', style: vTheme.textTheme.headlineSmall),
            const SizedBox(height: 8),
            Text(
              describeTimeAttack(score, widget.state.timeAttackBest, record),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: start,
              icon: const Icon(Icons.replay),
              label: const Text('Rejouer'),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Terminer'),
            ),
          ],
        ),
      ),
    );

    return rView;
  }

  @override
  Widget build(BuildContext context) {
    final rScreen = Scaffold(
      appBar: AppBar(title: const Text('Contre la montre')),
      body: deck.isEmpty
          ? const Center(child: Text("Aucun QCM pour le moment : synchronisez d'abord."))
          : finished
              ? buildResult()
              : buildQuestion(),
    );

    return rScreen;
  }
}
