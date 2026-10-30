// Bac à sable Git, hors ligne : commandes simulées, graphe du dépôt à côté de
// l'objectif. Un niveau réussi part au PC, qui rejoue les commandes.

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../logic/git_levels.dart';
import '../logic/git_sandbox.dart';
import '../revision_state.dart';

/// Débuts de commande proposés sous le champ, pour taper moins au téléphone.
const quickCommands = [
  'git status',
  'git log',
  'git commit',
  'git add .',
  'git switch ',
  'git merge ',
  'git rebase ',
  'git stash',
  'git stash pop',
  'modifier ',
];

/// Texte d'introduction : **gras** et `code` repris du Markdown du PC.
List<InlineSpan> markdownSpans(String pText, TextStyle? pCode) {
  final rSpans = <InlineSpan>[];
  final vPattern = RegExp(r'\*\*(.+?)\*\*|`(.+?)`');
  var vStart = 0;

  for (final vMatch in vPattern.allMatches(pText)) {
    rSpans.add(TextSpan(text: pText.substring(vStart, vMatch.start)));
    rSpans.add(
      vMatch.group(1) != null
          ? TextSpan(text: vMatch.group(1), style: const TextStyle(fontWeight: FontWeight.bold))
          : TextSpan(text: vMatch.group(2), style: pCode),
    );
    vStart = vMatch.end;
  }

  rSpans.add(TextSpan(text: pText.substring(vStart)));

  return rSpans;
}

class GitListScreen extends StatelessWidget {
  const GitListScreen({super.key, required this.state});

  final RevisionState state;

  /// Meilleur résultat d'un niveau, ou le nombre de commandes de la référence.
  String describeLevel(Map<String, dynamic> pLevel) {
    final vBest = state.gitBest(pLevel['id'] as String);
    final vPar = (pLevel['solution'] as List).length;

    final rText = vBest == null
        ? '$vPar commande(s) attendue(s)'
        : 'Réussi en $vBest commande(s), référence $vPar';

    return rText;
  }

  @override
  Widget build(BuildContext pContext) => Scaffold(
        appBar: AppBar(title: const Text('Bac à sable Git')),
        body: ListenableBuilder(
          listenable: state,
          builder: (pContext, _) {
            final vSeries = <String, List<Map<String, dynamic>>>{};

            for (final vLevel in state.gitLevels) {
              vSeries.putIfAbsent(vLevel['series'] as String, () => []).add(vLevel);
            }

            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                for (final vEntry in vSeries.entries) ...[
                  Padding(
                    padding: const EdgeInsets.only(top: 12, bottom: 4),
                    child: Text(vEntry.key, style: Theme.of(pContext).textTheme.titleMedium),
                  ),
                  for (final vLevel in vEntry.value)
                    Card(
                      child: ListTile(
                        leading: Icon(
                          state.gitBest(vLevel['id'] as String) != null
                              ? Icons.check_circle
                              : Icons.account_tree_outlined,
                        ),
                        title: Text(vLevel['title'] as String),
                        subtitle: Text(describeLevel(vLevel)),
                        onTap: () => Navigator.of(pContext).push(
                          MaterialPageRoute<void>(
                              builder: (_) => GitScreen(state: state, level: vLevel)),
                        ),
                      ),
                    ),
                ],
              ],
            );
          },
        ),
      );
}

class GitScreen extends StatefulWidget {
  const GitScreen({super.key, required this.state, required this.level});

  final RevisionState state;
  final Map<String, dynamic> level;

  @override
  State<GitScreen> createState() => _GitScreenState();
}

class _GitScreenState extends State<GitScreen> {
  final command = TextEditingController();
  List<String> history = [];
  String message = '';
  String tone = 'info';
  bool showHint = false;
  bool showSolution = false;

  Map<String, dynamic> get level => widget.level;

  @override
  void initState() {
    super.initState();
    history = widget.state.gitHistory(level['id'] as String);

    try {
      replayLevel(level, history);
    } on GitError {
      history = [];
    }
  }

  @override
  void dispose() {
    command.dispose();
    super.dispose();
  }

  Future<void> run() async {
    final (vHistory, vMessage, vTone) = runLevelCommand(level, history, command.text);

    setState(() {
      history = vHistory;
      message = vMessage;
      tone = vTone;
    });

    if (vTone != 'danger') {
      command.clear();
    }

    await widget.state.saveGitHistory(level['id'] as String, history);

    if (vTone == 'success') {
      final vFirst = await widget.state.recordGit(level['id'] as String, history);

      if (vFirst && mounted) {
        setState(() => message += ' +${widget.state.gitXp} XP au retour sur le PC.');
      }
    }
  }

