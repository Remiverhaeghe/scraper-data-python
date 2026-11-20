// Connexion au PC : le téléphone cherche le serveur sur le Wi-Fi tout seul, puis
// échange le code à 6 chiffres affiché par le PC contre le jeton. Le QR code et la
// saisie de l'adresse et du jeton restent en secours.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../l10n/texts.dart';
import '../revision_state.dart';
import '../services/api_client.dart';
import '../services/discovery.dart';
import '../services/revision_store.dart';
import '../services/starter_package.dart';
import '../theme.dart';
import '../widgets/brand.dart';
import 'home_screen.dart';
import 'scan_screen.dart';

/// Où en est la recherche du PC sur le Wi-Fi.
enum SearchStatus { searching, found, missing }

class ConnectScreen extends StatefulWidget {
  const ConnectScreen({super.key, required this.state, this.bundle});

  final RevisionState state;

  /// Fichiers livrés avec l'appli ; remplaçable dans les tests.
  final AssetBundle? bundle;

  @override
  State<ConnectScreen> createState() => _ConnectScreenState();
}

class _ConnectScreenState extends State<ConnectScreen> {
  final codeController = TextEditingController();
  late final addressController = TextEditingController(
    text: widget.state.settings?.address ?? '',
  );
  late final tokenController = TextEditingController(
    text: widget.state.settings?.token ?? '',
  );

  SearchStatus status = SearchStatus.searching;
  String? foundAddress;
  bool busy = false;
  String? error;

  /// Empreinte du certificat HTTPS, reçue par le QR code ou avec le jeton.
  late String? certificateSha256 = widget.state.settings?.certificateSha256;

  @override
  void initState() {
    super.initState();
    search();
  }

  @override
  void dispose() {
    codeController.dispose();
    addressController.dispose();
    tokenController.dispose();
    super.dispose();
  }

  /// Cherche le PC sur le Wi-Fi, en commençant par l'adresse déjà connue.
  Future<void> search() async {
    setState(() {
      status = SearchStatus.searching;
      error = null;
    });

    final vAddress = await widget.state.discovery.discover(
      pKnownHost: getHost(widget.state.settings?.address),
      pScheme: (widget.state.settings?.address ?? '').startsWith('https') ? 'https' : 'http',
    );

    if (!mounted) {
      return;
    }

    setState(() {
      foundAddress = vAddress;
      status = vAddress == null ? SearchStatus.missing : SearchStatus.found;

      if (vAddress != null) {
        addressController.text = vAddress;
      }
    });
  }

  /// Envoie le code tapé ; se connecte dès qu'il est accepté.
  Future<void> pair() async {
    final vAddress = foundAddress;

    if (vAddress == null || codeController.text.replaceAll(' ', '').length != 6) {
      return;
    }

    setState(() {
      busy = true;
      error = null;
    });

    try {
      final vSettings = await widget.state.discovery.pair(vAddress, codeController.text);
      await finish(vSettings);
    } on ApiException catch (vException) {
      if (mounted) {
        setState(() => error = vException.message);
      }
    } finally {
      if (mounted) {
        setState(() => busy = false);
      }
    }
  }

  /// Lit l'adresse et le jeton dans le QR code du PC, puis se connecte.
  Future<void> scan() async {
    final vSettings = await Navigator.of(context).push<ServerSettings>(
      MaterialPageRoute(builder: (_) => const ScanScreen()),
    );

    if (vSettings != null && mounted) {
      await guarded(() => finish(vSettings));
    }
  }

  /// Adresse et jeton saisis à la main.
  Future<void> connectManually() async {
    if (addressController.text.trim().isEmpty || tokenController.text.trim().isEmpty) {
      setState(() => error = "Saisissez l'adresse et le jeton.");
      return;
    }

    final vAddress = normalizeAddress(addressController.text);
    await guarded(
      () => finish(
        ServerSettings(
          address: vAddress,
          token: tokenController.text.trim(),
          // En HTTP, aucun certificat n'est à vérifier.
          certificateSha256: vAddress.startsWith('https') ? certificateSha256 : null,
        ),
      ),
    );
  }

  Future<void> guarded(Future<void> Function() pAction) async {
    setState(() {
      busy = true;
      error = null;
    });

    try {
      await pAction();
    } on ApiException catch (vException) {
      if (mounted) {
        setState(() => error = vException.message);
      }
    } on FormatException catch (vException) {
      if (mounted) {
        setState(() => error = vException.message);
      }
    } finally {
      if (mounted) {
        setState(() => busy = false);
      }
    }
  }

