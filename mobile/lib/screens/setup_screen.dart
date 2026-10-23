// Configuration : adresse du serveur et jeton, vérifiés par une première
// synchronisation avant d'être enregistrés.

import 'package:flutter/material.dart';

import '../logic/offer_alerts.dart';
import '../revision_state.dart';
import '../services/api_client.dart';
import '../services/discovery.dart';
import '../services/revision_store.dart';
import 'home_screen.dart';
import 'scan_screen.dart';

class SetupScreen extends StatefulWidget {
  const SetupScreen({super.key, required this.state});

  final RevisionState state;

  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  late final addressController = TextEditingController(
    text: widget.state.settings?.address ?? '',
  );
  late final tokenController = TextEditingController(
    text: widget.state.settings?.token ?? '',
  );

  bool busy = false;
  bool searching = false;
  String? error;

  /// Empreinte du certificat HTTPS, reçue par le QR code : elle ne se saisit pas.
  late String? certificateSha256 = widget.state.settings?.certificateSha256;

  /// Cherche le serveur sur le Wi-Fi et remplit son adresse.
  Future<void> search() async {
    setState(() {
      searching = true;
      error = null;
    });

    final vAddress = await widget.state.discovery.discover(
      pKnownHost: getHost(widget.state.settings?.address),
      pScheme: addressController.text.trim().startsWith('https') ? 'https' : 'http',
    );

    if (!mounted) {
      return;
    }

    setState(() {
      searching = false;

      if (vAddress == null) {
        error = 'Aucun serveur trouvé : le téléphone est-il sur le Wi-Fi de la maison, '
            'et le serveur web lancé sur le PC ?';
      } else {
        addressController.text = vAddress;
      }
    });
  }

  /// Lit l'adresse et le jeton dans le QR code du PC, puis se connecte.
  Future<void> scan() async {
    final vSettings = await Navigator.of(context).push<ServerSettings>(
      MaterialPageRoute(builder: (_) => const ScanScreen()),
    );

    if (vSettings == null || !mounted) {
      return;
    }

    addressController.text = vSettings.address;
    tokenController.text = vSettings.token;
    certificateSha256 = vSettings.certificateSha256;
    await connect();
  }

  @override
  void dispose() {
    addressController.dispose();
    tokenController.dispose();
    super.dispose();
  }

