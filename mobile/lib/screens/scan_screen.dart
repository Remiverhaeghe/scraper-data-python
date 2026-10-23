// Scan du QR code de connexion : retourne l'adresse et le jeton du serveur.

import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../services/connection_code.dart';

class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  final controller = MobileScannerController(formats: const [BarcodeFormat.qrCode]);

  bool done = false;
  bool wrongCode = false;

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  void handle(BarcodeCapture pCapture) {
    if (done) {
      return;
    }

    for (final vBarcode in pCapture.barcodes) {
      final vSettings = parseConnectionCode(vBarcode.rawValue);

      if (vSettings != null) {
        done = true;
        Navigator.of(context).pop(vSettings);
        return;
      }
    }

    if (!wrongCode) {
      setState(() => wrongCode = true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final rScreen = Scaffold(
      appBar: AppBar(title: const Text('Scanner le QR code')),
      body: Column(
        children: [
          Expanded(
            child: MobileScanner(
              controller: controller,
              onDetect: handle,
              errorBuilder: (_, pError) => const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text(
                    "Caméra indisponible : autorisez-la dans les réglages du téléphone, "
                    "ou saisissez l'adresse et le jeton.",
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text(
              wrongCode
                  ? "Ce QR code n'est pas celui de JobBoard Perso : sur le PC, "
                      'Paramètres, « Application mobile », bouton « QR code ».'
                  : 'Visez le QR code affiché sur le PC, dans Paramètres, '
                      '« Application mobile ».',
              textAlign: TextAlign.center,
            ),
          ),
        ],
      ),
    );

    return rScreen;
  }
}
