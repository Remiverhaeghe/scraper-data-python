// Puzzles de code hors ligne : séries de dix, de difficulté croissante. Une série
// terminée part au PC, qui la recorrige à la synchronisation.

import 'dart:math';

import 'package:flutter/material.dart';

import '../l10n/texts.dart';
import '../logic/code_puzzles.dart';
import '../models/quiz_package.dart';
import '../revision_state.dart';
import '../widgets/question_input.dart';

const _codeStyle = TextStyle(fontFamily: 'monospace', fontSize: 13);

class PuzzleScreen extends StatefulWidget {
  const PuzzleScreen({super.key, required this.state, this.random});

  final RevisionState state;

  /// Tirage des séries, fixé par les tests.
  final Random? random;

  @override
  State<PuzzleScreen> createState() => _PuzzleScreenState();
}

class _PuzzleScreenState extends State<PuzzleScreen> {
  late final Random random = widget.random ?? Random();
  final text = TextEditingController();
  Object? response;
  String message = '';

  /// Correction de la dernière réponse, affichée jusqu'au puzzle suivant.
  (bool, String, String, Map<String, dynamic>)? feedback;

  RevisionState get state => widget.state;

  @override
  void dispose() {
    text.dispose();
    super.dispose();
  }

  Map<String, dynamic>? get puzzle {
    final vSeries = state.puzzleSeries;

    if (vSeries == null) {
      return null;
    }

    final vId = (vSeries['ids'] as List)[(vSeries['answers'] as List).length];

    return state.puzzles.firstWhere((pPuzzle) => pPuzzle['id'] == vId);
  }

  Future<void> start() async {
    await state.startPuzzleSeries(random);
    setState(() => next());
  }

  void next() {
    feedback = null;
    response = null;
    message = '';
    text.clear();
  }

  Future<void> submit(Map<String, dynamic> pPuzzle) async {
    try {
      final (vCorrect, vGiven, vExpected) =
          await state.answerPuzzle(pPuzzle['type'] == 'saisie' ? text.text : response);

      setState(() => feedback = (vCorrect, vGiven, vExpected, pPuzzle));
    } on PuzzleAnswerError catch (vError) {
      setState(() => message = vError.message);
    }
  }

