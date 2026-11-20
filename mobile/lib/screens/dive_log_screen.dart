// Carnet de plongée : la semaine de révision jour par jour, comparée à la précédente.

import 'package:flutter/material.dart';

import '../l10n/texts.dart';
import '../logic/dive.dart';
import '../revision_state.dart';
import '../theme.dart';
import '../widgets/brand.dart';

class DiveLogScreen extends StatelessWidget {
  const DiveLogScreen({super.key, required this.state, this.today});

  final RevisionState state;

  /// Jour du carnet ; aujourd'hui sauf dans les tests.
  final DateTime? today;

  @override
  Widget build(BuildContext context) {
    final vText = context.texts;
    final vTheme = Theme.of(context);
    final vWeek = diveWeek(state.diveLog, today ?? DateTime.now());
    final vBars = diveBars(vWeek);
    final vDays = [
      vText.diveMonday,
      vText.diveTuesday,
      vText.diveWednesday,
      vText.diveThursday,
      vText.diveFriday,
      vText.diveSaturday,
      vText.diveSunday,
    ];
    final vBest = vWeek.bestDay;

    final rScreen = Scaffold(
      appBar: AppBar(title: Text(vText.diveLogTitle)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
        children: [
          PoolCard(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    vText.diveLogWeek(vWeek.answered),
                    style: vTheme.textTheme.headlineSmall?.copyWith(color: Colors.white),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    vWeek.answered == 0
                        ? vText.diveLogEmpty
                        : vText.diveLogSummary(
                            vWeek.correct,
                            vWeek.activeDays,
                            (vWeek.correct * 100 / vWeek.answered).round(),
                          ),
                    style: vTheme.textTheme.bodyMedium?.copyWith(color: Colors.white),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Semantics(
            label: vText.diveLogChart,
            child: SizedBox(
              height: 160,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  for (final (vIndex, vDay) in vWeek.days.indexed)
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 4),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            Text('${vDay.answered}', style: vTheme.textTheme.labelSmall),
                            const SizedBox(height: 4),
                            TweenAnimationBuilder<double>(
                              tween: Tween(end: vBars[vIndex]),
                              duration: motionOf(context, const Duration(milliseconds: 700)),
                              curve: Curves.easeOutCubic,
                              builder: (_, pValue, __) => Container(
                                height: 4 + 100 * pValue,
                                decoration: BoxDecoration(
                                  gradient: const LinearGradient(
                                    begin: Alignment.topCenter,
                                    end: Alignment.bottomCenter,
                                    colors: [waterColor, deepColor],
                                  ),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                              ),
                            ),
                            const SizedBox(height: 6),
                            Text(vDays[vIndex], style: vTheme.textTheme.labelMedium),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          if (vBest != null)
            ListTile(
              leading: const Icon(Icons.emoji_events_outlined, color: boardColor),
              title: Text(vText.diveLogBestDay(vDays[vBest.day.weekday - 1], vBest.answered)),
            ),
          ListTile(
            leading: Icon(
              vWeek.answered >= vWeek.previousAnswered ? Icons.trending_up : Icons.trending_down,
              color: primaryColor,
            ),
            title: Text(vText.diveLogPrevious(vWeek.previousAnswered)),
          ),
          const SizedBox(height: 8),
          Text(vText.diveLogHelp, style: vTheme.textTheme.bodySmall),
        ],
      ),
    );

    return rScreen;
  }
}
