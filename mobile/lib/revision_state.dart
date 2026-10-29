// État de l'application : contenu, calendrier de révision et réponses en
// attente. Les écrans l'écoutent et se redessinent à chaque changement.

import 'dart:async';
import 'dart:convert';
import 'dart:developer';
import 'dart:math' show Random;

import 'package:flutter/foundation.dart';
import 'package:uuid/uuid.dart';

import 'logic/exam.dart';
import 'logic/grading.dart';
import 'logic/interview_alerts.dart';
import 'logic/offer_alerts.dart';
import 'logic/review.dart';
import 'models/quiz_package.dart';
import 'models/review_state.dart';
import 'services/api_client.dart';
import 'services/discovery.dart';
import 'services/home_widget_service.dart';
import 'services/reminders.dart';
import 'services/revision_store.dart';

/// Le serveur refuse plus de 500 réponses par envoi.
const maxAnswersPerUpload = 500;

/// Réponses accumulées avant un envoi automatique, si le réseau le permet.
const autoSyncEvery = 10;

/// Préférence du rappel quotidien
const reminderPreference = 'reminder_enabled';
const offerAlertPreference = 'offer_alerts';

/// Réponses de recruteurs déjà notifiées, par identifiant.
const notifiedRepliesPreference = 'notified_replies';

/// Offres suivies retirées déjà notifiées, par source et identifiant.
const notifiedWithdrawnPreference = 'notified_withdrawn';

/// Apparence choisie : system (celle du téléphone), light ou dark.
const appearancePreference = 'appearance';
const appearances = ['system', 'light', 'dark'];

/// Questions signalées, pas encore envoyées au PC
const flaggedPreference = 'flagged_questions';

/// Objectif de réponses par jour, et réponses déjà données ce jour-là
const dailyGoalPreference = 'daily_goal';
const goalDayPreference = 'goal_day';
const goalCountPreference = 'goal_count';
const defaultDailyGoal = 15;
const dailyGoals = [10, 15, 25, 40];

/// Statuts donnés aux offres sur le téléphone, pas encore envoyés au PC
const pendingStatusPreference = 'pending_status';

/// Notes rapides prises sur une offre, pas encore envoyées au PC
const pendingNotesPreference = 'pending_notes';

/// Candidatures en cours et fiches des entretiens à venir, lisibles hors ligne
const trackingPreference = 'tracking';

/// Progression reçue du PC (niveau, série, quêtes) et dernier niveau fêté ici
const gamePreference = 'game';
const celebratedLevelPreference = 'celebrated_level';

/// Meilleur score du jeu « Contre la montre »
const timeAttackBestPreference = 'time_attack_best';

/// Avant un entretien, la fiche de préparation est proposée sur l'accueil.
const interviewSheetLead = Duration(hours: 24);

/// Taille d'une note rapide, la même limite que côté PC
const maxNoteLength = 1000;

/// Simulation d'entretien : questions reçues du PC et séries pas encore envoyées
const interviewPreference = 'interview_content';
const pendingInterviewPreference = 'pending_interview';

/// Auto-évaluation : grille reçue du PC et niveaux saisis pas encore envoyés
const skillGridPreference = 'skill_grid';
const pendingSkillsPreference = 'pending_skills';

/// Statuts qu'une offre peut recevoir sur le téléphone, avec leur libellé
const offerStatuses = {
  'INTERESTED': 'Intéressé',
  'APPLIED': 'Postulé',
  'IGNORED': 'Ignorée',
};

/// Vibration à la correction : courte si juste, appuyée si faux
const hapticsPreference = 'haptics';

/// Agrandissement du texte, en plus de celui réglé sur le téléphone.
const textScalePreference = 'text_scale';
const textScales = [1.0, 1.15, 1.3];

/// Bilan d'une synchronisation, montré à l'utilisateur.
class SyncReport {
  const SyncReport({required this.sent, required this.rejected, required this.contentUpdated});

  final int sent;
  final int rejected;
  final bool contentUpdated;

