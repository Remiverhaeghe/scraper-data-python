// Paramètres : connexion au PC, apparence, objectif du jour et notifications.

import 'package:flutter/material.dart';

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
      appBar: AppBar(title: const Text('Paramètres')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Card(
            child: ListTile(
              leading: const Icon(Icons.computer),
              title: const Text('Connexion au PC'),
              subtitle: Text(getHost(state.settings?.address) ?? 'Pas encore connecté'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute<void>(builder: (_) => ConnectScreen(state: state)),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text('Apparence', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
          ListenableBuilder(
            listenable: state,
            builder: (_, __) => SegmentedButton<String>(
              segments: const [
                ButtonSegment(
                    value: 'system', label: Text('Auto'), icon: Icon(Icons.brightness_auto)),
                ButtonSegment(value: 'light', label: Text('Clair'), icon: Icon(Icons.light_mode)),
                ButtonSegment(value: 'dark', label: Text('Sombre'), icon: Icon(Icons.dark_mode)),
              ],
              selected: {state.appearance},
              onSelectionChanged: (pChoice) => state.setDisplay(pAppearance: pChoice.first),
            ),
          ),
          const SizedBox(height: 16),
          Text('Taille du texte', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
          ListenableBuilder(
            listenable: state,
            builder: (_, __) => SegmentedButton<double>(
              segments: const [
                ButtonSegment(value: 1.0, label: Text('Normale')),
                ButtonSegment(value: 1.15, label: Text('Grande')),
                ButtonSegment(value: 1.3, label: Text('Très grande')),
              ],
              selected: {state.textScale},
              onSelectionChanged: (pChoice) => state.setDisplay(pTextScale: pChoice.first),
            ),
          ),
          const SizedBox(height: 16),
          Text('Objectif du jour', style: Theme.of(context).textTheme.titleSmall),
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
              title: const Text('Vibration à la correction'),
              subtitle: const Text('Courte si la réponse est juste, appuyée si elle est fausse'),
              value: state.hapticsEnabled,
              onChanged: (pEnabled) => state.savePreference(hapticsPreference, pEnabled),
            ),
          ),
          ListenableBuilder(
            listenable: state,
            builder: (_, __) => SwitchListTile(
              title: const Text('Alerte des nouvelles offres'),
              subtitle: const Text(
                'Vérifiées toutes les 3 h environ quand le PC est joignable ; '
                'signalées si la correspondance atteint $offerAlertScore %',
              ),
              value: state.offerAlertsEnabled,
              onChanged: (pEnabled) async {
                final vMessenger = ScaffoldMessenger.of(context);
                final vEnabled = await state.setOfferAlerts(pEnabled);

                if (pEnabled && !vEnabled) {
                  vMessenger.showSnackBar(
                    const SnackBar(
                      content: Text('Notifications refusées : autorisez-les dans les réglages.'),
                    ),
                  );
                }
              },
            ),
          ),
          ListenableBuilder(
            listenable: state,
            builder: (_, __) => SwitchListTile(
              title: const Text('Rappel quotidien à 18 h 30'),
              subtitle: const Text('Une notification avec le nombre de questions à revoir'),
              value: state.reminderEnabled,
              onChanged: (pEnabled) async {
                final vMessenger = ScaffoldMessenger.of(context);
                final vEnabled = await state.setReminder(pEnabled);

                if (pEnabled && !vEnabled) {
                  vMessenger.showSnackBar(
                    const SnackBar(
                      content: Text('Notifications refusées : autorisez-les dans les réglages.'),
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
