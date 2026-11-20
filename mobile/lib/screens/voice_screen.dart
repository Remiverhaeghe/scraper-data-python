// Révision à la voix, les mains prises ou les yeux ailleurs : la question et ses choix sont
// lus, on répond en disant la lettre, le rang ou le texte du choix, et la correction est lue.

import 'package:flutter/material.dart';

import '../l10n/texts.dart';
import '../logic/review.dart';
import '../logic/voice_answer.dart';
import '../models/quiz_package.dart';
import '../revision_state.dart';
import '../services/speech.dart';

class VoiceScreen extends StatefulWidget {
  const VoiceScreen({super.key, required this.state, this.speech = const Speech()});

  final RevisionState state;
  final Speech speech;

  @override
  State<VoiceScreen> createState() => _VoiceScreenState();
}

class _VoiceScreenState extends State<VoiceScreen> {
  QuizQuestion? question;
  String? heard;
  String? verdict;
  bool busy = false;
  int answered = 0;
  int correct = 0;

  /// Seuls les QCM se prêtent à la voix : une lettre ou un rang suffit.
  List<QuizQuestion> get questions =>
      widget.state.package!.questions.where((pQuestion) => pQuestion.type == 'qcm').toList();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => next());
  }

  @override
  void dispose() {
    widget.speech.stop();
    super.dispose();
  }

  String spoken(QuizQuestion pQuestion) {
    final vText = context.texts;

    return [
      pQuestion.text,
      for (final (vIndex, vChoice) in pQuestion.choices.indexed)
        vText.voiceChoice(choiceLetters[vIndex], vChoice),
    ].join(' ');
  }

  Future<void> next() async {
    final vQuestion = pickQuestion(
      questions,
      widget.state.schedule,
      DateTime.now(),
      widget.state.random,
    );
    setState(() {
      question = vQuestion;
      heard = null;
      verdict = null;
    });
    if (vQuestion != null) {
      await widget.speech.speak(spoken(vQuestion));
    }
  }

  Future<void> listen() async {
    final vQuestion = question;
    if (vQuestion == null || busy) {
      return;
    }
    final vText = context.texts;
    setState(() => busy = true);
    final vHeard = await widget.speech.listen();
    final vChoice =
        matchSpokenChoice(vHeard, vQuestion.choices.take(choiceLetters.length).toList());
    if (!mounted) {
      return;
    }
    if (vChoice == null) {
      setState(() {
        busy = false;
        heard = vHeard.isEmpty ? vText.voiceNothing : vText.voiceNotUnderstood(vHeard.first);
      });
      await widget.speech.speak(vText.voiceRepeat);
      return;
    }
    await choose(vChoice);
  }

  Future<void> choose(int pChoice) async {
    final vQuestion = question!;
    final vText = context.texts;
    final vGrade = await widget.state.answer(vQuestion, pChoice);
    final vSaid = vGrade.correct
        ? vText.voiceRight
        : vText.voiceWrong(choiceLetters[vQuestion.answer], vGrade.expected);
    if (!mounted) {
      return;
    }
    setState(() {
      busy = false;
      answered++;
      correct += vGrade.correct ? 1 : 0;
      heard = vText.voiceHeard(choiceLetters[pChoice]);
      verdict = vSaid;
    });
    await widget.speech.speak(vSaid);
  }

  @override
  Widget build(BuildContext context) {
    final vText = context.texts;
    final vTheme = Theme.of(context);
    final vQuestion = question;

    final rScreen = Scaffold(
      appBar: AppBar(
        title: Text(vText.voiceTitle),
        actions: [
          IconButton(
            tooltip: vText.voiceReadAgain,
            icon: const Icon(Icons.replay),
            onPressed: vQuestion == null ? null : () => widget.speech.speak(spoken(vQuestion)),
          ),
        ],
      ),
      body: vQuestion == null
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(vText.voiceEmpty, textAlign: TextAlign.center),
              ),
            )
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text(vText.voiceHelp, style: vTheme.textTheme.bodySmall),
                const SizedBox(height: 12),
                Text(vQuestion.text, style: vTheme.textTheme.titleMedium),
                const SizedBox(height: 12),
                for (final (vIndex, vChoice)
                    in vQuestion.choices.take(choiceLetters.length).indexed)
                  ListTile(
                    leading: CircleAvatar(child: Text(choiceLetters[vIndex])),
                    title: Text(vChoice),
                    enabled: verdict == null && !busy,
                    onTap: () => choose(vIndex),
                  ),
                const SizedBox(height: 16),
                if (heard != null) Text(heard!, style: vTheme.textTheme.bodyMedium),
                if (verdict != null) ...[
                  Text(verdict!, style: vTheme.textTheme.titleMedium),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: next,
                    icon: const Icon(Icons.arrow_forward),
                    label: Text(vText.voiceNext),
                  ),
                ] else
                  FilledButton.icon(
                    onPressed: busy ? null : listen,
                    icon: const Icon(Icons.mic),
                    label: Text(vText.voiceAnswer),
                  ),
                const SizedBox(height: 16),
                if (answered > 0)
                  Text(
                    vText.voiceScore(answered, correct),
                    textAlign: TextAlign.center,
                    style: vTheme.textTheme.bodySmall,
                  ),
              ],
            ),
    );

    return rScreen;
  }
}
