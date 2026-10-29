// Widget de l'écran d'accueil Android : questions à revoir et prochain entretien,
// mis à jour après chaque synchronisation.

import 'dart:developer';

import 'package:flutter/services.dart';
import 'package:home_widget/home_widget.dart';

import '../logic/interview_alerts.dart';

/// Nom de la classe Kotlin qui dessine le widget (android/app/src/main/kotlin).
const widgetProviderName = 'RevisionWidgetProvider';

/// Les deux lignes du widget : révision du jour, puis prochain entretien.
(String, String) buildWidgetLines(
  int pDueCount,
  List<Map<String, dynamic>> pApplications,
  DateTime pNow,
) {
  DateTime? vNext;
  String? vCompany;

  for (final vApplication in pApplications) {
    final vAt = DateTime.tryParse('${vApplication['interview_at'] ?? ''}');

    if (vAt != null && vAt.isAfter(pNow) && (vNext == null || vAt.isBefore(vNext))) {
      vNext = vAt;
      vCompany = (vApplication['company'] ?? vApplication['title']) as String?;
    }
  }

  final vDue = pDueCount == 0
      ? "Rien à revoir aujourd'hui"
      : '$pDueCount question${pDueCount > 1 ? 's' : ''} à revoir';
  final vInterview = vNext == null
      ? 'Aucun entretien prévu'
      : 'Entretien le ${twoDigits(vNext.day)}/${twoDigits(vNext.month)} à '
          '${twoDigits(vNext.hour)}:${twoDigits(vNext.minute)}'
          '${vCompany == null ? '' : ' · $vCompany'}';

  final rLines = (vDue, vInterview);

  return rLines;
}

/// Envoie les lignes au widget ; sans widget posé, Android les garde pour plus tard.
abstract class HomeWidgetUpdater {
  Future<void> show((String, String) pLines);
}

class AndroidHomeWidget implements HomeWidgetUpdater {
  @override
  Future<void> show((String, String) pLines) async {
    try {
      await HomeWidget.saveWidgetData<String>('due', pLines.$1);
      await HomeWidget.saveWidgetData<String>('next', pLines.$2);
      await HomeWidget.updateWidget(androidName: widgetProviderName);
    } on PlatformException catch (vException) {
      // Un widget indisponible n'empêche pas la synchronisation.
      log('Widget non mis à jour : ${vException.message}', name: 'widget');
    }
  }
}
