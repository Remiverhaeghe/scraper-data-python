// Accueil : progression, synchronisation et thèmes rangés par domaine, avec
// pour chacun les questions à revoir aujourd'hui.

import 'package:flutter/material.dart';

import '../logic/review.dart';
import '../models/quiz_package.dart';
import '../revision_state.dart';
import '../services/api_client.dart';
import '../theme.dart';
import 'exam_screen.dart';
import 'interview_screen.dart';
import 'offers_screen.dart';
import 'question_screen.dart';
import 'setup_screen.dart';
import 'skills_screen.dart';
import 'statistics_screen.dart';

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

    // Synchronisation à l'ouverture, sans attendre un geste de l'utilisateur.
    WidgetsBinding.instance.addPostFrameCallback((_) => state.synchronizeQuietly());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState pState) {
    // Au retour dans l'application, le réseau est peut-être revenu.
    if (pState == AppLifecycleState.resumed) {
      state.synchronizeQuietly();
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

  @override
  Widget build(BuildContext context) {
    final rScreen = ListenableBuilder(
      listenable: state,
      builder: (pContext, _) => Scaffold(
        appBar: AppBar(
          title: const Text('Révision'),
          actions: [
            IconButton(
              tooltip: 'Nouvelles offres',
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute<void>(builder: (_) => OffersScreen(state: state)),
              ),
              icon: const Icon(Icons.work_outline),
            ),
            IconButton(
              tooltip: 'Statistiques',
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute<void>(builder: (_) => StatisticsScreen(state: state)),
              ),
              icon: const Icon(Icons.insights),
            ),
            IconButton(
              tooltip: 'Examen blanc, tous thèmes',
              onPressed: state.package == null ? null : openExam,
              icon: const Icon(Icons.timer_outlined),
            ),
            IconButton(
              tooltip: 'Synchroniser',
              onPressed: state.syncing ? null : synchronize,
              icon: const Icon(Icons.sync),
            ),
            PopupMenuButton<Widget Function()>(
              tooltip: 'Entretien',
              icon: const Icon(Icons.record_voice_over_outlined),
              onSelected: (pBuild) => Navigator.of(context).push(
                MaterialPageRoute<void>(builder: (_) => pBuild()),
              ),
              itemBuilder: (_) => [
                PopupMenuItem(
                  value: () => InterviewScreen(state: state),
                  child: const Text("Simulation d'entretien"),
                ),
                PopupMenuItem(
                  value: () => SkillsScreen(state: state),
                  child: const Text('Auto-évaluation'),
                ),
              ],
            ),
            IconButton(
              tooltip: 'Paramètres',
              onPressed: () => Navigator.of(pContext).push(
                MaterialPageRoute<void>(builder: (_) => SetupScreen(state: state)),
              ),
              icon: const Icon(Icons.settings_outlined),
            ),
          ],
        ),
        body: RefreshIndicator(
          onRefresh: synchronize,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (state.syncing) const LinearProgressIndicator(),
              SummaryCard(state: state),
              DailyGoalCard(state: state),
              if (state.package != null)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: FilledButton.tonalIcon(
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => QuestionScreen(state: state, timeLimit: sprintDuration),
                      ),
                    ),
                    icon: const Icon(Icons.bolt),
                    label: const Text('Révision express · 5 minutes'),
                  ),
                ),
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

    return rScreen;
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
    final vToday = DateTime.now();
    final vDue =
        state.package == null ? 0 : countDue(state.package!.questions, state.schedule, vToday);

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
            Statistic(value: '$vDue', label: "à revoir aujourd'hui"),
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
                  subtitle: Text(
                    '$vDue à revoir · $vNew nouvelle(s) · ${vQuestions.length} question(s)',
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

/// Objectif du jour : réponses données aujourd'hui sur l'objectif choisi.
class DailyGoalCard extends StatelessWidget {
  const DailyGoalCard({super.key, required this.state});

  final RevisionState state;

  @override
  Widget build(BuildContext context) {
    final vDone = state.answersToday;
    final vGoal = state.dailyGoal;
    final vReached = vDone >= vGoal;

    final rCard = Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              vReached
                  ? 'Objectif du jour atteint : $vDone réponses'
                  : 'Objectif du jour : $vDone / $vGoal réponses',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: 8),
            LinearProgressIndicator(
              value: vGoal == 0 ? 0 : (vDone / vGoal).clamp(0, 1).toDouble(),
              minHeight: 8,
              borderRadius: BorderRadius.circular(4),
              color: vReached ? successColorOf(context) : null,
            ),
          ],
        ),
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
