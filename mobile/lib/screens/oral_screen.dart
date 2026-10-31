// Entretien oral simulé, hors ligne : la question est lue par le moteur vocal du
// téléphone, la réponse se dit à voix haute dans le temps choisi, puis se note.
// La séance terminée part au PC, qui la renote et compte les points.

import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../logic/oral_interview.dart';
import '../logic/python_compat.dart';
import '../revision_state.dart';
import '../services/speech.dart';

class OralScreen extends StatefulWidget {
  const OralScreen({super.key, required this.state, this.speech = const Speech(), this.random});

  final RevisionState state;
  final Speech speech;

  /// Tirage des questions, fixé par les tests.
  final Random? random;

  @override
  State<OralScreen> createState() => _OralScreenState();
}

class _OralScreenState extends State<OralScreen> {
  late final Random random = widget.random ?? Random();
  late String mode = (rules['modes'] as Map).keys.first as String;
  late int duration = (rules['durations'] as List)[1] as int;
  List<List> questions = [];
  final answers = <Map<String, dynamic>>[];
  final watch = Stopwatch();
  Timer? ticker;
  bool answering = false;
  int? seconds;
  int? structure;
  int? example;
  Map<String, dynamic>? feedback;
  int? finalScore;

  Map<String, dynamic> get rules => widget.state.oralRules;

  int get position => answers.length;

  @override
  void dispose() {
    ticker?.cancel();
    widget.speech.stop();
    super.dispose();
  }

  void start() {
    final vPool = [
      for (final vQuestion in (widget.state.oralContent['questions'] as Map)[mode] as List)
        vQuestion as List,
    ]..shuffle(random);

    setState(() {
      questions = vPool.take(rules['session_length'] as int).toList();
      answers.clear();
      finalScore = null;
    });
    showQuestion();
  }

  void showQuestion() {
    setState(() {
      feedback = null;
      seconds = null;
      structure = null;
      example = null;
      answering = false;
    });
    read();
  }

  /// Lit la question ; le chrono démarre à la fin de la lecture, ou aussitôt sans voix.
  Future<void> read() async {
    await widget.speech.speak(questions[position][0] as String);

    if (mounted) {
      begin();
    }
  }

  void begin() {
    if (answering || seconds != null || feedback != null) {
      return;
    }

    widget.speech.stop();
    watch
      ..reset()
      ..start();
    ticker = Timer.periodic(const Duration(milliseconds: 250), (_) => setState(() {}));
    setState(() => answering = true);
  }

  void finish() {
    ticker?.cancel();
    watch.stop();
    setState(() {
      answering = false;
      seconds = watch.elapsed.inMilliseconds ~/ 1000;
    });
  }

  Future<void> validate() async {
    final vGrade =
        gradeOralAnswer(seconds, duration, structure, example, rules['min_seconds'] as int);

    if (vGrade == null) {
      return;
    }

    answers.add(vGrade);
    int? vScore;

    if (answers.length == questions.length) {
      vScore = roundHalfEven(
          answers.map((pAnswer) => pAnswer['score'] as int).reduce((pA, pB) => pA + pB) /
              answers.length);
      await widget.state.recordOral(
        {
          'mode': mode,
          'duration': duration,
          'answers': [
            for (final vAnswer in answers)
              {
                'seconds': vAnswer['seconds'],
                'structure': vAnswer['structure'],
                'example': vAnswer['example']
              },
          ],
        },
        vScore,
      );
    }

    setState(() {
      feedback = vGrade;
      finalScore = vScore;
    });
  }

  String clock(num pSeconds) {
    final vSeconds = pSeconds.abs().truncate();

    return '${pSeconds < 0 ? '-' : ''}${vSeconds ~/ 60}:${(vSeconds % 60).toString().padLeft(2, '0')}';
  }

