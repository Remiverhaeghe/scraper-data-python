// Point d'entrée : charge le stockage local, puis ouvre la configuration au
// premier lancement ou directement les thèmes de révision.

import 'package:flutter/material.dart';
import 'package:workmanager/workmanager.dart';

import 'revision_state.dart';
import 'screens/home_screen.dart';
import 'screens/setup_screen.dart';
import 'services/file_store.dart';
import 'services/home_widget_service.dart';
import 'services/offer_checks.dart';
import 'services/reminders.dart';
import 'theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Point d'entrée de la vérification des offres, lancée par Android même
  // application fermée.
  await Workmanager().initialize(checkOffersInBackground);

  runApp(
    RevisionApp(
      state: RevisionState(
        FileRevisionStore(),
        reminders: LocalReminders(),
        homeWidget: AndroidHomeWidget(),
      ),
    ),
  );
}

class RevisionApp extends StatelessWidget {
  const RevisionApp({super.key, required this.state});

  final RevisionState state;

  static const themeModes = {
    'system': ThemeMode.system,
    'light': ThemeMode.light,
    'dark': ThemeMode.dark,
  };

  @override
  Widget build(BuildContext context) {
    final rApp = ListenableBuilder(
      listenable: state,
      builder: (_, __) => MaterialApp(
        title: 'JobBoard Révision',
        debugShowCheckedModeBanner: false,
        theme: buildTheme(Brightness.light),
        darkTheme: buildTheme(Brightness.dark),
        themeMode: themeModes[state.appearance],
        // Le choix de l'application s'ajoute à la taille réglée sur le téléphone.
        builder: (pContext, pChild) => MediaQuery(
          data: MediaQuery.of(pContext).copyWith(
            textScaler: TextScaler.linear(
              MediaQuery.textScalerOf(pContext).scale(1) * state.textScale,
            ),
          ),
          child: pChild!,
        ),
        home: StartScreen(state: state),
      ),
    );

    return rApp;
  }
}

class StartScreen extends StatefulWidget {
  const StartScreen({super.key, required this.state});

  final RevisionState state;

  @override
  State<StartScreen> createState() => _StartScreenState();
}

class _StartScreenState extends State<StartScreen> {
  late final Future<void> loading = widget.state.load();

  @override
  Widget build(BuildContext context) {
    final rScreen = FutureBuilder<void>(
      future: loading,
      builder: (pContext, pSnapshot) {
        if (pSnapshot.connectionState != ConnectionState.done) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }

        return widget.state.settings == null
            ? SetupScreen(state: widget.state)
            : HomeScreen(state: widget.state);
      },
    );

    return rScreen;
  }
}
