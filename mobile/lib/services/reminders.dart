// Rappel quotidien de révision et alerte des nouvelles offres, par notification
// locale : aucune donnée ne quitte le téléphone.

import 'dart:developer';

import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_timezone/flutter_timezone.dart';
import 'package:timezone/data/latest_all.dart' as tz_data;
import 'package:timezone/timezone.dart' as tz;
import 'package:workmanager/workmanager.dart';

import '../logic/interview_alerts.dart';

/// Heure du rappel, chaque jour.
const reminderHour = 18;
const reminderMinute = 30;

const reminderId = 1;
const offersNotificationId = 2;
const repliesNotificationId = 3;
const withdrawnNotificationId = 4;

// Rappels d'entretien : identifiants réservés, un par rappel
const firstInterviewAlertId = 100;
const maxInterviewAlerts = 20;

/// Résume une réponse : « Entretien chez Kiabi le 05/11 à 14:00 », « Refus de Kiabi ».
String describeReply(Map<String, dynamic> pReply) {
  final vCompany = '${pReply['company'] ?? 'l\'entreprise'}';

  if (pReply['status'] != 'INTERVIEW') {
    return 'Refus de $vCompany';
  }

  final vDate = DateTime.tryParse('${pReply['interview_at'] ?? ''}');

  final rText = vDate == null
      ? 'Entretien chez $vCompany'
      : 'Entretien chez $vCompany le ${twoDigits(vDate.day)}/${twoDigits(vDate.month)} '
          'à ${twoDigits(vDate.hour)}:${twoDigits(vDate.minute)}';

  return rText;
}

/// Vérification des offres en arrière-plan : Android la lance au mieux toutes les
/// trois heures, seulement avec une connexion réseau.
const offerCheckTask = 'offer-check';
const offerCheckFrequency = Duration(hours: 3);

/// Rappel quotidien ; remplaçable dans les tests.
abstract class Reminders {
  /// Demande l'autorisation d'afficher des notifications ; retourne si elle est accordée.
  Future<bool> requestPermission();

  /// Planifie le rappel de chaque jour avec le nombre de questions à revoir.
  Future<void> schedule(int pDueCount);

  Future<void> cancel();

  /// Signale les nouvelles offres proches du profil, en une seule notification.
  Future<void> showNewOffers(List<Map<String, dynamic>> pOffers);

  /// Signale les réponses de recruteurs repérées par le PC, en une seule notification.
  Future<void> showReplies(List<Map<String, dynamic>> pReplies);

  /// Signale les offres suivies que leur site a retirées.
  Future<void> showWithdrawn(List<Map<String, dynamic>> pOffers);

  /// Remplace les rappels d'entretien par ceux donnés.
  Future<void> scheduleInterviews(List<InterviewAlert> pAlerts);

  /// Lance ou arrête la vérification périodique des offres en arrière-plan.
  Future<void> scheduleOfferChecks(bool pEnabled);
}

class LocalReminders implements Reminders {
  final plugin = FlutterLocalNotificationsPlugin();
  bool initialized = false;

  Future<void> initialize() async {
    if (initialized) {
      return;
    }

    tz_data.initializeTimeZones();
    tz.setLocalLocation(
      tz.getLocation((await FlutterTimezone.getLocalTimezone()).identifier),
    );

    await plugin.initialize(
      settings: const InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
      ),
    );