  /// Enregistre la connexion par une première synchronisation, puis ouvre l'accueil.
  Future<void> finish(ServerSettings pSettings) async {
    final vReport = await widget.state.configure(pSettings);

    if (!mounted) {
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(context.texts.connectConnecte(vReport.describe()))),
    );
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute<void>(builder: (_) => HomeScreen(state: widget.state)),
      (_) => false,
    );
  }

  /// Installe le paquet livré : la révision marche sans le PC ni le réseau.
  Future<void> startWithoutServer() async {
    setState(() => busy = true);
    try {
      await widget.state.startWithoutServer(await loadStarterPackage(widget.bundle));
    } finally {
      if (mounted) {
        setState(() => busy = false);
      }
    }
  }

  Widget buildStatus(BuildContext pContext) {
    final vTheme = Theme.of(pContext);

    final rStatus = switch (status) {
      SearchStatus.searching => ListTile(
          key: const ValueKey('searching'),
          leading: const SizedBox.square(
            dimension: 24,
            child: const CircularProgressIndicator(strokeWidth: 3),
          ),
          title: Text(context.texts.connectRechercheTonPcSur),
        ),
      SearchStatus.found => ListTile(
          key: const ValueKey('found'),
          leading: Icon(Icons.check_circle, color: successColorOf(pContext)),
          title: Text(context.texts.connectPcTrouve),
          subtitle: Text(getHost(foundAddress) ?? ''),
        ),
      SearchStatus.missing => ListTile(
          key: const ValueKey('missing'),
          leading: Icon(Icons.wifi_off, color: vTheme.colorScheme.error),
          title: Text(context.texts.connectPcIntrouvableSurCe),
          subtitle: Text(
            context.texts.connectTelephoneDoitEtreSur,
          ),
          trailing: IconButton(
            tooltip: context.texts.connectChercherNouveau,
            onPressed: search,
            icon: const Icon(Icons.refresh),
          ),
        ),
    };

    return rStatus;
  }

  @override
  Widget build(BuildContext context) {
    final vTheme = Theme.of(context);
    final vCanGoBack = Navigator.of(context).canPop();

    final rScreen = Scaffold(
      appBar: vCanGoBack ? AppBar(title: Text(context.texts.commonConnexionAuPc)) : null,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            PoolCard(
              child: Row(
                children: [
                  const SpringboardMark(size: 84),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          context.texts.connectTremplin,
                          style: vTheme.textTheme.headlineSmall!
                              .copyWith(color: Colors.white, fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: 4),
                        Text(context.texts.connectReviseToutSuiteMeme),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            if (widget.state.settings == null && widget.state.package == null) ...[
              const SizedBox(height: 16),
              FilledButton.icon(
                style: FilledButton.styleFrom(
                  backgroundColor: boardColor,
                  foregroundColor: deepColor,
                ),
                onPressed: busy ? null : startWithoutServer,
                icon: const Icon(Icons.menu_book_rounded),
                label: Text(context.texts.connectReviserSansPc),
              ),
            ],
            const SizedBox(height: 16),
            Card(
              child: AnimatedSwitcher(
                duration: motionOf(context, const Duration(milliseconds: 300)),
                child: buildStatus(context),
              ),
            ),
            AnimatedSize(
              duration: motionOf(context, const Duration(milliseconds: 300)),
              curve: Curves.easeOutCubic,
              child: status == SearchStatus.found
                  ? Padding(
                      padding: const EdgeInsets.only(top: 16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Text(
                            context.texts.connectSurPcParametresApplication,
                            style: vTheme.textTheme.bodyMedium,
                          ),
                          const SizedBox(height: 12),
                          TextField(
                            controller: codeController,
                            autofocus: true,
                            keyboardType: TextInputType.number,
                            textAlign: TextAlign.center,
                            maxLength: 7,
                            inputFormatters: [FilteringTextInputFormatter.allow(RegExp('[0-9 ]'))],
                            style: vTheme.textTheme.headlineMedium!.copyWith(letterSpacing: 8),
                            decoration: InputDecoration(
                              labelText: context.texts.connectCode6Chiffres,
                              counterText: '',
                              border: const OutlineInputBorder(),
                            ),
                            onChanged: (pText) {
                              // Les six chiffres tapés suffisent : pas de bouton à chercher.
                              if (pText.replaceAll(' ', '').length == 6 && !busy) {
                                pair();
                              }
                            },
                          ),
                          const SizedBox(height: 12),
                          FilledButton.icon(
                            onPressed: busy ? null : pair,
                            icon: busy
                                ? const SizedBox.square(
                                    dimension: 18,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  )
                                : const Icon(Icons.link),
                            label: Text(context.texts.connectConnecter),
                          ),
                        ],
                      ),
                    )
                  : const SizedBox(width: double.infinity),
            ),
            if (error != null)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Text(error!, style: TextStyle(color: vTheme.colorScheme.error)),
              ),
            const SizedBox(height: 20),
            OutlinedButton.icon(
              onPressed: busy ? null : scan,
              icon: const Icon(Icons.qr_code_scanner),
              label: Text(context.texts.connectScannerQrCodePc),
            ),
            const SizedBox(height: 8),
            ExpansionTile(
              tilePadding: EdgeInsets.zero,
              title: Text(context.texts.connectSaisirAdresseJeton),
              children: [
                TextField(
                  controller: addressController,
                  keyboardType: TextInputType.url,
                  autocorrect: false,
                  decoration: InputDecoration(
                    labelText: context.texts.connectAdresseServeur,
                    hintText: context.texts.connectHttp1921681,
                    border: const OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: tokenController,
                  obscureText: true,
                  autocorrect: false,
                  enableSuggestions: false,
                  decoration: InputDecoration(
                    labelText: context.texts.connectJeton,
                    border: const OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 8),
                Align(
                  alignment: Alignment.centerRight,
                  child: FilledButton.tonal(
                    onPressed: busy ? null : connectManually,
                    child: Text(context.texts.connectSeConnecter),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );

    return rScreen;
  }
}