  Future<void> restart(List<String> pHistory) async {
    setState(() {
      history = pHistory;
      message = '';
    });
    await widget.state.saveGitHistory(level['id'] as String, history);
  }

  Widget buildGraph(String pTitle, String pSvg) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(pTitle, style: Theme.of(context).textTheme.labelLarge),
          SingleChildScrollView(scrollDirection: Axis.horizontal, child: SvgPicture.string(pSvg)),
        ],
      );

  @override
  Widget build(BuildContext pContext) {
    final vTheme = Theme.of(pContext);
    final vRepository = replayLevel(level, history);
    final vGoal = goalOf(level);
    final vDone = isGoalReached(level, vRepository);
    final vWorktree = describeWorktree(vRepository);
    final vGoalWorktree = describeWorktree(vGoal);
    final vColor = switch (tone) {
      'success' => Colors.green.shade700,
      'danger' => vTheme.colorScheme.error,
      'warning' => Colors.orange.shade800,
      _ => vTheme.colorScheme.onSurface,
    };
    final vCode = TextStyle(
        fontFamily: 'monospace', backgroundColor: vTheme.colorScheme.surfaceContainerHighest);

    return Scaffold(
      appBar: AppBar(title: Text(level['title'] as String)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text.rich(TextSpan(children: markdownSpans(level['intro'] as String, vCode))),
          const SizedBox(height: 12),
          buildGraph('Votre dépôt', renderGraph(vRepository.localView(), 'Votre dépôt')),
          buildGraph('Objectif', renderGraph(vGoal.localView(), 'Objectif')),
          if (vRepository.remote.isNotEmpty) ...[
            buildGraph('Serveur', renderGraph(vRepository.serverView(), 'Serveur', false)),
            buildGraph(
                'Serveur attendu', renderGraph(vGoal.serverView(), 'Serveur attendu', false)),
          ],
          if (vWorktree.isNotEmpty || vGoalWorktree.isNotEmpty)
            Text(
              'Fichiers : ${vWorktree.isEmpty ? 'rien en cours' : vWorktree.join(' · ')}. '
              'Objectif : ${vGoalWorktree.isEmpty ? 'rien en cours' : vGoalWorktree.join(' · ')}.',
              style: vTheme.textTheme.bodySmall,
            ),
          if (message.isNotEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Text(message, style: TextStyle(color: vColor, fontWeight: FontWeight.w600)),
            ),
          if (!vDone) ...[
            TextField(
              controller: command,
              autocorrect: false,
              enableSuggestions: false,
              style: const TextStyle(fontFamily: 'monospace'),
              decoration: InputDecoration(
                labelText: 'Commande',
                hintText: 'git commit',
                border: const OutlineInputBorder(),
                suffixIcon:
                    IconButton(icon: const Icon(Icons.send), tooltip: 'Exécuter', onPressed: run),
              ),
              onSubmitted: (_) => run(),
            ),
            Wrap(
              spacing: 6,
              children: [
                for (final vQuick in quickCommands)
                  ActionChip(
                    label: Text(vQuick.trim()),
                    onPressed: () => setState(() {
                      command.text = vQuick;
                      command.selection = TextSelection.collapsed(offset: vQuick.length);
                    }),
                  ),
              ],
            ),
          ],
          if (history.isNotEmpty)
            Text('Commandes : ${history.join(' · ')}', style: vTheme.textTheme.bodySmall),
          Wrap(
            spacing: 8,
            children: [
              if (history.isNotEmpty && !vDone)
                TextButton(
                    onPressed: () => restart(history.sublist(0, history.length - 1)),
                    child: const Text('Annuler')),
              TextButton(onPressed: () => restart([]), child: const Text('Recommencer')),
              TextButton(
                  onPressed: () => setState(() => showHint = true), child: const Text('Indice')),
              TextButton(
                  onPressed: () => setState(() => showSolution = true),
                  child: const Text('Solution')),
            ],
          ),
          if (showHint) Text('Indice : ${level['hint']}'),
          if (showSolution) Text('Solution : ${(level['solution'] as List).join(' · ')}'),
        ],
      ),
    );
  }
}
