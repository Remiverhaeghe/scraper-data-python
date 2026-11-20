// Simulation d'entretien technique : questions ouvertes, réponse attendue et
// points clés cochés, comme sur le PC. La série part au PC à la synchronisation.

import 'dart:math';

import 'package:flutter/material.dart';

import '../l10n/texts.dart';
import '../revision_state.dart';

/// Questions d'une série, au plus
const simulationSize = 5;

/// En dessous, la question est à retravailler.
const weakScore = 50;

class InterviewScreen extends StatefulWidget {
  const InterviewScreen({super.key, required this.state, this.random});

  final RevisionState state;
  final Random? random;

  @override
  State<InterviewScreen> createState() => _InterviewScreenState();
}

class _InterviewScreenState extends State<InterviewScreen> {
  String? theme;
  List<Map<String, dynamic>> questions = [];
  final results = <Map<String, dynamic>>[];
  final scores = <int>[];
  final checked = <int>{};
  bool revealed = false;

  int get position => results.length;

  bool get finished => questions.isNotEmpty && position >= questions.length;

  void start() {
    final vAll = widget.state.interviewQuestions;
    final vChosen = theme == null || theme == widget.state.interviewThemes.firstOrNull
        ? [...vAll]
        : vAll.where((vQuestion) => vQuestion['theme'] == theme).toList();

    vChosen.shuffle(widget.random ?? Random());

    setState(() {
      questions = vChosen.take(simulationSize).toList();
      results.clear();
      scores.clear();
      checked.clear();
      revealed = false;
    });
  }

  Future<void> validate() async {
    final vQuestion = questions[position];
    final vPoints = (vQuestion['points'] as List).length;

    results.add({'question_id': vQuestion['id'], 'checked': checked.toList()});
    scores.add((100 * checked.length / vPoints).round());

    if (position >= questions.length) {
      await widget.state.recordInterviewSeries(
        theme ?? widget.state.interviewThemes.firstOrNull ?? '',
        results,
      );
    }

    setState(() {
      checked.clear();
      revealed = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final vThemes = widget.state.interviewThemes;

    final Widget vBody;

    if (widget.state.interviewQuestions.isEmpty) {
      vBody = Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text(context.texts.interviewSynchronisezAvecPcPour),
        ),
      );
    } else if (questions.isEmpty) {
      vBody = buildStart(vThemes);
    } else if (finished) {
      vBody = buildSummary();
    } else {
      vBody = buildQuestion(questions[position]);
    }

    final rScreen = Scaffold(
      appBar: AppBar(title: Text(context.texts.interviewSimulationEntretien)),
      body: vBody,
    );

    return rScreen;
  }

  Widget buildStart(List<String> pThemes) {
    final rStart = ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          context.texts.interviewCinqQuestionsOuvertesComme,
        ),
        const SizedBox(height: 16),
        DropdownButton<String>(
          value: theme ?? pThemes.firstOrNull,
          isExpanded: true,
          items: [
            for (final vTheme in pThemes) DropdownMenuItem(value: vTheme, child: Text(vTheme)),
          ],
          onChanged: (pTheme) => setState(() => theme = pTheme),
        ),
        const SizedBox(height: 16),
        FilledButton(onPressed: start, child: Text(context.texts.interviewCommencer)),
      ],
    );

    return rStart;
  }

  Widget buildQuestion(Map<String, dynamic> pQuestion) {
    final vTheme = Theme.of(context);
    final vPoints = List<String>.from(pQuestion['points'] as List);

    final rQuestion = ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          context.texts.interviewQuestionSur('${pQuestion['theme']}', '${position + 1}', '${questions.length}'),
          style: vTheme.textTheme.bodySmall,
        ),
        const SizedBox(height: 8),
        Text('${pQuestion['question']}', style: vTheme.textTheme.titleMedium),
        const SizedBox(height: 12),
        TextField(
          minLines: 3,
          maxLines: 8,
          decoration: InputDecoration(
            border: OutlineInputBorder(),
            hintText: context.texts.interviewVotreReponsePourVous,
          ),
        ),
        const SizedBox(height: 12),
        if (!revealed)
          OutlinedButton(
            onPressed: () => setState(() => revealed = true),
            child: Text(context.texts.interviewVoirReponseAttendue),
          )
        else ...[
          Text('${pQuestion['answer']}'),
          const SizedBox(height: 12),
          Text(context.texts.interviewCochezPointsClesCites, style: vTheme.textTheme.labelLarge),
          for (var vIndex = 0; vIndex < vPoints.length; vIndex++)
            CheckboxListTile(
              value: checked.contains(vIndex),
              title: Text(vPoints[vIndex]),
              onChanged: (pValue) => setState(
                () => pValue ?? false ? checked.add(vIndex) : checked.remove(vIndex),
              ),
            ),
          FilledButton(onPressed: validate, child: Text(context.texts.interviewValiderContinuer)),
        ],
      ],
    );

    return rQuestion;
  }

  Widget buildSummary() {
    final vScore = (scores.reduce((vSum, vValue) => vSum + vValue) / scores.length).round();
    final vWeak = [
      for (var vIndex = 0; vIndex < scores.length; vIndex++)
        if (scores[vIndex] < weakScore) '${questions[vIndex]['question']}',
    ];

    final rSummary = ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          context.texts.interviewSerieTermineePointsCles('${vScore}'),
          style: Theme.of(context).textTheme.titleMedium,
        ),
        if (vWeak.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text(context.texts.interviewRetravaillerAjouteEntrainementOral),
          for (final vQuestion in vWeak) Text('• $vQuestion'),
        ],
        const SizedBox(height: 16),
        FilledButton(onPressed: start, child: Text(context.texts.interviewNouvelleSerie)),
      ],
    );

    return rSummary;
  }
}