  Widget buildRating(String pLabel, String pTip, int? pValue, ValueChanged<int> pOnChanged) {
    final vRatings = Map<String, dynamic>.from(rules['ratings'] as Map);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 8),
        Text('$pLabel : $pTip'),
        SegmentedButton<int>(
          emptySelectionAllowed: true,
          segments: [
            for (final vEntry in vRatings.entries)
              ButtonSegment(value: int.parse(vEntry.key), label: Text(vEntry.value as String)),
          ],
          selected: {if (pValue != null) pValue},
          onSelectionChanged: (pSelection) => setState(() => pOnChanged(pSelection.first)),
        ),
      ],
    );
  }

  Widget buildSession() {
    final vTheme = Theme.of(context);
    final vQuestion = questions[position < questions.length ? position : questions.length - 1];
    final vCriteria = [
      for (final vCriterion in rules['criteria'] as List) List<String>.from(vCriterion as List)
    ];
    final vRemaining = duration - watch.elapsed.inMilliseconds / 1000;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Question ${min(position + 1, questions.length)} sur ${questions.length}',
          style: vTheme.textTheme.bodySmall,
        ),
        Text(vQuestion[0] as String, style: vTheme.textTheme.titleLarge),
        const SizedBox(height: 12),
        if (feedback == null && seconds == null) ...[
          Text(
            clock(answering ? vRemaining : duration),
            style: vTheme.textTheme.displaySmall?.copyWith(
              color: vRemaining < 0 ? vTheme.colorScheme.error : null,
            ),
          ),
          Wrap(
            spacing: 8,
            children: [
              if (!answering) ...[
                OutlinedButton.icon(
                    onPressed: read,
                    icon: const Icon(Icons.volume_up),
                    label: const Text('Réécouter')),
                FilledButton.icon(
                    onPressed: begin,
                    icon: const Icon(Icons.timer),
                    label: const Text('Je commence')),
              ] else
                FilledButton.icon(
                    onPressed: finish,
                    icon: const Icon(Icons.check),
                    label: const Text("J'ai terminé")),
            ],
          ),
        ],
        if (seconds != null && feedback == null) ...[
          Text('Réponse de ${clock(seconds!)}'),
          buildRating(vCriteria[0][1], vCriteria[0][2], structure, (pValue) => structure = pValue),
          buildRating(vCriteria[1][1], vCriteria[1][2], example, (pValue) => example = pValue),
          const SizedBox(height: 8),
          FilledButton(
            onPressed: structure == null || example == null ? null : validate,
            child: const Text('Valider ma note'),
          ),
        ],
        if (feedback case final vFeedback?) ...[
          Text(
            'Réponse notée ${vFeedback['score']} % · ${vFeedback['seconds']} s, '
            '${(rules['duration_ratings'] as Map)['${vFeedback['duration']}']}',
            style: vTheme.textTheme.titleMedium,
          ),
          Text('Conseil : ${vQuestion[1]}'),
          const SizedBox(height: 8),
          if (finalScore case final vScore?)
            Text(
              'Séance terminée : $vScore % · +${widget.state.oralXp} XP au retour sur le PC',
              style: vTheme.textTheme.titleMedium?.copyWith(color: Colors.green.shade700),
            )
          else
            FilledButton.icon(
              onPressed: showQuestion,
              icon: const Icon(Icons.arrow_forward),
              label: const Text('Question suivante'),
            ),
        ],
      ],
    );
  }

  Widget buildChoice() {
    final vModes = Map<String, dynamic>.from(rules['modes'] as Map);
    final vTarget = (widget.state.oralContent['targets'] as Map?)?[mode] as String? ?? '';
    final vRecent = widget.state.oralRecent;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (vRecent.isNotEmpty)
          Text('Notes récentes : ${vRecent.map((pScore) => '$pScore %').join(', ')}'),
        const SizedBox(height: 8),
        DropdownButtonFormField<String>(
          initialValue: mode,
          decoration:
              const InputDecoration(labelText: 'Type de questions', border: OutlineInputBorder()),
          items: [
            for (final vEntry in vModes.entries)
              DropdownMenuItem(value: vEntry.key, child: Text(vEntry.value as String)),
          ],
          onChanged: (pMode) => setState(() => mode = pMode ?? mode),
        ),
        if (vTarget.isNotEmpty) Text('Pour : $vTarget'),
        const SizedBox(height: 8),
        SegmentedButton<int>(
          segments: [
            for (final vDuration in rules['durations'] as List)
              ButtonSegment(value: vDuration as int, label: Text(clock(vDuration))),
          ],
          selected: {duration},
          onSelectionChanged: (pSelection) => setState(() => duration = pSelection.first),
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: start,
          icon: const Icon(Icons.record_voice_over),
          label: Text(finalScore == null ? 'Commencer' : 'Nouvelle séance'),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext pContext) => Scaffold(
        appBar: AppBar(title: const Text('Entretien oral')),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            const Text(
              'La question est lue à voix haute : répondez à l\'oral, dans le temps, puis notez '
              'votre réponse. Rien n\'est enregistré du son.',
            ),
            const SizedBox(height: 12),
            if (questions.isEmpty || finalScore != null) ...[
              if (finalScore != null) buildSession(),
              const SizedBox(height: 12),
              buildChoice(),
            ] else
              buildSession(),
          ],
        ),
      );
}
