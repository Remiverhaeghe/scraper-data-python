// Scan du QR code de connexion : retourne l'adresse et le jeton du serveur.

import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../l10n/texts.dart';
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
      appBar: AppBar(title: Text(context.texts.scanScannerQrCode)),
      body: Column(
        children: [
          Expanded(
            child: MobileScanner(
              controller: controller,
              onDetect: handle,
              errorBuilder: (_, pError) => Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text(
                    context.texts.scanCameraIndisponibleAutorisezDans,
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
                  ? "Ce QR code n'est pas celui de Tremplin : sur le PC, "
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
