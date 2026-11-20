// Accueil : progression, synchronisation et thèmes rangés par domaine, avec
// pour chacun les questions à revoir aujourd'hui.

import 'package:flutter/material.dart';

import '../logic/review.dart';
import '../models/quiz_package.dart';
import '../revision_state.dart';
import '../services/api_client.dart';
import '../theme.dart';
import '../widgets/celebration.dart';
import '../widgets/brand.dart';
import '../widgets/game_card.dart';
import 'exam_screen.dart';
import 'hub_tabs.dart';
import 'offers_screen.dart';
import 'question_screen.dart';
import 'tracking_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.state});

  final RevisionState state;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with WidgetsBindingObserver {
  RevisionState get state => widget.state;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    state.addListener(celebrateLevel);

    // Synchronisation à l'ouverture, sans attendre un geste de l'utilisateur.
    WidgetsBinding.instance.addPostFrameCallback((_) => state.synchronizeQuietly());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    state.removeListener(celebrateLevel);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState pState) {
    // Au retour dans l'application, le réseau est peut-être revenu.
    if (pState == AppLifecycleState.resumed) {
      state.synchronizeQuietly();
    }
  }

  /// Fête un niveau gagné, reçu du PC à la synchronisation ; une seule fois.
  Future<void> celebrateLevel() async {
    final vLevel = state.levelToCelebrate;

    if (vLevel == null || !mounted) {
      return;
    }

    await state.markLevelCelebrated();

    if (mounted) {
      await showCelebration(
        context,
        title: 'Niveau $vLevel',
        subtitle: '${state.game?['title'] ?? ''}',
        detail: 'Prochain titre : ${state.game?['next_title'] ?? ''}',
      );
    }
  }

  Future<void> synchronize() async {
    final vMessenger = ScaffoldMessenger.of(context);

    try {
      final vReport = await state.synchronizeOrRelocate();

      vMessenger.showSnackBar(SnackBar(content: Text(vReport.describe())));
    } on ApiException catch (vException) {
      vMessenger.showSnackBar(SnackBar(content: Text(vException.message)));
    } on FormatException catch (vException) {
      vMessenger.showSnackBar(SnackBar(content: Text(vException.message)));
    }
  }

  void openExam() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => ExamScreen(
          state: state,
          title: 'Examen blanc',
          questions: state.package!.questions,
        ),
      ),
    );
  }

  /// Onglet ouvert, et onglets déjà ouverts : un onglet n'est construit qu'à sa
  /// première visite, puis gardé tel quel (défilement, filtres).
  int tab = 0;
  final visited = <int>{0};

  void openTab(int pIndex) => setState(() {
        tab = pIndex;
        visited.add(pIndex);
      });

  Widget buildTab(int pIndex) {
    final rTab = switch (pIndex) {
      0 => buildRevision(),
      1 => OffersScreen(state: state),
      2 => TrackingScreen(state: state),
      3 => InterviewHub(state: state),
      _ => MoreTab(state: state, onExam: state.package == null ? null : openExam),
    };

    return rTab;
  }

  @override
  Widget build(BuildContext context) {
    final rScreen = Scaffold(
      body: IndexedStack(
        index: tab,
        children: [
          for (var vIndex = 0; vIndex < 5; vIndex++)
            visited.contains(vIndex) ? buildTab(vIndex) : const SizedBox.shrink(),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: tab,
        onDestinationSelected: openTab,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.school_outlined),
            selectedIcon: Icon(Icons.school),
            label: 'Réviser',
          ),
          NavigationDestination(
            icon: Icon(Icons.work_outline),
            selectedIcon: Icon(Icons.work),
            label: 'Offres',
          ),
          NavigationDestination(
            icon: Icon(Icons.assignment_outlined),
            selectedIcon: Icon(Icons.assignment),
            label: 'Candidatures',
          ),
          NavigationDestination(
            icon: Icon(Icons.record_voice_over_outlined),
            selectedIcon: Icon(Icons.record_voice_over),
            label: 'Entretien',
          ),
          NavigationDestination(
            icon: Icon(Icons.more_horiz),
            label: 'Plus',
          ),
        ],
      ),
    );

    return rScreen;
  }

  /// Onglet Réviser : la journée en grand, puis les candidatures et les thèmes.
  Widget buildRevision() {
    final rTab = ListenableBuilder(
      listenable: state,
      builder: (pContext, _) => Scaffold(
        appBar: AppBar(
          title: const Text('Réviser'),
          actions: [
            IconButton(
              tooltip: 'Synchroniser',
              onPressed: state.syncing ? null : synchronize,
              icon: const Icon(Icons.sync),
            ),
          ],
        ),
        body: RefreshIndicator(
          onRefresh: synchronize,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            children: [
              if (state.syncing) const LinearProgressIndicator(),
              TodayCard(state: state),
              const SizedBox(height: 12),
              SummaryCard(state: state),
              if (state.nextInterview(DateTime.now()) case final vInterview?)
                Card(
                  color: Theme.of(pContext).colorScheme.tertiaryContainer,
                  child: ListTile(
                    leading: const Icon(Icons.event_available),
                    title: Text(
                      'Entretien le ${formatMoment(vInterview['interview_at'] as String?)}',
                    ),
                    subtitle: Text('${vInterview['company'] ?? vInterview['title'] ?? ''}'
                        ' · ouvrir la fiche de préparation'),
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => SheetScreen(sheet: state.sheetOf(vInterview)!),
                      ),
                    ),
                  ),
                ),
              GameCard(state: state),
              if (state.package != null && state.applications.isNotEmpty)
                ApplicationsCard(state: state),
              if (state.package == null)
                const Padding(
                  padding: EdgeInsets.all(24),
                  child: Text(
                    'Aucune question pour le moment : tirez vers le bas pour '
                    'synchroniser.',
                    textAlign: TextAlign.center,
                  ),
                )
              else
                for (final vDomain in groupByDomain(state.package!).entries)
                  DomainCard(
                    state: state,
                    domain: vDomain.key,
                    themes: vDomain.value,
                  ),
            ],
          ),
        ),
      ),
    );

    return rTab;
  }
}

