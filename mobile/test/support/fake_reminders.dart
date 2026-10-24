// Rappels et alertes simulés, partagés par les tests.

import 'package:jobboard_revision/logic/interview_alerts.dart';
import 'package:jobboard_revision/services/reminders.dart';

/// Rappels simulés : retient les planifications au lieu de notifier.
class FakeReminders implements Reminders {
  FakeReminders({this.granted = true});

  final bool granted;
  final scheduled = <int>[];
  int cancelled = 0;

  @override
  Future<bool> requestPermission() async => granted;

  @override
  Future<void> schedule(int pDueCount) async => scheduled.add(pDueCount);

  @override
  Future<void> cancel() async => cancelled++;

  final shownOffers = <List<Map<String, dynamic>>>[];
  final offerChecks = <bool>[];

  @override
  Future<void> showNewOffers(List<Map<String, dynamic>> pOffers) async => shownOffers.add(pOffers);

  final shownReplies = <List<Map<String, dynamic>>>[];
  final interviewAlerts = <List<InterviewAlert>>[];
  final shownWithdrawn = <List<Map<String, dynamic>>>[];

  @override
  Future<void> showWithdrawn(List<Map<String, dynamic>> pOffers) async =>
      shownWithdrawn.add(pOffers);

  @override
  Future<void> scheduleInterviews(List<InterviewAlert> pAlerts) async =>
      interviewAlerts.add(pAlerts);

  @override
  Future<void> showReplies(List<Map<String, dynamic>> pReplies) async => shownReplies.add(pReplies);

  @override
  Future<void> scheduleOfferChecks(bool pEnabled) async => offerChecks.add(pEnabled);
}
