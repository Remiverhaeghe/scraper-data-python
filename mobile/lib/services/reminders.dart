// Rappel quotidien de révision et alerte des nouvelles offres, par notification
// locale : aucune donnée ne quitte le téléphone.

import 'dart:developer';

import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_timezone/flutter_timezone.dart';
import 'package:timezone/data/latest_all.dart' as tz_data;
import 'package:timezone/timezone.dart' as tz;
import 'package:workmanager/workmanager.dart';

/// Heure du rappel, chaque jour.
const reminderHour = 18;
const reminderMinute = 30;

const reminderId = 1;
const offersNotificationId = 2;

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
