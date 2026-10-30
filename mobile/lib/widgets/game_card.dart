// Carte de progression de l'accueil : niveau et série reçus du PC, quêtes du
// jour et accès au jeu « Contre la montre ».

import 'package:flutter/material.dart';

import '../revision_state.dart';
import '../screens/time_attack_screen.dart';
import '../theme.dart';

class GameCard extends StatelessWidget {
  const GameCard({super.key, required this.state});

  final RevisionState state;

  Widget buildLevel(BuildContext pContext, Map<String, dynamic> pGame) {
    final vTheme = Theme.of(pContext);
    final vInLevel = (pGame['xp_in_level'] as num?)?.toDouble() ?? 0;
    final vForLevel = (pGame['xp_for_level'] as num?)?.toDouble() ?? 1;
    final vStreak = (pGame['streak'] as num?)?.toInt() ?? 0;

    final rLevel = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            CircleAvatar(
              radius: 20,
              backgroundColor: vTheme.colorScheme.primary,
              child: Text(
                '${pGame['level']}',
                style: TextStyle(
                  color: vTheme.colorScheme.onPrimary,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${pGame['title']}', style: vTheme.textTheme.titleMedium),
                  Text(
                    '${vInLevel.toInt()} / ${vForLevel.toInt()} XP · prochain : '
                    '${pGame['next_title']}',
                    style: vTheme.textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            Icon(Icons.local_fire_department, color: Colors.orange.shade700),
            Text(
              '$vStreak',
              semanticsLabel: 'Série de $vStreak jours',
              style: vTheme.textTheme.titleMedium?.copyWith(color: Colors.orange.shade800),
            ),
          ],
        ),
        const SizedBox(height: 10),
        // La barre se remplit en douceur à chaque nouvelle progression reçue.
        TweenAnimationBuilder<double>(
          tween: Tween(begin: 0, end: vInLevel / vForLevel),
          duration: const Duration(milliseconds: 800),
          curve: Curves.easeOutCubic,
          builder: (_, pValue, __) => LinearProgressIndicator(
            value: pValue,
            minHeight: 8,
            borderRadius: BorderRadius.circular(4),
          ),
        ),
      ],
    );

    return rLevel;
  }

  /// Nombre de trophées et les trois derniers obtenus, du plus récent au plus ancien.
  Widget buildTrophies(BuildContext pContext, Map<String, dynamic> pGame) {
    final vAll = [
      for (final vItem in pGame['achievements'] as List? ?? const [])
        Map<String, dynamic>.from(vItem as Map),
    ];
    final vUnlocked = vAll.where((vItem) => vItem['unlocked'] == true).toList()
      ..sort((vA, vB) => '${vB['unlocked_on']}'.compareTo('${vA['unlocked_on']}'));

    if (vAll.isEmpty) {
      return const SizedBox.shrink();
    }

    final rTrophies = Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Wrap(
        spacing: 6,
        runSpacing: 6,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          Icon(Icons.emoji_events, color: Colors.amber.shade700, size: 20),
          Text('Trophées : ${vUnlocked.length} / ${vAll.length}'),
          for (final vItem in vUnlocked.take(3))
            Chip(
              label: Text('${vItem['title']}'),
              visualDensity: VisualDensity.compact,
              backgroundColor: Colors.amber.shade100,
            ),
        ],
      ),
    );

    return rTrophies;
  }

  Widget buildQuest(BuildContext pContext, Map<String, dynamic> pQuest) {
    final vDone = pQuest['done'] == true;
    final vColor = vDone ? successColorOf(pContext) : null;

    final rQuest = ListTile(
      dense: true,
      contentPadding: EdgeInsets.zero,
      leading: AnimatedSwitcher(
        duration: const Duration(milliseconds: 300),
        transitionBuilder: (pChild, pAnimation) => ScaleTransition(scale: pAnimation, child: pChild),
        child: Icon(
          vDone
              ? Icons.check_circle
              : pQuest['weekly'] == true
                  ? Icons.calendar_month_outlined
                  : Icons.radio_button_unchecked,
          key: ValueKey<bool>(vDone),
          color: vColor,
        ),
      ),
      title: Text(
        '${pQuest['weekly'] == true ? 'Semaine · ' : ''}${pQuest['label']}',
        style: vDone ? const TextStyle(decoration: TextDecoration.lineThrough) : null,
      ),
      trailing: Text('${pQuest['progress']} / ${pQuest['target']} · +${pQuest['xp']} XP'),
    );

    return rQuest;
  }

  @override
  Widget build(BuildContext context) {
    final vGame = state.game;

    final rCard = Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (vGame == null)
              const Text('Votre niveau et vos quêtes arrivent à la prochaine synchronisation.')
            else ...[
              buildLevel(context, vGame),
              buildTrophies(context, vGame),
              const SizedBox(height: 8),
              for (final vQuest in vGame['quests'] as List? ?? const [])
                buildQuest(context, Map<String, dynamic>.from(vQuest as Map)),
            ],
            if (state.package != null) ...[
              const SizedBox(height: 8),
              FilledButton.icon(
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(builder: (_) => TimeAttackScreen(state: state)),
                ),
                icon: const Icon(Icons.timer_outlined),
                label: Text(
                  'Contre la montre · 60 s'
                  '${state.timeAttackBest > 0 ? ' · record ${state.timeAttackBest}' : ''}',
                ),
              ),
            ],
          ],
        ),
      ),
    );

    return rCard;
  }
}
