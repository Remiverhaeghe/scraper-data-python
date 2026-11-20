// Bilan d'une série de questions, vue comme un plongeon : réponses, justes et profondeur
// gagnée dans le thème.

import 'package:flutter/material.dart';

import '../l10n/texts.dart';
import '../logic/dive.dart';
import '../theme.dart';
import '../widgets/brand.dart';
import '../widgets/depth_gauge.dart';

class DiveResultScreen extends StatelessWidget {
  const DiveResultScreen({super.key, required this.title, required this.dive, this.onDiveAgain});

  final String title;
  final DiveResult dive;

  /// Repart pour une série dans le même thème ; bouton caché si absent.
  final VoidCallback? onDiveAgain;

  @override
  Widget build(BuildContext context) {
    final vText = context.texts;
    final vTheme = Theme.of(context);
    final vPercent = (diveAccuracy(dive) * 100).round();
    final vVerdict = diveVerdict(dive);

    final rScreen = Scaffold(
      appBar: AppBar(title: Text(title)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 24, 16, 32),
        children: [
          Center(
            child: SplashRings(
              size: 96,
              child: Icon(
                vVerdict == DiveVerdict.shallower ? Icons.waves : Icons.pool,
                size: 48,
                color: primaryColor,
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text(
            switch (vVerdict) {
              DiveVerdict.deeper => vText.diveDeeperTitle,
              DiveVerdict.steady => vText.diveSteadyTitle,
              DiveVerdict.shallower => vText.diveShallowerTitle,
              DiveVerdict.dry => vText.diveDryTitle,
            },
            style: vTheme.textTheme.headlineSmall,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            dive.answered == 0
                ? vText.diveNoAnswer
                : vText.diveScore(dive.answered, dive.correct, vPercent),
            style: vTheme.textTheme.titleMedium,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    vText.diveDepthChange(formatDepth(dive.before), formatDepth(dive.after)),
                    style: vTheme.textTheme.titleSmall,
                  ),
                  const SizedBox(height: 12),
                  DepthGauge(depth: dive.after, before: dive.before, height: 22),
                  const SizedBox(height: 12),
                  Text(
                    switch (vVerdict) {
                      DiveVerdict.deeper => vText.diveDeeperHelp,
                      DiveVerdict.steady => vText.diveSteadyHelp,
                      DiveVerdict.shallower => vText.diveShallowerHelp,
                      DiveVerdict.dry => vText.diveDryHelp,
                    },
                    style: vTheme.textTheme.bodySmall,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
          if (onDiveAgain != null)
            FilledButton.icon(
              onPressed: onDiveAgain,
              icon: const Icon(Icons.replay),
              label: Text(vText.diveAgain),
            ),
          const SizedBox(height: 8),
          OutlinedButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(vText.diveBackToThemes),
          ),
        ],
      ),
    );

    return rScreen;
  }
}
