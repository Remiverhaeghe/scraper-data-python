// Auto-évaluation des compétences : un niveau de 0 à 10 par compétence, envoyé
// au PC à la synchronisation, où il pèse dans le score des offres.

import 'package:flutter/material.dart';

import '../revision_state.dart';

const maxSkillLevel = 10;

class SkillsScreen extends StatefulWidget {
  const SkillsScreen({super.key, required this.state});

  final RevisionState state;

  @override
  State<SkillsScreen> createState() => _SkillsScreenState();
}

class _SkillsScreenState extends State<SkillsScreen> {
  late final levels = {
    for (final vItem in widget.state.skillGrid)
      vItem['skill'] as String: (vItem['level'] as num).toInt(),
  };

  Future<void> save() async {
    final vMessenger = ScaffoldMessenger.of(context);

    await widget.state.saveSkillLevels(levels);

    vMessenger.showSnackBar(
      const SnackBar(content: Text('Niveaux enregistrés : envoyés au PC à la synchronisation.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final Widget vBody = levels.isEmpty
        ? const Center(
            child: Padding(
              padding: EdgeInsets.all(24),
              child: Text('Synchronisez avec le PC pour recevoir la grille.'),
            ),
          )
        : ListView(
            padding: const EdgeInsets.all(16),
            children: [
              const Text(
                'Niveau de 0 (inconnue) à 10. Dès 5, la compétence compte dans le score '
                'des offres ; de 1 à 4, ses thèmes sont proposés en priorité.',
              ),
              for (final vSkill in levels.keys)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(vSkill),
                  trailing: Text(levels[vSkill] == 0 ? '—' : '${levels[vSkill]}/10'),
                  subtitle: Slider(
                    value: levels[vSkill]!.toDouble(),
                    max: maxSkillLevel.toDouble(),
                    divisions: maxSkillLevel,
                    label: '${levels[vSkill]}',
                    onChanged: (pValue) => setState(() => levels[vSkill] = pValue.round()),
                  ),
                ),
            ],
          );

    final rScreen = Scaffold(
      appBar: AppBar(
        title: const Text('Auto-évaluation'),
        actions: [
          if (levels.isNotEmpty)
            IconButton(tooltip: 'Enregistrer', onPressed: save, icon: const Icon(Icons.save)),
        ],
      ),
      body: vBody,
    );

    return rScreen;
  }
}
