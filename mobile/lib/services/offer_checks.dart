// Tâche d'arrière-plan lancée par Android : synchronise avec le PC, ce qui
// envoie les réponses en attente et signale les nouvelles offres.

import 'dart:developer';

import 'package:workmanager/workmanager.dart';

import '../revision_state.dart';
import 'file_store.dart';
import 'reminders.dart';

@pragma('vm:entry-point')
void checkOffersInBackground() {
  Workmanager().executeTask((pTask, _) async {
    final vState = RevisionState(FileRevisionStore(), reminders: LocalReminders());

    await vState.load();

    if (vState.offerAlertsEnabled) {
      await vState.synchronizeQuietly();
    }

    log('Tâche $pTask terminée', name: 'offres');

    return true;
  });
}
