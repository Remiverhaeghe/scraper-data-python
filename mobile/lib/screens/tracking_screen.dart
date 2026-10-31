// Candidatures en cours lisibles hors ligne, et fiche de préparation des
// entretiens à venir : pitch, questions pièges, questions à poser.

import 'package:flutter/material.dart';

import '../logic/interview_alerts.dart';
import '../revision_state.dart';

/// Date et heure lisibles, « 27/10 à 14:30 », ou la date seule.
String formatMoment(String? pValue) {
  final vDate = DateTime.tryParse(pValue ?? '');

  if (vDate == null) {
    return '';
  }

  final vDay = '${twoDigits(vDate.day)}/${twoDigits(vDate.month)}';

  final rText = (pValue ?? '').length > 10
      ? '$vDay à ${twoDigits(vDate.hour)}:${twoDigits(vDate.minute)}'
      : vDay;

  return rText;
}

/// Ligne de détail d'une candidature : prochain entretien, sinon prochaine relance.
String describeTracking(Map<String, dynamic> pApplication) {
  final vInterview = formatMoment(pApplication['interview_at'] as String?);
  // Une relance se prévoit au jour près : l'heure enregistrée n'a pas de sens.
  final vFollowUpDate = '${pApplication['follow_up_date'] ?? ''}';
  final vFollowUp = formatMoment(
    vFollowUpDate.length > 10 ? vFollowUpDate.substring(0, 10) : vFollowUpDate,
  );

  final rText = [
    pApplication['company'],
    pApplication['status_label'],
    if (vInterview.isNotEmpty) 'entretien le $vInterview',
    if (vInterview.isEmpty && vFollowUp.isNotEmpty) 'relance le $vFollowUp',
  ].where((vPart) => vPart != null && '$vPart'.isNotEmpty).join(' · ');

  return rText;
}

class TrackingScreen extends StatelessWidget {
  const TrackingScreen({super.key, required this.state});

  final RevisionState state;

  @override
  Widget build(BuildContext context) {
    final vApplications = state.trackedApplications;

    final rScreen = Scaffold(
      appBar: AppBar(title: const Text('Mes candidatures')),
      body: vApplications.isEmpty
          ? const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text(
                  'Aucune candidature en cours reçue du PC : synchronisez pour la mettre à jour.',
                  textAlign: TextAlign.center,
                ),
              ),
            )
          : ListView(
              children: [
                for (final vApplication in vApplications)
                  Builder(
                    builder: (pContext) {
                      final vSheet = state.sheetOf(vApplication);

                      return ListTile(
                        title: Text('${vApplication['title'] ?? 'Offre sans titre'}'),
                        subtitle: Text(describeTracking(vApplication)),
                        trailing: vSheet == null ? null : const Icon(Icons.description_outlined),
                        onTap: vSheet == null
                            ? null
                            : () => Navigator.of(pContext).push(
                                  MaterialPageRoute<void>(
                                    builder: (_) => SheetScreen(sheet: vSheet),
                                  ),
                                ),
                      );
                    },
                  ),
              ],
            ),
    );

    return rScreen;
  }
}

/// Fiche de préparation d'un entretien, telle que construite par le PC.
class SheetScreen extends StatelessWidget {
  const SheetScreen({super.key, required this.sheet});

  final Map<String, dynamic> sheet;

  @override
  Widget build(BuildContext context) {
    final vTheme = Theme.of(context);
    final vHeader = List<String>.from(sheet['header'] as List? ?? const []);
    final vSections = [
      for (final vSection in sheet['sections'] as List? ?? const [])
        (
          '${(vSection as List)[0]}',
          List<String>.from(vSection[1] as List),
        ),
    ];

    final rScreen = Scaffold(
      appBar: AppBar(title: const Text('Fiche de préparation')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('${sheet['title'] ?? ''}', style: vTheme.textTheme.titleLarge),
          for (final vLine in vHeader) Text(vLine, style: vTheme.textTheme.bodyMedium),
          const SizedBox(height: 8),
          if (sheet['mission'] case final Map vMission) MissionCard(mission: vMission),
          for (final (vName, vLines) in vSections)
            ExpansionTile(
              title: Text(vName),
              initiallyExpanded: vName.startsWith('Mon pitch'),
              childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
              expandedCrossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final vLine in vLines)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: SelectableText('• $vLine'),
                  ),
              ],
            ),
        ],
      ),
    );

    return rScreen;
  }
}

/// Avancement de la mission d'entretien, cochée sur le PC.
class MissionCard extends StatelessWidget {
  const MissionCard({super.key, required this.mission});

  final Map mission;

  @override
  Widget build(BuildContext context) {
    final vTheme = Theme.of(context);
    final vPercent = (mission['percent'] as num? ?? 0).toInt();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Mission entretien · $vPercent %', style: vTheme.textTheme.titleMedium),
            const SizedBox(height: 6),
            LinearProgressIndicator(value: vPercent / 100),
            if (mission['completed_at'] != null)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(
                  'Mission accomplie : vous êtes prêt pour le jour J.',
                  style: TextStyle(color: Colors.green.shade700),
                ),
              ),
            for (final vStep in mission['steps'] as List? ?? const [])
              ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: Icon(
                  (vStep as Map)['done'] == true
                      ? Icons.check_circle
                      : Icons.radio_button_unchecked,
                  color: vStep['done'] == true ? Colors.green.shade700 : null,
                ),
                title: Text('${vStep['label']}'),
                subtitle: Text(
                  '${vStep['task']}${'${vStep['detail'] ?? ''}'.isEmpty ? '' : '\n${vStep['detail']}'}',
                ),
              ),
            Text('Les étapes se cochent sur le PC.', style: vTheme.textTheme.bodySmall),
          ],
        ),
      ),
    );
  }
}
