// Pannes à résoudre, hors ligne : choisir ses mesures, réparer, comparer son
// temps à celui d'un technicien. La partie part au PC à la synchronisation.

import 'package:flutter/material.dart';

import '../logic/troubleshooting.dart';
import '../revision_state.dart';

/// Liste des machines en panne, avec le meilleur score de chacune.
class TroubleshootingListScreen extends StatelessWidget {
  const TroubleshootingListScreen({super.key, required this.state});

  final RevisionState state;

  @override
  Widget build(BuildContext pContext) {
    final vScenarios = state.troubleshootingScenarios;

    return Scaffold(
      appBar: AppBar(title: const Text('Pannes à résoudre')),
      body: ListenableBuilder(
        listenable: state,
        builder: (pContext, _) => vScenarios.isEmpty
            ? const Padding(
                padding: EdgeInsets.all(24),
                child: Text(
                  'Synchronisez une fois avec le PC pour télécharger les simulations : '
                  'elles se jouent ensuite sans réseau.',
                ),
              )
            : ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  if (state.pendingLabs.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Text(
                        '${state.pendingLabs.length} partie(s) à envoyer au PC à la prochaine '
                        'synchronisation.',
                      ),
                    ),
                  for (final vScenario in vScenarios)
                    Card(
                      child: ListTile(
                        leading: const Icon(Icons.build_outlined),
                        title: Text(vScenario['title'] as String),
                        subtitle: Text('${vScenario['domain']} · ${vScenario['symptom']}'),
                        trailing: Text(describeBest(state.bestLabScore(vScenario['id'] as String))),
                        isThreeLine: true,
                        onTap: () => Navigator.of(pContext).push(
                          MaterialPageRoute<void>(
                            builder: (_) =>
                                TroubleshootingScreen(state: state, scenario: vScenario),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
      ),
    );
  }
}

/// Meilleur score en étoiles, ou rien si le scénario n'a pas encore été résolu.
String describeBest(int? pScore) {
  final rText =
      pScore == null ? '' : '${'★' * starsOf(pScore, const TroubleshootingRules())}\n$pScore';

  return rText;
}

class TroubleshootingScreen extends StatefulWidget {
  const TroubleshootingScreen({super.key, required this.state, required this.scenario});

  final RevisionState state;
  final Map<String, dynamic> scenario;

  @override
  State<TroubleshootingScreen> createState() => _TroubleshootingScreenState();
}

class _TroubleshootingScreenState extends State<TroubleshootingScreen> {
  final actions = <String>[];
  bool recorded = false;

  Map<String, dynamic> get game =>
      playScenario(widget.scenario, actions, widget.state.troubleshootingRules);

  Future<void> act(String pAction) async {
    setState(() => actions.add(pAction));

    final vGame = game;

    if (vGame['solved'] == true && !recorded) {
      recorded = true;
      await widget.state.recordTroubleshooting(
        widget.scenario['id'] as String,
        List<String>.from(actions),
        vGame['score'] as int,
      );
    }
  }

  void restart() => setState(() {
        actions.clear();
        recorded = false;
      });

  @override
  Widget build(BuildContext pContext) {
    final vGame = game;
    final vDone = List<String>.from(vGame['done'] as List);
    final vWrong = List<String>.from(vGame['wrong'] as List);
    final vSolved = vGame['solved'] == true;
    final vTheme = Theme.of(pContext);
    final vRules = widget.state.troubleshootingRules;

    return Scaffold(
      appBar: AppBar(title: Text(widget.scenario['title'] as String)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(widget.scenario['symptom'] as String, style: vTheme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Text(widget.scenario['machine'] as String, style: vTheme.textTheme.bodySmall),
          const SizedBox(height: 12),
          Text('Temps passé : ${vGame['minutes']} min', style: vTheme.textTheme.labelLarge),
          if (vSolved)
            Card(
              color: vTheme.colorScheme.primaryContainer,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Panne résolue : ${vGame['score']} points '
                      '${'★' * (vGame['stars'] as int)}',
                      style: vTheme.textTheme.titleMedium,
                    ),
                    Text(
                      'Un technicien expérimenté met ${widget.scenario['best_minutes']} min. '
                      '+${xpOf(vGame['score'] as int, vRules)} XP au retour sur le PC.',
                    ),
                    if (vGame['proven'] != true)
                      const Text('Réparation devinée sans mesure qui la prouve : score plafonné.'),
                    const SizedBox(height: 8),
                    Text(widget.scenario['explanation'] as String? ?? ''),
                    TextButton(onPressed: restart, child: const Text('Rejouer')),
                  ],
                ),
              ),
            ),
          if (!vSolved) ...[
            const SizedBox(height: 8),
            Text('Mesures', style: vTheme.textTheme.titleSmall),
            for (final vCheck in widget.scenario['checks'] as List)
              ListTile(
                dense: true,
                enabled: !vDone.contains((vCheck as Map)['id']),
                leading: const Icon(Icons.search),
                title: Text(vCheck['label'] as String),
                trailing: Text('${vCheck['minutes']} min'),
                onTap: () => act('$checkPrefix${vCheck['id']}'),
              ),
            Text('Réparations', style: vTheme.textTheme.titleSmall),
            for (final vCause in widget.scenario['causes'] as List)
              ListTile(
                dense: true,
                enabled: !vWrong.contains((vCause as Map)['id']),
                leading: const Icon(Icons.handyman_outlined),
                title: Text(vCause['label'] as String),
                trailing: Text('${vCause['minutes']} min'),
                onTap: () => act('$repairPrefix${vCause['id']}'),
              ),
          ],
          const SizedBox(height: 12),
          Text("Journal d'intervention", style: vTheme.textTheme.titleSmall),
          for (final vEntry in (vGame['log'] as List).reversed)
            ListTile(
              dense: true,
              title: Text((vEntry as Map)['label'] as String),
              subtitle: Text(vEntry['result'] as String),
              trailing: Text('${vEntry['minutes']} min'),
            ),
        ],
      ),
    );
  }
}
