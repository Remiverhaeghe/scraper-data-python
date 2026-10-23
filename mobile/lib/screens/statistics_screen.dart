// Statistiques de révision : chiffres d'ensemble, activité des derniers jours,
// réussite par thème et examens blancs.

import 'package:flutter/material.dart';

import '../logic/statistics.dart';
import '../revision_state.dart';
import '../theme.dart';

class StatisticsScreen extends StatelessWidget {
  const StatisticsScreen({super.key, required this.state});

  final RevisionState state;

  @override
  Widget build(BuildContext context) {
    final vStatistics = state.statistics;
    final vDays = readDayActivity(vStatistics);
    final vThemes = state.package == null
        ? const <ThemeStatistics>[]
        : buildThemeStatistics(state.package!, state.schedule, DateTime.now());
    final vTextTheme = Theme.of(context).textTheme;

    final rScreen = Scaffold(
      appBar: AppBar(title: const Text('Statistiques')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Wrap(
                spacing: 24,
                runSpacing: 12,
                children: [
                  _Figure(value: '${vStatistics['answers'] ?? 0}', label: 'réponses'),
                  _Figure(
                    value: vStatistics['rate'] == null ? '–' : '${vStatistics['rate']} %',
                    label: 'de réussite',
                  ),
                  _Figure(value: '${vStatistics['streak'] ?? 0} j', label: 'de suite'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text('Derniers jours', style: vTextTheme.titleMedium),
          Text(
            'À la dernière synchronisation ; en vert, les réponses justes.',
            style: vTextTheme.bodySmall,
          ),
          const SizedBox(height: 8),
          if (vDays.isEmpty)
            const Text('Aucune activité reçue : synchronisez une première fois.')
          else
            ActivityChart(days: vDays),
          const SizedBox(height: 24),
          Text('Par thème', style: vTextTheme.titleMedium),
          Text('Les moins acquis en premier.', style: vTextTheme.bodySmall),
          const SizedBox(height: 8),
          for (final vTheme in vThemes) ThemeProgress(theme: vTheme),
          if (state.examResults.isNotEmpty) ...[
            const SizedBox(height: 24),
            Text('Examens blancs', style: vTextTheme.titleMedium),
            for (final vResult in state.examResults.take(10))
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(vResult.title),
                subtitle: Text(
                  '${vResult.finishedAt.day.toString().padLeft(2, '0')}/'
                  '${vResult.finishedAt.month.toString().padLeft(2, '0')} · '
                  '${vResult.correct} / ${vResult.count}',
                ),
                trailing: Text('${vResult.score} %', style: vTextTheme.titleMedium),
              ),
          ],
        ],
      ),
    );

    return rScreen;
  }
}

/// Barres des réponses par jour, la part juste en vert.
class ActivityChart extends StatelessWidget {
  const ActivityChart({super.key, required this.days});

  final List<DayActivity> days;

  static const height = 120.0;

  @override
  Widget build(BuildContext context) {
    final vMaximum = days.fold<int>(1, (vMax, vDay) => vDay.answers > vMax ? vDay.answers : vMax);
    final vTheme = Theme.of(context);

    final rChart = SizedBox(
      height: height + 36,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          for (final vDay in days)
            Expanded(
              child: Semantics(
                label: '${vDay.date.day}/${vDay.date.month} : ${vDay.answers} réponse(s), '
                    '${vDay.correct} juste(s)',
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    if (vDay.answers > 0)
                      Text('${vDay.answers}', style: vTheme.textTheme.labelSmall),
                    Container(
                      height: height * vDay.answers / vMaximum,
                      margin: const EdgeInsets.symmetric(horizontal: 2),
                      color: vTheme.colorScheme.primaryContainer,
                      alignment: Alignment.bottomCenter,
                      child: FractionallySizedBox(
                        heightFactor: vDay.answers == 0 ? 0 : vDay.correct / vDay.answers,
                        child: Container(color: successColor),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text('${vDay.date.day}', style: vTheme.textTheme.labelSmall),
                  ],
                ),
              ),
            ),
        ],
      ),
    );

    return rChart;
  }
}

/// Avancement d'un thème : barre des questions acquises et nombre à revoir.
class ThemeProgress extends StatelessWidget {
  const ThemeProgress({super.key, required this.theme});

  final ThemeStatistics theme;

  @override
  Widget build(BuildContext context) {
    final vTextTheme = Theme.of(context).textTheme;

    final rProgress = Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(theme.label, style: vTextTheme.bodyLarge)),
              Text('${theme.acquired} / ${theme.total}'),
            ],
          ),
          const SizedBox(height: 4),
          LinearProgressIndicator(
            value: theme.share,
            minHeight: 8,
            borderRadius: BorderRadius.circular(4),
            color: theme.share >= 0.8 ? successColor : null,
          ),
          if (theme.due > 0)
            Text("${theme.due} à revoir aujourd'hui", style: vTextTheme.bodySmall),
        ],
      ),
    );

    return rProgress;
  }
}

class _Figure extends StatelessWidget {
  const _Figure({required this.value, required this.label});

  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    final vTextTheme = Theme.of(context).textTheme;

    final rFigure = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(value, style: vTextTheme.headlineSmall),
        Text(label, style: vTextTheme.bodySmall),
      ],
    );

    return rFigure;
  }
}
