// Simulations jouables hors ligne : contenu reçu du PC à la synchronisation.

import 'package:flutter/material.dart';

import '../revision_state.dart';
import 'circuit_screen.dart';
import 'devops_screen.dart';
import 'git_screen.dart';
import 'ladder_screen.dart';
import 'oral_screen.dart';
import 'puzzle_screen.dart';
import 'sql_screen.dart';
import 'troubleshooting_screen.dart';

class LabsScreen extends StatelessWidget {
  const LabsScreen({super.key, required this.state});

  final RevisionState state;

  @override
  Widget build(BuildContext pContext) => Scaffold(
        appBar: AppBar(title: const Text('Simulations')),
        body: ListenableBuilder(
          listenable: state,
          builder: (pContext, _) => ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (state.troubleshootingScenarios.isEmpty &&
                  state.ladderLevels.isEmpty &&
                  state.gitLevels.isEmpty &&
                  state.circuitLevels.isEmpty &&
                  state.puzzles.isEmpty)
                const Text(
                  'Synchronisez une fois avec le PC pour télécharger les simulations : '
                  'elles se jouent ensuite sans réseau.',
                ),
              if (state.pendingLabs.isNotEmpty)
                Text(
                    '${state.pendingLabs.length} partie(s) à envoyer au PC à la prochaine synchronisation.'),
              if (state.oralRules.isNotEmpty)
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.record_voice_over),
                    title: const Text('Entretien oral'),
                    subtitle: const Text('Questions lues à voix haute, réponse chronométrée'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.of(pContext).push(
                      MaterialPageRoute<void>(builder: (_) => OralScreen(state: state)),
                    ),
                  ),
                ),
              if (state.puzzles.isNotEmpty)
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.extension_outlined),
                    title: const Text('Puzzles de code'),
                    subtitle: Text(
                      'Ordre, ligne fautive, code à compléter · niveau '
                      '${state.puzzleRules.levelLabel(state.puzzleProgress['level'] as int)}',
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.of(pContext).push(
                      MaterialPageRoute<void>(builder: (_) => PuzzleScreen(state: state)),
                    ),
                  ),
                ),
              if (state.troubleshootingScenarios.isNotEmpty)
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.build_outlined),
                    title: const Text('Pannes à résoudre'),
                    subtitle: Text('${state.troubleshootingScenarios.length} machines en panne'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.of(pContext).push(
                      MaterialPageRoute<void>(
                          builder: (_) => TroubleshootingListScreen(state: state)),
                    ),
                  ),
                ),
              if (state.gitLevels.isNotEmpty)
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.account_tree_outlined),
                    title: const Text('Bac à sable Git'),
                    subtitle: Text(
                      '${state.gitLevels.where((pLevel) => state.gitBest(pLevel['id'] as String) != null).length}'
                      ' / ${state.gitLevels.length} niveaux réussis',
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.of(pContext).push(
                      MaterialPageRoute<void>(builder: (_) => GitListScreen(state: state)),
                    ),
                  ),
                ),
              if (state.sqlLevelList.isNotEmpty)
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.storage_outlined),
                    title: const Text('Bac à sable SQL'),
                    subtitle: Text(
                      '${state.sqlPassed.length} / ${state.sqlLevelList.length} niveaux réussis',
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.of(pContext).push(
                      MaterialPageRoute<void>(builder: (_) => SqlListScreen(state: state)),
                    ),
                  ),
                ),
              if (state.devopsLevels.isNotEmpty)
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.dns_outlined),
                    title: const Text('Maven et Docker'),
                    subtitle: Text(
                      '${state.devopsPassed.length} / ${state.devopsLevels.length} niveaux réussis',
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.of(pContext).push(
                      MaterialPageRoute<void>(builder: (_) => DevopsListScreen(state: state)),
                    ),
                  ),
                ),
              if (state.circuitLevels.isNotEmpty && state.circuitLibrary != null)
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.electrical_services),
                    title: const Text('Schémas électriques'),
                    subtitle: Text(
                      '${state.circuitPassed.length} / ${state.circuitLevels.length} montages réussis, et le mode libre',
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.of(pContext).push(
                      MaterialPageRoute<void>(builder: (_) => CircuitListScreen(state: state)),
                    ),
                  ),
                ),
              if (state.ladderLevels.isNotEmpty)
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.memory_outlined),
                    title: const Text("Simulateur d'automate"),
                    subtitle: Text(
                      '${state.ladderPassed.length} / ${state.ladderLevels.length} niveaux réussis',
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.of(pContext).push(
                      MaterialPageRoute<void>(builder: (_) => LadderListScreen(state: state)),
                    ),
                  ),
                ),
            ],
          ),
        ),
      );
}