/// Regroupe les thèmes qui ont des questions par domaine, dans l'ordre reçu.
Map<String, List<QuizTheme>> groupByDomain(QuizPackage pPackage) {
  final rDomains = <String, List<QuizTheme>>{};

  for (final vTheme in pPackage.themes) {
    if (pPackage.questionsOf(vTheme.key).isNotEmpty) {
      rDomains.putIfAbsent(vTheme.domain, () => []).add(vTheme);
    }
  }

  return rDomains;
}

class SummaryCard extends StatelessWidget {
  const SummaryCard({super.key, required this.state});

  final RevisionState state;

  @override
  Widget build(BuildContext context) {
    final vStatistics = state.statistics;
    final vLastSync = state.lastSync;
    final rCard = Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Wrap(
          spacing: 24,
          runSpacing: 12,
          children: [
            Statistic(
              value: '${vStatistics['acquired'] ?? 0} / ${vStatistics['total'] ?? 0}',
              label: 'acquises',
            ),
            Statistic(value: '${vStatistics['streak'] ?? 0} j', label: 'de suite'),
            Statistic(value: '${state.pending.length}', label: 'réponse(s) à envoyer'),
            if (state.examResults.isNotEmpty)
              Statistic(
                value: '${state.examResults.first.score} %',
                label: 'dernier examen blanc',
              ),
            if (vLastSync != null)
              Text(
                'Synchronisé le ${vLastSync.day.toString().padLeft(2, '0')}/'
                '${vLastSync.month.toString().padLeft(2, '0')} à '
                '${vLastSync.hour.toString().padLeft(2, '0')}:'
                '${vLastSync.minute.toString().padLeft(2, '0')}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
          ],
        ),
      ),
    );

    return rCard;
  }
}

class Statistic extends StatelessWidget {
  const Statistic({super.key, required this.value, required this.label});

  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    final rStatistic = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(value, style: Theme.of(context).textTheme.titleLarge),
        Text(label, style: Theme.of(context).textTheme.bodySmall),
      ],
    );

    return rStatistic;
  }
}

class DomainCard extends StatelessWidget {
  const DomainCard({
    super.key,
    required this.state,
    required this.domain,
    required this.themes,
  });

  final RevisionState state;
  final String domain;
  final List<QuizTheme> themes;

