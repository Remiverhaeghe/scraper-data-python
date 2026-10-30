// Simulations jouables hors ligne : contenu reçu du PC à la synchronisation.

import 'package:flutter/material.dart';

import '../revision_state.dart';
import 'git_screen.dart';
import 'ladder_screen.dart';
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
                  state.gitLevels.isEmpty)
                const Text(
                  'Synchronisez une fois avec le PC pour télécharger les simulations : '
                  'elles se jouent ensuite sans réseau.',
                ),
              if (state.pendingLabs.isNotEmpty)
                Text(
                    '${state.pendingLabs.length} partie(s) à envoyer au PC à la prochaine synchronisation.'),
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