  String describe() {
    final rText = [
      if (sent > 0) '$sent réponse(s) envoyée(s)',
      if (rejected > 0) '$rejected refusée(s) par le serveur',
      contentUpdated ? 'questions mises à jour' : 'questions déjà à jour',
    ].join(', ');

    return rText;
  }
}

class RevisionState extends ChangeNotifier {
  RevisionState(
    this.store, {
    ApiClient Function(ServerSettings)? pClientFactory,
    Random? pRandom,
    ServerDiscovery? pDiscovery,
    this.reminders,
    this.homeWidget,
  })  : clientFactory = pClientFactory ?? ((pSettings) => ApiClient(pSettings)),
        random = pRandom ?? Random(),
        discovery = pDiscovery ?? ServerDiscovery();

  final RevisionStore store;
  final ApiClient Function(ServerSettings) clientFactory;

  /// Rappel quotidien ; absent dans les tests, qui n'ont pas de notifications.
  final Reminders? reminders;

  /// Widget de l'écran d'accueil ; absent dans les tests.
  final HomeWidgetUpdater? homeWidget;

  /// Recherche du serveur sur le Wi-Fi, quand son adresse est inconnue ou a changé.
  final ServerDiscovery discovery;

  /// Tirage des questions et mélange des réponses, sans enjeu de sécurité.
  final Random random;

  ServerSettings? settings;
  QuizPackage? package;
  Map<String, dynamic> progress = {};
  List<Map<String, dynamic>> pending = [];
  Map<String, ReviewState> schedule = {};
  List<ExamResult> examResults = [];

  /// Nouvelles offres de la semaine, reçues à la synchronisation.
  List<Map<String, dynamic>> offers = [];
  Map<String, dynamic> preferences = {};
  bool syncing = false;

  bool get reminderEnabled => preferences[reminderPreference] == true;

  bool get offerAlertsEnabled => preferences[offerAlertPreference] == true;

  bool get hapticsEnabled => preferences[hapticsPreference] != false;

  Set<String> get flaggedIds =>
      {for (final vId in preferences[flaggedPreference] as List? ?? const []) vId as String};

  int get dailyGoal {
    final vGoal = (preferences[dailyGoalPreference] as num?)?.toInt();

    final rGoal = dailyGoals.contains(vGoal) ? vGoal! : defaultDailyGoal;

    return rGoal;
  }

  /// Réponses données aujourd'hui, pour l'objectif du jour.
  int get answersToday {
    final vToday = DateTime.now().toIso8601String().split('T').first;

    final rCount = preferences[goalDayPreference] == vToday
        ? (preferences[goalCountPreference] as num? ?? 0).toInt()
        : 0;

    return rCount;
  }

