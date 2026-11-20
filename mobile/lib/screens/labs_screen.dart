// Simulations jouables hors ligne : contenu reçu du PC à la synchronisation.

import 'package:flutter/material.dart';

import '../l10n/texts.dart';
import '../revision_state.dart';
import 'circuit_screen.dart';
import 'devops_screen.dart';
import 'excel_screen.dart';
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
        appBar: AppBar(title: Text(pContext.texts.labsSimulations)),
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
                Text(
                  pContext.texts.commonSynchronisezFoisAvecPc,
                ),
              if (state.pendingLabs.isNotEmpty)
                Text(pContext.texts.commonPartieEnvoyerAuPc('${state.pendingLabs.length}')),
              if (state.oralRules.isNotEmpty)
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.record_voice_over),
                    title: Text(pContext.texts.commonEntretienOral),
                    subtitle: Text(pContext.texts.labsQuestionsLuesVoixHaute),
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
                    title: Text(pContext.texts.commonPuzzlesCode),
                    subtitle: Text(
                      pContext.texts.labsOrdreLigneFautiveCode(
                          state.puzzleRules.levelLabel(state.puzzleProgress['level'] as int)),
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
                    title: Text(pContext.texts.commonPannesResoudre),
                    subtitle: Text(pContext.texts
                        .labsMachinesPanne('${state.troubleshootingScenarios.length}')),
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
                    title: Text(pContext.texts.commonBacSableGit),
                    subtitle: Text(
                      pContext.texts.labsNiveauxReussis(
                          '${state.gitLevels.where((pLevel) => state.gitBest(pLevel['id'] as String) != null).length}',
                          '${state.gitLevels.length}'),
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
                    title: Text(pContext.texts.commonBacSableSql),
                    subtitle: Text(
                      pContext.texts.labsNiveauxReussis(
                          '${state.sqlPassed.length}', '${state.sqlLevelList.length}'),
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.of(pContext).push(
                      MaterialPageRoute<void>(builder: (_) => SqlListScreen(state: state)),
                    ),
                  ),
                ),
              if (state.excelLevelList.isNotEmpty && state.excelLevels != null)
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.table_chart_outlined),
                    title: Text(pContext.texts.commonAtelierExcel),
                    subtitle: Text(
                      pContext.texts.labsNiveauxReussis(
                          '${state.excelPassed.length}', '${state.excelLevelList.length}'),
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.of(pContext).push(
                      MaterialPageRoute<void>(builder: (_) => ExcelListScreen(state: state)),
                    ),
                  ),
                ),
              if (state.devopsLevels.isNotEmpty)
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.dns_outlined),
                    title: Text(pContext.texts.commonMavenDocker),
                    subtitle: Text(
                      pContext.texts.labsNiveauxReussis(
                          '${state.devopsPassed.length}', '${state.devopsLevels.length}'),
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
                    title: Text(pContext.texts.commonSchemasElectriques),
                    subtitle: Text(
                      pContext.texts.labsMontagesReussisModeLibre(
                          '${state.circuitPassed.length}', '${state.circuitLevels.length}'),
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
                    title: Text(pContext.texts.commonSimulateurAutomate),
                    subtitle: Text(
                      pContext.texts.labsNiveauxReussis(
                          '${state.ladderPassed.length}', '${state.ladderLevels.length}'),
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