    initialized = true;
  }

  @override
  Future<bool> requestPermission() async {
    await initialize();

    final vGranted = await plugin
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();

    final rGranted = vGranted ?? false;

    return rGranted;
  }

  @override
  Future<void> schedule(int pDueCount) async {
    await initialize();

    final vNow = tz.TZDateTime.now(tz.local);
    var vNext = tz.TZDateTime(
      tz.local,
      vNow.year,
      vNow.month,
      vNow.day,
      reminderHour,
      reminderMinute,
    );

    if (!vNext.isAfter(vNow)) {
      vNext = vNext.add(const Duration(days: 1));
    }

    // Planification inexacte : Android regroupe le réveil avec d'autres, sans
    // permission d'alarme exacte, à quelques minutes près.
    await plugin.zonedSchedule(
      id: reminderId,
      scheduledDate: vNext,
      title: 'Révision du jour',
      body: pDueCount > 0
          ? '$pDueCount question(s) à revoir : quelques minutes suffisent.'
          : 'Quelques nouvelles questions vous attendent.',
      notificationDetails: const NotificationDetails(
        android: AndroidNotificationDetails(
          'revision',
          'Rappel de révision',
          channelDescription: 'Rappel quotidien des questions à revoir',
        ),
      ),
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      matchDateTimeComponents: DateTimeComponents.time,
    );

    log('Rappel planifié à $reminderHour:$reminderMinute ($pDueCount à revoir)', name: 'rappel');
  }

  @override
  Future<void> cancel() async {
    await initialize();
    await plugin.cancel(id: reminderId);
  }

  @override
  Future<void> showNewOffers(List<Map<String, dynamic>> pOffers) async {
    await initialize();

    final vTitles = [for (final vOffer in pOffers.take(3)) vOffer['title'] ?? 'Offre sans titre'];

    await plugin.show(
      id: offersNotificationId,
      title: pOffers.length == 1
          ? 'Nouvelle offre pour vous'
          : '${pOffers.length} nouvelles offres pour vous',
      body: vTitles.join(' · '),
      notificationDetails: const NotificationDetails(
        android: AndroidNotificationDetails(
          'offers',
          'Nouvelles offres',
          channelDescription: 'Nouvelles offres proches du profil, trouvées par le PC',
        ),
      ),
    );

    log('Notification de ${pOffers.length} nouvelle(s) offre(s)', name: 'offres');
  }

  @override
  Future<void> showReplies(List<Map<String, dynamic>> pReplies) async {
    await initialize();

    await plugin.show(
      id: repliesNotificationId,
      title: pReplies.length == 1
          ? 'Réponse d\'un recruteur'
          : '${pReplies.length} réponses de recruteurs',
      body: pReplies.take(3).map(describeReply).join(' · '),
      notificationDetails: const NotificationDetails(
        android: AndroidNotificationDetails(
          'replies',
          'Réponses des recruteurs',
          channelDescription: 'Refus ou entretien repérés par le PC dans vos e-mails',
        ),
      ),
    );

    log('Notification de ${pReplies.length} réponse(s) de recruteur', name: 'réponses');
  }

  @override
  Future<void> showWithdrawn(List<Map<String, dynamic>> pOffers) async {
    await initialize();

    await plugin.show(
      id: withdrawnNotificationId,
      title: pOffers.length == 1
          ? 'Offre suivie retirée'
          : '${pOffers.length} offres suivies retirées',
      body: pOffers.take(3).map((vOffer) => '${vOffer['title'] ?? 'Offre'}').join(' · '),
      notificationDetails: const NotificationDetails(
        android: AndroidNotificationDetails(
          'withdrawn',
          'Offres retirées',
          channelDescription: 'Offres suivies que leur site ne publie plus',
        ),
      ),
    );

    log('Notification de ${pOffers.length} offre(s) retirée(s)', name: 'offres');
  }

  @override
  Future<void> scheduleInterviews(List<InterviewAlert> pAlerts) async {
    await initialize();

    // Un entretien déplacé ou annulé ne doit pas laisser d'ancien rappel.
    for (var vIndex = 0; vIndex < maxInterviewAlerts; vIndex++) {
      await plugin.cancel(id: firstInterviewAlertId + vIndex);
    }

    for (final (vIndex, vAlert) in pAlerts.take(maxInterviewAlerts).indexed) {
      await plugin.zonedSchedule(
        id: firstInterviewAlertId + vIndex,
        scheduledDate: tz.TZDateTime.from(vAlert.at, tz.local),
        title: vAlert.title,
        body: vAlert.body,
        notificationDetails: const NotificationDetails(
          android: AndroidNotificationDetails(
            'interviews',
            "Rappels d'entretien",
            channelDescription: 'La veille et une heure avant chaque entretien',
          ),
        ),
        androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      );
    }

    log("${pAlerts.length} rappel(s) d'entretien planifié(s)", name: 'entretiens');
  }

  @override
  Future<void> scheduleOfferChecks(bool pEnabled) async {
    if (pEnabled) {
      await Workmanager().registerPeriodicTask(
        offerCheckTask,
        offerCheckTask,
        frequency: offerCheckFrequency,
        constraints: Constraints(networkType: NetworkType.connected),
        existingWorkPolicy: ExistingPeriodicWorkPolicy.update,
      );
    } else {
      await Workmanager().cancelByUniqueName(offerCheckTask);
    }

    log('Vérification des offres en arrière-plan ${pEnabled ? 'activée' : 'arrêtée'}',
        name: 'offres');
  }
}