  /// Candidatures en cours et thèmes à revoir pour chacune, reçus du PC.
  List<Map<String, dynamic>> get applications => [
        for (final vItem in progress['applications'] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  Future<void> savePreference(String pKey, Object pValue) async {
    preferences = {...preferences, pKey: pValue};
    await store.savePreferences(preferences);
    notifyListeners();
  }

  List<String> get interviewThemes => [
        for (final vTheme
            in (preferences[interviewPreference] as Map?)?['themes'] as List? ?? const [])
          vTheme as String,
      ];

  List<Map<String, dynamic>> get interviewQuestions => [
        for (final vItem
            in (preferences[interviewPreference] as Map?)?['questions'] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  List<Map<String, dynamic>> get pendingInterview => [
        for (final vItem in preferences[pendingInterviewPreference] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  /// Grille d'auto-évaluation : compétence et niveau de 0 à 10.
  List<Map<String, dynamic>> get skillGrid => [
        for (final vItem in preferences[skillGridPreference] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  /// Garde une série de simulation, envoyée au PC à la synchronisation suivante.
  Future<void> recordInterviewSeries(String pTheme, List<Map<String, dynamic>> pResults) =>
      savePreference(pendingInterviewPreference, [
        ...pendingInterview,
        {'theme': pTheme, 'finished_at': DateTime.now().toIso8601String(), 'results': pResults},
      ]);

  /// Enregistre les niveaux saisis : affichés tout de suite, envoyés ensuite.
  Future<void> saveSkillLevels(Map<String, int> pLevels) async {
    preferences = {
      ...preferences,
      skillGridPreference: [
        for (final vEntry in pLevels.entries) {'skill': vEntry.key, 'level': vEntry.value},
      ],
      pendingSkillsPreference: pLevels,
    };
    await store.savePreferences(preferences);
    notifyListeners();
  }

  /// Échange simulation et auto-évaluation avec le PC ; un serveur plus ancien
  /// qui ne les connaît pas n'empêche pas le reste de la synchronisation.
  Future<void> exchangeInterviewAndSkills(ApiClient pClient) async {
    try {
      if (pendingInterview.isNotEmpty) {
        await pClient.uploadInterview(pendingInterview);
        await savePreference(pendingInterviewPreference, <Map<String, dynamic>>[]);
      }

      final vPendingSkills = preferences[pendingSkillsPreference] as Map?;

      if (vPendingSkills != null) {
        await pClient.uploadSkills(Map<String, int>.from(vPendingSkills));
        preferences = {...preferences}..remove(pendingSkillsPreference);
      }

      final vInterview = await pClient.downloadInterview();
      final vSkills = await pClient.downloadSkills();

      preferences = {
        ...preferences,
        interviewPreference: vInterview,
        skillGridPreference: vSkills['grid'] as List? ?? const [],
      };
      await store.savePreferences(preferences);
    } on ApiException catch (vException) {
      if (vException.unreachable) {
        rethrow;
      }

      log('Simulation ou auto-évaluation non échangée : ${vException.message}', name: 'sync');
    } on FormatException catch (vException) {
      log('Réponse illisible pour la simulation : ${vException.message}', name: 'sync');
    }
  }

  List<Map<String, dynamic>> get pendingStatuses => [
        for (final vItem in preferences[pendingStatusPreference] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  /// Donne un statut à une offre : affiché tout de suite, envoyé au PC ensuite.
  Future<void> setOfferStatus(Map<String, dynamic> pOffer, String pStatus) async {
    offers = [
      for (final vOffer in offers)
        if (vOffer['source'] == pOffer['source'] && vOffer['source_id'] == pOffer['source_id'])
          {...vOffer, 'status': pStatus}
        else
          vOffer,
    ];
    await store.saveOffers(offers);

    // Seul le dernier statut d'une offre compte : l'ancien changement est remplacé.
    await savePreference(pendingStatusPreference, [
      for (final vChange in pendingStatuses)
        if (vChange['source'] != pOffer['source'] || vChange['source_id'] != pOffer['source_id'])
          vChange,
      {'source': pOffer['source'], 'source_id': pOffer['source_id'], 'status': pStatus},
    ]);
  }

  List<Map<String, dynamic>> get pendingNotes => [
        for (final vItem in preferences[pendingNotesPreference] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  /// Garde une note rapide sur une offre, envoyée au PC à la synchronisation.
  Future<void> addOfferNote(Map<String, dynamic> pOffer, String pText) async {
    final vText = pText.trim();

    if (vText.isEmpty) {
      return;
    }

    await savePreference(pendingNotesPreference, [
      ...pendingNotes,
      {
        'source': pOffer['source'],
        'source_id': pOffer['source_id'],
        'text': vText.length > maxNoteLength ? vText.substring(0, maxNoteLength) : vText,
        'written_at': DateTime.now().toIso8601String(),
      },
    ]);
  }

  /// Retire une question fausse ou ambiguë des tirages et la signale au PC.
  Future<void> flagQuestion(String pQuestionId) async {
    package = package?.withoutQuestions({pQuestionId});
    await savePreference(flaggedPreference, [...flaggedIds, pQuestionId]);
  }

  String get appearance {
    final vAppearance = preferences[appearancePreference];

    final rAppearance = appearances.contains(vAppearance) ? vAppearance as String : 'system';

    return rAppearance;
  }

  double get textScale {
    final vScale = (preferences[textScalePreference] as num?)?.toDouble();

    final rScale = textScales.contains(vScale) ? vScale! : 1.0;

    return rScale;
  }

  /// Enregistre l'apparence et la taille du texte ; l'application se redessine.
  Future<void> setDisplay({String? pAppearance, double? pTextScale}) async {
    preferences = {
      ...preferences,
      if (pAppearance != null) appearancePreference: pAppearance,
      if (pTextScale != null) textScalePreference: pTextScale,
    };
    await store.savePreferences(preferences);
    notifyListeners();
  }

  Map<String, dynamic> get statistics =>
      Map<String, dynamic>.from(progress['statistics'] as Map? ?? const {});

  /// Date de la dernière progression reçue du serveur.
  DateTime? get lastSync {
    final vGeneratedAt = progress['generated_at'] as String?;

    final rDate = vGeneratedAt == null ? null : DateTime.parse(vGeneratedAt);

    return rDate;
  }

  /// Relit le stockage local au démarrage.
  Future<void> load() async {
    settings = await store.loadSettings();
    progress = await store.loadProgress() ?? {};
    pending = await store.loadPending();
    preferences = await store.loadPreferences();
    examResults = [
      for (final vItem in await store.loadExamResults()) ExamResult.fromJson(vItem),
    ];
    offers = await store.loadOffers();

    final vContent = await store.loadPackage();

    if (vContent != null) {
      try {
        package = QuizPackage.fromJson(jsonDecode(vContent) as Map<String, dynamic>);
      } on FormatException catch (vException) {
        // Un contenu illisible est retéléchargé à la prochaine synchronisation.
        log('Contenu local illisible : ${vException.message}', name: 'store');
      }
    }

    package = package?.withoutQuestions(flaggedIds);

    rebuildSchedule();
    notifyListeners();
    unawaited(refreshReminder());
  }

  /// Calendrier du serveur, complété par les réponses pas encore envoyées.
  void rebuildSchedule() {
    final vIntervals = package?.leitnerIntervals ?? const [1, 3, 7, 21, 60];
    final vSchedule = <String, ReviewState>{
      for (final vEntry in (progress['questions'] as Map? ?? const {}).entries)
        vEntry.key as String: ReviewState.fromJson(Map<String, dynamic>.from(vEntry.value as Map)),
    };

    final vAnswers = [...pending]..sort((pFirst, pSecond) =>
        (pFirst['answered_at'] as String).compareTo(pSecond['answered_at'] as String));

    for (final vAnswer in vAnswers) {
      final vQuestionId = vAnswer['question_id'] as String;

      vSchedule[vQuestionId] = applyAnswer(
        vSchedule[vQuestionId],
        vAnswer['correct'] as bool,
        DateTime.parse(vAnswer['answered_at'] as String),
        vIntervals,
      );
    }

    schedule = vSchedule;
  }

  /// Enregistre de nouveaux réglages après une première synchronisation réussie.
  Future<SyncReport> configure(ServerSettings pSettings) async {
    final vPrevious = settings;

    settings = pSettings;

    try {
      final rReport = await synchronize();

      await store.saveSettings(pSettings);

      return rReport;
    } catch (_) {
      // Des réglages refusés ne remplacent pas ceux qui fonctionnaient.
      settings = vPrevious;
      rethrow;
    }
  }

  /// Envoie les réponses en attente, puis récupère progression et contenu.
  Future<SyncReport> synchronize() async {
    final vSettings = settings;

    if (vSettings == null) {
      throw const ApiException("Renseignez d'abord l'adresse du serveur et le jeton.");
    }

    if (!await store.acquireSyncLock()) {
      throw const ApiException('Synchronisation déjà en cours : réessayez dans un instant.');
    }

    final vClient = clientFactory(vSettings);
    var vSent = 0;
    var vRejected = 0;

    syncing = true;
    notifyListeners();

    try {
      while (pending.isNotEmpty) {
        final vBatch = pending.take(maxAnswersPerUpload).toList();
        final vReport = await vClient.uploadAnswers([
          for (final vAnswer in vBatch)
            {
              for (final vEntry in vAnswer.entries)
                // La correction locale n'est pas envoyée : le serveur recorrige.
                if (vEntry.key != 'correct') vEntry.key: vEntry.value,
            },
        ]);

        vSent += vBatch.length;
        vRejected += (vReport['rejected'] as List? ?? const []).length;

        // Une réponse refusée ne serait jamais acceptée : elle n'est pas renvoyée.
        pending = pending.skip(vBatch.length).toList();
        await store.savePending(pending);
      }

      await sendFlagsAndExams(vClient);
      await exchangeInterviewAndSkills(vClient);

      final vProgress = await vClient.downloadProgress();
      final vContent = await vClient.downloadQuiz(package?.version);

      if (vContent != null) {
        package = QuizPackage.fromJson(jsonDecode(vContent) as Map<String, dynamic>)
            .withoutQuestions(flaggedIds);
        await store.savePackage(vContent);
      }

      progress = vProgress;
      await store.saveProgress(vProgress);
      rebuildSchedule();
      unawaited(refreshReminder());
      unawaited(refreshHomeWidget());

      final rReport = SyncReport(
        sent: vSent,
        rejected: vRejected,
        contentUpdated: vContent != null,
      );

      log('Synchronisation : ${rReport.describe()}', name: 'sync');

      return rReport;
    } finally {
      syncing = false;
      await store.releaseSyncLock();
      notifyListeners();
    }
  }

  /// Envoie signalements, examens blancs et statuts d'offres, puis reçoit les offres.
  ///
  /// Un serveur plus ancien qui ne les connaît pas n'empêche pas la
  /// synchronisation ; seule une coupure du réseau l'interrompt.
  Future<void> sendFlagsAndExams(ApiClient pClient) async {
    try {
      if (flaggedIds.isNotEmpty) {
        await pClient.uploadFlags(flaggedIds.toList());
        await savePreference(flaggedPreference, <String>[]);
      }

      if (examResults.isNotEmpty) {
        await pClient.uploadExams([for (final vResult in examResults) vResult.toJson()]);
      }

      if (pendingStatuses.isNotEmpty) {
        await pClient.uploadStatusChanges(pendingStatuses);
        await savePreference(pendingStatusPreference, <Map<String, dynamic>>[]);
      }

      if (pendingNotes.isNotEmpty) {
        await pClient.uploadNotes(pendingNotes);
        await savePreference(pendingNotesPreference, <Map<String, dynamic>>[]);
      }

      final vPrevious = offers;

      offers = await pClient.downloadOffers();
      await store.saveOffers(offers);
      await notifyNewOffers(findNewGoodOffers(vPrevious, offers));
      await exchangeReplies(pClient);
      await exchangeWithdrawn(pClient);
      await scheduleInterviewAlerts(pClient);
      await exchangeTracking(pClient);
      await exchangeGame(pClient);
    } on ApiException catch (vException) {
      if (vException.unreachable) {
        rethrow;
      }

      log('Signalements, examens ou offres non échangés : ${vException.message}', name: 'sync');
    } on FormatException catch (vException) {
      log('Réponse illisible pour les offres : ${vException.message}', name: 'sync');
    }
  }

  /// Cherche le serveur sur le Wi-Fi et garde sa nouvelle adresse ; retourne si
  /// elle a changé.
  Future<bool> relocateServer() async {
    final vSettings = settings;
    var rMoved = false;

    if (vSettings != null) {
      final vAddress = await discovery.discover(
        pKnownHost: getHost(vSettings.address),
        pScheme: Uri.tryParse(vSettings.address)?.scheme ?? 'http',
      );

      if (vAddress != null && vAddress != vSettings.address) {
        settings = vSettings.withAddress(vAddress);
        await store.saveSettings(settings!);
        rMoved = true;

        log('Serveur retrouvé à une nouvelle adresse', name: 'sync');
      }
    }

    return rMoved;
  }

  /// Synchronise ; si le serveur ne répond plus, le cherche sur le Wi-Fi et
  /// réessaie à sa nouvelle adresse.
  Future<SyncReport> synchronizeOrRelocate() async {
    SyncReport rReport;

    try {
      rReport = await synchronize();
    } on ApiException catch (vException) {
      if (!vException.unreachable || !await relocateServer()) {
        rethrow;
      }

      rReport = await synchronize();
    }

    return rReport;
  }

  /// Synchronise sans déranger : sans réseau, les réponses attendent le suivant.
  Future<SyncReport?> synchronizeQuietly() async {
    SyncReport? rReport;

    if (settings != null && !syncing) {
      try {
        rReport = await synchronizeOrRelocate();
      } on ApiException catch (vException) {
        log('Synchronisation automatique reportée : ${vException.message}', name: 'sync');
      } on FormatException catch (vException) {
        log('Contenu reçu illisible : ${vException.message}', name: 'sync');
      }
    }

    return rReport;
  }

  /// Questions à revoir aujourd'hui, tous thèmes confondus.
  int countDueToday() {
    final rCount = package == null ? 0 : countDue(package!.questions, schedule, DateTime.now());

    return rCount;
  }

  /// Active ou coupe le rappel quotidien ; retourne s'il est actif.
  Future<bool> setReminder(bool pEnabled) async {
    var vEnabled = pEnabled;

    if (vEnabled && reminders != null) {
      vEnabled = await reminders!.requestPermission();
    }

    preferences = {...preferences, reminderPreference: vEnabled};
    await store.savePreferences(preferences);
    await refreshReminder();
    notifyListeners();

    final rEnabled = vEnabled;

    return rEnabled;
  }

  /// Active ou coupe l'alerte des nouvelles offres ; retourne si elle est active.
  Future<bool> setOfferAlerts(bool pEnabled) async {
    var vEnabled = pEnabled;

    if (vEnabled && reminders != null) {
      vEnabled = await reminders!.requestPermission();
    }

    preferences = {...preferences, offerAlertPreference: vEnabled};
    await store.savePreferences(preferences);

    try {
      await reminders?.scheduleOfferChecks(vEnabled);
    } on Exception catch (vException) {
      log('Vérification des offres non planifiée : $vException', name: 'offres');
    }

    notifyListeners();

    final rEnabled = vEnabled;

    return rEnabled;
  }

  /// Replanifie les rappels d'entretien d'après les entretiens connus du PC.
  ///
  /// Un serveur plus ancien qui ne les connaît pas n'empêche pas la synchronisation.
  Future<void> scheduleInterviewAlerts(ApiClient pClient) async {
    if (reminders == null) {
      return;
    }

    try {
      await reminders!.scheduleInterviews(
        buildInterviewAlerts(await pClient.downloadInterviews(), DateTime.now()),
      );
    } on ApiException catch (vException) {
      if (vException.unreachable) {
        rethrow;
      }

      log('Entretiens non reçus : ${vException.message}', name: 'sync');
    }
  }

  /// Reçoit les réponses de recruteurs repérées par le PC et signale les nouvelles.
  ///
  /// Un serveur plus ancien qui ne les connaît pas n'empêche pas la synchronisation.
  Future<void> exchangeReplies(ApiClient pClient) => notifyOnce(
        'Réponses de recruteurs',
        pClient.downloadReplies,
        notifiedRepliesPreference,
        (pReply) => '${pReply['id']}',
        (pReplies) => reminders!.showReplies(pReplies),
      );

  /// Reçoit les offres suivies retirées par leur site et signale les nouvelles.
  /// Met à jour le widget de l'écran d'accueil avec la révision et l'entretien.
  Future<void> refreshHomeWidget() async {
    final vPackage = package;

    if (homeWidget == null || vPackage == null) {
      return;
    }

    await homeWidget!.show(
      buildWidgetLines(
        countDue(vPackage.questions, schedule, DateTime.now()),
        trackedApplications,
        DateTime.now(),
      ),
    );
  }

  /// Candidatures en cours, reçues du PC à la dernière synchronisation.
  List<Map<String, dynamic>> get trackedApplications => [
        for (final vItem
            in (preferences[trackingPreference] as Map?)?['applications'] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  /// Fiche de préparation d'une candidature, ou null si aucun entretien proche.
  Map<String, dynamic>? sheetOf(Map<String, dynamic> pApplication) {
    final vSheets = (preferences[trackingPreference] as Map?)?['sheets'] as Map?;
    final vSheet = vSheets?['${pApplication['source']}/${pApplication['source_id']}'];

    final rSheet = vSheet == null ? null : Map<String, dynamic>.from(vSheet as Map);

    return rSheet;
  }

  /// Prochain entretien dans les 24 heures qui a sa fiche, ou null.
  Map<String, dynamic>? nextInterview(DateTime pNow) {
    Map<String, dynamic>? rNext;

    for (final vApplication in trackedApplications) {
      final vAt = DateTime.tryParse('${vApplication['interview_at'] ?? ''}');

      if (vAt != null &&
          vAt.isAfter(pNow) &&
          vAt.isBefore(pNow.add(interviewSheetLead)) &&
          sheetOf(vApplication) != null &&
          (rNext == null || vAt.isBefore(DateTime.parse('${rNext['interview_at']}')))) {
        rNext = vApplication;
      }
    }

    return rNext;
  }

  /// Progression reçue du PC, ou null avant la première synchronisation.
  Map<String, dynamic>? get game {
    final vGame = preferences[gamePreference];

    final rGame = vGame is Map ? Map<String, dynamic>.from(vGame) : null;

    return rGame;
  }

  /// Niveau atteint depuis la dernière fête, ou null : la première progression
  /// reçue sert de référence, sans fête pour l'historique.
  int? get levelToCelebrate {
    final vLevel = (game?['level'] as num?)?.toInt();
    final vCelebrated = (preferences[celebratedLevelPreference] as num?)?.toInt();

    final rLevel = vLevel != null && vCelebrated != null && vLevel > vCelebrated ? vLevel : null;

    return rLevel;
  }

  /// Note le niveau actuel comme fêté.
  Future<void> markLevelCelebrated() async {
    final vLevel = (game?['level'] as num?)?.toInt();

    if (vLevel != null) {
      await savePreference(celebratedLevelPreference, vLevel);
    }
  }

  /// Garde la progression du PC ; la première reçue devient la référence des fêtes.
  Future<void> exchangeGame(ApiClient pClient) async {
    try {
      final vGame = await pClient.downloadGame();

      await savePreference(gamePreference, vGame);

      if (preferences[celebratedLevelPreference] == null && vGame['level'] is num) {
        await savePreference(celebratedLevelPreference, vGame['level'] as num);
      }
    } on ApiException catch (vException) {
      if (vException.unreachable) {
        rethrow;
      }

      log('Progression non reçue : ${vException.message}', name: 'sync');
    }
  }

  /// Meilleur score du jeu « Contre la montre », 0 avant la première partie.
  int get timeAttackBest => (preferences[timeAttackBestPreference] as num?)?.toInt() ?? 0;

  /// Garde le score s'il bat le record ; retourne si c'est un nouveau record.
  Future<bool> recordTimeAttack(int pScore) async {
    final rRecord = pScore > timeAttackBest;

    if (rRecord) {
      await savePreference(timeAttackBestPreference, pScore);
    }

    return rRecord;
  }

  /// Garde les candidatures et les fiches pour une consultation hors ligne ; un
  /// serveur plus ancien qui ne les connaît pas n'empêche pas la synchronisation.
  Future<void> exchangeTracking(ApiClient pClient) async {
    try {
      await savePreference(trackingPreference, await pClient.downloadTracking());
    } on ApiException catch (vException) {
      if (vException.unreachable) {
        rethrow;
      }

      log('Candidatures non reçues : ${vException.message}', name: 'sync');
    }
  }

  Future<void> exchangeWithdrawn(ApiClient pClient) => notifyOnce(
        'Offres retirées',
        pClient.downloadWithdrawn,
        notifiedWithdrawnPreference,
        (pOffer) => '${pOffer['source']}/${pOffer['source_id']}',
        (pOffers) => reminders!.showWithdrawn(pOffers),
      );

  /// Télécharge une liste du PC et notifie ses éléments jamais signalés.
  ///
  /// Seuls les identifiants encore présents sont gardés ; un serveur plus ancien
  /// qui ne connaît pas la liste n'empêche pas la synchronisation.
  Future<void> notifyOnce(
    String pLabel,
    Future<List<Map<String, dynamic>>> Function() pDownload,
    String pPreference,
    String Function(Map<String, dynamic>) pIdOf,
    Future<void> Function(List<Map<String, dynamic>>) pShow,
  ) async {
    try {
      final vItems = await pDownload();
      final vNotified = {
        for (final vId in preferences[pPreference] as List? ?? const []) '$vId',
      };
      final vNew = [
        for (final vItem in vItems)
          if (!vNotified.contains(pIdOf(vItem))) vItem,
      ];

      if (vNew.isNotEmpty && offerAlertsEnabled && reminders != null) {
        await pShow(vNew);
      }

      await savePreference(pPreference, [for (final vItem in vItems) pIdOf(vItem)]);
    } on ApiException catch (vException) {
      if (vException.unreachable) {
        rethrow;
      }

      log('$pLabel non reçues : ${vException.message}', name: 'sync');
    }
  }

  /// Signale les nouvelles offres bien notées, si l'alerte est active.
  Future<void> notifyNewOffers(List<Map<String, dynamic>> pOffers) async {
    if (!offerAlertsEnabled || pOffers.isEmpty || reminders == null) {
      return;
    }

    try {
      await reminders!.showNewOffers(pOffers);
    } on Exception catch (vException) {
      log('Nouvelles offres non signalées : $vException', name: 'offres');
    }
  }

  /// Replanifie le rappel avec le nombre de questions à revoir, ou l'annule.
  Future<void> refreshReminder() async {
    final vReminders = reminders;

    if (vReminders == null) {
      return;
    }

    try {
      if (reminderEnabled) {
        await vReminders.schedule(countDueToday());
      } else {
        await vReminders.cancel();
      }
    } on Exception catch (vException) {
      // Un rappel impossible à planifier ne bloque pas la révision.
      log('Rappel non planifié : $vException', name: 'rappel');
    }
  }

  /// Garde le résultat d'un examen blanc terminé.
  Future<void> recordExam(ExamResult pResult) async {
    examResults = [pResult, ...examResults].take(maxExamResults).toList();

    await store.saveExamResults([for (final vResult in examResults) vResult.toJson()]);
    notifyListeners();
  }

  /// Corrige une réponse, la garde pour l'envoi et met à jour le calendrier.
  ///
  /// Lève UnreadableAnswer si la réponse est illisible : elle n'est pas comptée.
  Future<Grade> answer(QuizQuestion pQuestion, Object? pResponse) async {
    final rGrade = gradeAnswer(pQuestion, pResponse);
    final vNow = DateTime.now();

    pending = [
      ...pending,
      {
        'id': const Uuid().v4(),
        'question_id': pQuestion.id,
        if (pQuestion.type == 'qcm') 'choice': pResponse else 'response': pResponse,
        'answered_at': vNow.toIso8601String().split('.').first,
        'correct': rGrade.correct,
      },
    ];

    await store.savePending(pending);

    final vToday = vNow.toIso8601String().split('T').first;
    preferences = {
      ...preferences,
      goalDayPreference: vToday,
      goalCountPreference: answersToday + 1,
    };
    await store.savePreferences(preferences);

    schedule = {
      ...schedule,
      pQuestion.id: applyAnswer(
        schedule[pQuestion.id],
        rGrade.correct,
        vNow,
        package?.leitnerIntervals ?? const [1, 3, 7, 21, 60],
      ),
    };

    notifyListeners();

    // Envoi régulier en arrière-plan : un téléphone perdu ne perd que peu de réponses.
    if (pending.length % autoSyncEvery == 0) {
      unawaited(synchronizeQuietly());
    }

    return rGrade;
  }
}
