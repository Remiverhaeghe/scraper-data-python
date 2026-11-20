// Paramètres : connexion au PC, apparence, objectif du jour et notifications.

import 'package:flutter/material.dart';

import '../l10n/texts.dart';
import '../logic/offer_alerts.dart';
import '../revision_state.dart';
import '../services/discovery.dart';
import 'connect_screen.dart';

class SetupScreen extends StatelessWidget {
  const SetupScreen({super.key, required this.state});

  final RevisionState state;

  @override
  Widget build(BuildContext context) {
    final rScreen = Scaffold(
      appBar: AppBar(title: Text(context.texts.setupParametres)),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Card(
            child: ListTile(
              leading: const Icon(Icons.computer),
              title: Text(context.texts.commonConnexionAuPc),
              subtitle: Text(getHost(state.settings?.address) ?? 'Pas encore connecté'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute<void>(builder: (_) => ConnectScreen(state: state)),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text(context.texts.setupApparence, style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
          ListenableBuilder(
            listenable: state,
            builder: (_, __) => SegmentedButton<String>(
              segments: [
                ButtonSegment(
                    value: 'system', label: Text(context.texts.setupAuto), icon: Icon(Icons.brightness_auto)),
                ButtonSegment(value: 'light', label: Text(context.texts.setupClair), icon: Icon(Icons.light_mode)),
                ButtonSegment(value: 'dark', label: Text(context.texts.setupSombre), icon: Icon(Icons.dark_mode)),
              ],
              selected: {state.appearance},
              onSelectionChanged: (pChoice) => state.setDisplay(pAppearance: pChoice.first),
            ),
          ),
          const SizedBox(height: 16),
          Text(context.texts.setupTailleTexte, style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
          ListenableBuilder(
            listenable: state,
            builder: (_, __) => SegmentedButton<double>(
              segments: [
                ButtonSegment(value: 1.0, label: Text(context.texts.setupNormale)),
                ButtonSegment(value: 1.15, label: Text(context.texts.setupGrande)),
                ButtonSegment(value: 1.3, label: Text(context.texts.setupTresGrande)),
              ],
              selected: {state.textScale},
              onSelectionChanged: (pChoice) => state.setDisplay(pTextScale: pChoice.first),
            ),
          ),
          const SizedBox(height: 16),
          Text(context.texts.setupObjectifJour, style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
          ListenableBuilder(
            listenable: state,
            builder: (_, __) => SegmentedButton<int>(
              segments: [
                for (final vGoal in dailyGoals) ButtonSegment(value: vGoal, label: Text('$vGoal')),
              ],
              selected: {state.dailyGoal},
              onSelectionChanged: (pChoice) =>
                  state.savePreference(dailyGoalPreference, pChoice.first),
            ),
          ),
          ListenableBuilder(
            listenable: state,
            builder: (_, __) => SwitchListTile(
              title: Text(context.texts.setupVibrationCorrection),
              subtitle: Text(context.texts.setupCourteSiReponseEst),
              value: state.hapticsEnabled,
              onChanged: (pEnabled) => state.savePreference(hapticsPreference, pEnabled),
            ),
          ),
          ListenableBuilder(
            listenable: state,
            builder: (_, __) => SwitchListTile(
              title: Text(context.texts.setupAlerteNouvellesOffres),
              subtitle: Text(
                context.texts.setupVerifieesToutes3H('${offerAlertScore}'),
              ),
              value: state.offerAlertsEnabled,
              onChanged: (pEnabled) async {
                final vMessenger = ScaffoldMessenger.of(context);
                final vEnabled = await state.setOfferAlerts(pEnabled);

                if (pEnabled && !vEnabled) {
                  vMessenger.showSnackBar(
                    SnackBar(
                      content: Text(context.texts.setupNotificationsRefuseesAutorisezDans),
                    ),
                  );
                }
              },
            ),
          ),
          ListenableBuilder(
            listenable: state,
            builder: (_, __) => SwitchListTile(
              title: Text(context.texts.setupRappelQuotidien18H),
              subtitle: Text(context.texts.setupNotificationAvecNombreQuestions),
              value: state.reminderEnabled,
              onChanged: (pEnabled) async {
                final vMessenger = ScaffoldMessenger.of(context);
                final vEnabled = await state.setReminder(pEnabled);

                if (pEnabled && !vEnabled) {
                  vMessenger.showSnackBar(
                    SnackBar(
                      content: Text(context.texts.setupNotificationsRefuseesAutorisezDans),
                    ),
                  );
                }
              },
            ),
          ),
        ],
      ),
    );

    return rScreen;
  }
}