  Future<void> connect() async {
    if (addressController.text.trim().isEmpty || tokenController.text.trim().isEmpty) {
      setState(() => error = "Saisissez l'adresse et le jeton.");
      return;
    }

    setState(() {
      busy = true;
      error = null;
    });

    try {
      final vReport = await widget.state.configure(
        ServerSettings(
          address: normalizeAddress(addressController.text),
          token: tokenController.text.trim(),
          // En HTTP, aucun certificat n'est à vérifier.
          certificateSha256: normalizeAddress(addressController.text).startsWith('https')
              ? certificateSha256
              : null,
        ),
      );

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Connecté : ${vReport.describe()}')),
      );
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute<void>(builder: (_) => HomeScreen(state: widget.state)),
        (_) => false,
      );
    } on ApiException catch (vException) {
      setState(() => error = vException.message);
    } on FormatException catch (vException) {
      setState(() => error = vException.message);
    } finally {
      if (mounted) {
        setState(() => busy = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final rScreen = Scaffold(
      appBar: AppBar(title: const Text('Connexion au serveur')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Text(
            "Sur le PC, ouvrez Paramètres, « Application mobile » : créez un jeton, "
            "puis scannez son QR code. Le téléphone doit être sur le même réseau "
            "que le PC, ou relié par Tailscale.",
          ),
          const SizedBox(height: 16),
          FilledButton.tonalIcon(
            onPressed: busy || searching ? null : scan,
            icon: const Icon(Icons.qr_code_scanner),
            label: const Text('Scanner le QR code'),
          ),
          const SizedBox(height: 8),
          const Text('ou saisissez-les :', textAlign: TextAlign.center),
          const SizedBox(height: 12),
          TextField(
            controller: addressController,
            keyboardType: TextInputType.url,
            autocorrect: false,
            decoration: const InputDecoration(
              labelText: 'Adresse du serveur',
              hintText: 'http://192.168.1.20:8000/api/v1',
              border: OutlineInputBorder(),
            ),
          ),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: searching || busy ? null : search,
              icon: searching
                  ? const SizedBox.square(
                      dimension: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.wifi_find),
              label: Text(
                searching ? 'Recherche sur le Wi-Fi…' : 'Rechercher le serveur sur le Wi-Fi',
              ),
            ),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: tokenController,
            obscureText: true,
            autocorrect: false,
            enableSuggestions: false,
            decoration: const InputDecoration(
              labelText: 'Jeton',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 20),
          if (error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Text(
                error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          FilledButton.icon(
            onPressed: busy ? null : connect,
            icon: busy
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.sync),
            label: const Text('Se connecter et télécharger'),
          ),
          const SizedBox(height: 24),
          const SizedBox(height: 8),
          Text('Apparence', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
          ListenableBuilder(
            listenable: widget.state,
            builder: (_, __) => SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'system', label: Text('Auto'), icon: Icon(Icons.brightness_auto)),
                ButtonSegment(value: 'light', label: Text('Clair'), icon: Icon(Icons.light_mode)),
                ButtonSegment(value: 'dark', label: Text('Sombre'), icon: Icon(Icons.dark_mode)),
              ],
              selected: {widget.state.appearance},
              onSelectionChanged: (pChoice) =>
                  widget.state.setDisplay(pAppearance: pChoice.first),
            ),
          ),
          const SizedBox(height: 16),
          Text('Taille du texte', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
          ListenableBuilder(
            listenable: widget.state,
            builder: (_, __) => SegmentedButton<double>(
              segments: const [
                ButtonSegment(value: 1.0, label: Text('Normale')),
                ButtonSegment(value: 1.15, label: Text('Grande')),
                ButtonSegment(value: 1.3, label: Text('Très grande')),
              ],
              selected: {widget.state.textScale},
              onSelectionChanged: (pChoice) =>
                  widget.state.setDisplay(pTextScale: pChoice.first),
            ),
          ),
          const SizedBox(height: 16),
          Text('Objectif du jour', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
          ListenableBuilder(
            listenable: widget.state,
            builder: (_, __) => SegmentedButton<int>(
              segments: [
                for (final vGoal in dailyGoals)
                  ButtonSegment(value: vGoal, label: Text('$vGoal')),
              ],
              selected: {widget.state.dailyGoal},
              onSelectionChanged: (pChoice) =>
                  widget.state.savePreference(dailyGoalPreference, pChoice.first),
            ),
          ),
          ListenableBuilder(
            listenable: widget.state,
            builder: (_, __) => SwitchListTile(
              title: const Text('Vibration à la correction'),
              subtitle: const Text('Courte si la réponse est juste, appuyée si elle est fausse'),
              value: widget.state.hapticsEnabled,
              onChanged: (pEnabled) => widget.state.savePreference(hapticsPreference, pEnabled),
            ),
          ),
          ListenableBuilder(
            listenable: widget.state,
            builder: (_, __) => SwitchListTile(
              title: const Text('Alerte des nouvelles offres'),
              subtitle: const Text(
                'Vérifiées toutes les 3 h environ quand le PC est joignable ; '
                'signalées si la correspondance atteint $offerAlertScore %',
              ),
              value: widget.state.offerAlertsEnabled,
              onChanged: (pEnabled) async {
                final vMessenger = ScaffoldMessenger.of(context);
                final vEnabled = await widget.state.setOfferAlerts(pEnabled);

                if (pEnabled && !vEnabled) {
                  vMessenger.showSnackBar(
                    const SnackBar(
                      content: Text('Notifications refusées : autorisez-les dans les réglages.'),
                    ),
                  );
                }
              },
            ),
          ),
          ListenableBuilder(
            listenable: widget.state,
            builder: (_, __) => SwitchListTile(
              title: const Text('Rappel quotidien à 18 h 30'),
              subtitle: const Text('Une notification avec le nombre de questions à revoir'),
              value: widget.state.reminderEnabled,
              onChanged: (pEnabled) async {
                final vMessenger = ScaffoldMessenger.of(context);
                final vEnabled = await widget.state.setReminder(pEnabled);

                if (pEnabled && !vEnabled) {
                  vMessenger.showSnackBar(
                    const SnackBar(
                      content: Text('Notifications refusées : autorisez-les dans les réglages.'),
                    ),
                  );
                }
              },
            ),
          ),
        ],
      ),
    );

    return rScreen;
  }
}