  @override
  Widget build(BuildContext context) {
    final vPackage = state.package!;
    final vToday = DateTime.now();

    final rCard = Card(
      clipBehavior: Clip.antiAlias,
      child: ExpansionTile(
        // L'état ouvert ou replié de chaque domaine est gardé pendant la session.
        key: PageStorageKey<String>(domain),
        initiallyExpanded: true,
        leading: Icon(getDomainIcon(vPackage.icons[domain]), color: primaryColor),
        title: Text(domain, style: Theme.of(context).textTheme.titleMedium),
        children: [
          for (final vTheme in themes)
            Builder(
              builder: (pContext) {
                final vQuestions = vPackage.questionsOf(vTheme.key);
                final vDue = countDue(vQuestions, state.schedule, vToday);
                final vNew = countNew(vQuestions, state.schedule);

                return ListTile(
                  title: Text(vTheme.label),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '$vDue à revoir · $vNew nouvelle(s) · ${vQuestions.length} question(s)',
                      ),
                      const SizedBox(height: 6),
                      AnimatedBar(
                        value:
                            vQuestions.isEmpty ? 0 : (vQuestions.length - vNew) / vQuestions.length,
                        color: sunriseColor,
                      ),
                    ],
                  ),
                  trailing: vDue > 0
                      ? Badge(label: Text('$vDue'), child: const Icon(Icons.chevron_right))
                      : const Icon(Icons.chevron_right),
                  onTap: () => Navigator.of(pContext).push(
                    MaterialPageRoute<void>(
                      builder: (_) => QuestionScreen(state: state, theme: vTheme),
                    ),
                  ),
                );
              },
            ),
        ],
      ),
    );

    return rCard;
  }
}

/// La journée en grand : questions à revoir, objectif du jour en anneau, et de
/// quoi commencer d'un toucher.
class TodayCard extends StatelessWidget {
  const TodayCard({super.key, required this.state});

  final RevisionState state;

  @override
  Widget build(BuildContext context) {
    final vDone = state.answersToday;
    final vGoal = state.dailyGoal;
    final vPackage = state.package;
    final vDue =
        vPackage == null ? 0 : countDue(vPackage.questions, state.schedule, DateTime.now());
    final vTitle = Theme.of(context).textTheme.headlineSmall!.copyWith(
          color: Colors.white,
          fontWeight: FontWeight.w700,
        );

    final rCard = ElanCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text("Aujourd'hui"),
                    const SizedBox(height: 4),
                    TweenAnimationBuilder<int>(
                      tween: IntTween(begin: 0, end: vDue),
                      duration: motionOf(context, const Duration(milliseconds: 800)),
                      builder: (_, pValue, __) => Text(
                        vDue == 0 ? 'Tout est à jour' : '$pValue à revoir',
                        style: vTitle,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      vDone >= vGoal
                          ? 'Objectif du jour atteint : bravo.'
                          : 'Objectif : $vGoal réponses aujourd\'hui',
                      style: const TextStyle(color: Colors.white70),
                    ),
                  ],
                ),
              ),
              GoalRing(done: vDone, goal: vGoal),
            ],
          ),
          if (vPackage != null) ...[
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: FilledButton.icon(
                    style: FilledButton.styleFrom(
                      backgroundColor: sunriseColor,
                      foregroundColor: nightColor,
                    ),
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(builder: (_) => QuestionScreen(state: state)),
                    ),
                    icon: const Icon(Icons.play_arrow_rounded),
                    label: const Text('Réviser'),
                  ),
                ),
                const SizedBox(width: 8),
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.white,
                    side: const BorderSide(color: Colors.white54),
                    minimumSize: const Size(48, 52),
                  ),
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => QuestionScreen(state: state, timeLimit: sprintDuration),
                    ),
                  ),
                  icon: const Icon(Icons.bolt),
                  label: const Text('5 min'),
                ),
              ],
            ),
          ],
        ],
      ),
    );

    return rCard;
  }
}

/// Candidatures en cours, avec les thèmes à revoir pour chacune.
class ApplicationsCard extends StatelessWidget {
  const ApplicationsCard({super.key, required this.state});

  final RevisionState state;

  @override
  Widget build(BuildContext context) {
    final vPackage = state.package!;
    final vThemes = {for (final vTheme in vPackage.themes) vTheme.key: vTheme};

    final rCard = Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Pour mes candidatures', style: Theme.of(context).textTheme.titleMedium),
            for (final vApplication in state.applications) ...[
              const SizedBox(height: 12),
              Text(
                '${vApplication['status'] ?? ''} · ${vApplication['company'] ?? ''}',
                style: Theme.of(context).textTheme.labelLarge,
              ),
              Text('${vApplication['title'] ?? ''}'),
              const SizedBox(height: 6),
              Wrap(
                spacing: 8,
                runSpacing: 4,
                children: [
                  for (final vKey in vApplication['themes'] as List? ?? const [])
                    if (vThemes[vKey] != null && vPackage.questionsOf(vKey as String).isNotEmpty)
                      ActionChip(
                        label: Text(vThemes[vKey]!.label),
                        onPressed: () => Navigator.of(context).push(
                          MaterialPageRoute<void>(
                            builder: (_) => QuestionScreen(state: state, theme: vThemes[vKey]!),
                          ),
                        ),
                      ),
                ],
              ),
            ],
          ],
        ),
      ),
    );

    return rCard;
  }
}