  Widget code(String pText) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(8),
        ),
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: SelectableText(pText, style: _codeStyle),
        ),
      );

  Widget buildAnswer(Map<String, dynamic> pPuzzle) {
    switch (pPuzzle['type']) {
      case 'ordre':
        return Theme(
          data: Theme.of(context)
              .copyWith(listTileTheme: const ListTileThemeData(titleTextStyle: _codeStyle)),
          child: OrderInput(
            key: ValueKey(pPuzzle['id']),
            question: QuizQuestion(pPuzzle),
            random: random,
            enabled: true,
            onChanged: (pResponse) => response = pResponse,
          ),
        );
      case 'saisie':
        return Column(
          children: [
            code(pPuzzle['code'] as String),
            const SizedBox(height: 8),
            TextField(
              controller: text,
              style: _codeStyle,
              autocorrect: false,
              enableSuggestions: false,
              decoration: InputDecoration(
                  labelText: context.texts.puzzleCeQuiRemplace, border: const OutlineInputBorder()),
              onSubmitted: (_) => submit(pPuzzle),
            ),
          ],
        );
      default:
        final vLines = pPuzzle['lines'] as List;

        return Card(
          child: Column(
            children: [
              for (var vIndex = 0; vIndex < vLines.length; vIndex++)
                ListTile(
                  dense: true,
                  selected: response == vIndex,
                  selectedTileColor: Theme.of(context).colorScheme.primaryContainer,
                  leading: Text('${vIndex + 1}', style: _codeStyle),
                  title: Text(vLines[vIndex] as String, style: _codeStyle),
                  onTap: () => setState(() => response = vIndex),
                ),
            ],
          ),
        );
    }
  }

  Widget buildPuzzle(Map<String, dynamic> pPuzzle) {
    final vTheme = Theme.of(context);
    final vPosition = (state.puzzleSeries!['answers'] as List).length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(pPuzzle['title'] as String, style: vTheme.textTheme.titleLarge),
        Text(
          context.texts.puzzlePuzzleSur(
              '${vPosition + 1}',
              '${state.puzzleRules.seriesLength}',
              '${state.puzzleRules.types[pPuzzle['type']]}',
              '${pPuzzle['language']}',
              state.puzzleRules.levelLabel(pPuzzle['level'] as int)),
          style: vTheme.textTheme.bodySmall,
        ),
        const SizedBox(height: 8),
        Text(pPuzzle['prompt'] as String),
        const SizedBox(height: 8),
        buildAnswer(pPuzzle),
        if (message.isNotEmpty) Text(message, style: TextStyle(color: vTheme.colorScheme.error)),
        const SizedBox(height: 8),
        FilledButton.icon(
          onPressed: () => submit(pPuzzle),
          icon: const Icon(Icons.check),
          label: Text(context.texts.commonValider),
        ),
      ],
    );
  }

  Widget buildFeedback() {
    final (vCorrect, vGiven, vExpected, vPuzzle) = feedback!;
    final vTheme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(vPuzzle['title'] as String, style: vTheme.textTheme.titleLarge),
        Text(
          context.texts.puzzleReponsesJustesAffilee(
              vCorrect ? 'Bonne réponse' : "Ce n'est pas la bonne réponse",
              '${state.puzzleProgress['streak']}'),
          style: vTheme.textTheme.titleMedium?.copyWith(
            color: vCorrect ? Colors.green.shade700 : vTheme.colorScheme.error,
          ),
        ),
        if (!vCorrect) ...[
          const SizedBox(height: 8),
          Text(context.texts.puzzleVotreReponse),
          code(vGiven),
          Text(context.texts.puzzleReponseAttendue),
          code(vExpected),
        ],
        const SizedBox(height: 8),
        Text(vPuzzle['explanation'] as String),
        const SizedBox(height: 8),
        if (state.puzzleSeries != null)
          FilledButton.icon(
            onPressed: () => setState(next),
            icon: const Icon(Icons.arrow_forward),
            label: Text(context.texts.puzzlePuzzleSuivant),
          ),
      ],
    );
  }

  Widget buildRecap(Map<String, dynamic> pRecap) {
    final vTheme = Theme.of(context);
    final vTitles = {for (final vPuzzle in state.puzzles) vPuzzle['id']: vPuzzle};

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(context.texts.puzzleBilanSerieSur('${pRecap['score']}', '${pRecap['total']}'),
            style: vTheme.textTheme.titleLarge),
        if ((pRecap['mistakes'] as List).isEmpty)
          Text(context.texts.puzzleAucuneErreurSerieParfaite),
        for (final vMistake in pRecap['mistakes'] as List)
          if (vTitles[(vMistake as Map)['id']] case final vPuzzle?)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${vPuzzle['title']} · ${vPuzzle['language']}',
                        style: vTheme.textTheme.titleSmall),
                    Text(context.texts.puzzleVotreReponse),
                    code(vMistake['given'] as String),
                    Text(context.texts.puzzleReponseAttendue),
                    code(vMistake['expected'] as String),
                    Text(vPuzzle['explanation'] as String),
                  ],
                ),
              ),
            ),
      ],
    );
  }

  @override
  Widget build(BuildContext pContext) {
    final vProgress = state.puzzleProgress;
    final vPuzzle = puzzle;
    final vRecap = state.puzzleRecap;

    return Scaffold(
      appBar: AppBar(title: Text(context.texts.commonPuzzlesCode)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: ListTile(
              leading: const Icon(Icons.extension_outlined),
              title: Text(context.texts
                  .puzzleNiveau(state.puzzleRules.levelLabel(vProgress['level'] as int))),
              subtitle: Text(
                context.texts.puzzleReponsesJustesAffileeRecord(
                    '${vProgress['streak']}',
                    '${vProgress['best_streak']}',
                    '${state.puzzleRules.levelUp}',
                    '${state.puzzleRules.levelDown}'),
              ),
            ),
          ),
          const SizedBox(height: 8),
          if (feedback != null) buildFeedback() else if (vPuzzle != null) buildPuzzle(vPuzzle),
          if (vPuzzle == null) ...[
            if (vRecap != null) buildRecap(vRecap),
            const SizedBox(height: 8),
            FilledButton.icon(
              onPressed: start,
              icon: const Icon(Icons.auto_awesome),
              label: Text(vRecap == null ? 'Commencer une série' : 'Nouvelle série'),
            ),
          ],
        ],
      ),
    );
  }
}
