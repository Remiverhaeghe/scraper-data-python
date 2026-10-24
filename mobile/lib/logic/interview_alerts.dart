// Rappels d'entretien calculés à partir des entretiens reçus du PC : la veille
// au soir, puis une heure avant.

/// Heure du rappel de la veille
const eveningReminderHour = 18;

/// Délai du dernier rappel avant l'entretien
const lastReminderDelay = Duration(hours: 1);

/// Un rappel à afficher : quand, et avec quel texte.
class InterviewAlert {
  const InterviewAlert(this.at, this.title, this.body);

  final DateTime at;
  final String title;
  final String body;
}

String twoDigits(int pValue) => pValue.toString().padLeft(2, '0');

/// Retourne les rappels encore à venir des entretiens donnés, les plus proches d'abord.
List<InterviewAlert> buildInterviewAlerts(
  List<Map<String, dynamic>> pInterviews,
  DateTime pNow,
) {
  final rAlerts = <InterviewAlert>[];

  for (final vInterview in pInterviews) {
    final vAt = DateTime.tryParse('${vInterview['interview_at'] ?? ''}');

    if (vAt == null || !vAt.isAfter(pNow)) {
      continue;
    }

    final vWhere = vInterview['company'] == null ? '' : ' chez ${vInterview['company']}';
    final vTime = '${twoDigits(vAt.hour)}:${twoDigits(vAt.minute)}';
    final vEvening = DateTime(vAt.year, vAt.month, vAt.day - 1, eveningReminderHour);
    final vLast = vAt.subtract(lastReminderDelay);

    if (vEvening.isAfter(pNow)) {
      rAlerts.add(InterviewAlert(
        vEvening,
        'Entretien demain à $vTime',
        '${vInterview['title'] ?? 'Entretien'}$vWhere',
      ));
    }

    if (vLast.isAfter(pNow)) {
      rAlerts.add(InterviewAlert(
        vLast,
        'Entretien dans une heure',
        '${vInterview['title'] ?? 'Entretien'}$vWhere, à $vTime',
      ));
    }
  }

  rAlerts.sort((pFirst, pSecond) => pFirst.at.compareTo(pSecond.at));

  return rAlerts;
}
