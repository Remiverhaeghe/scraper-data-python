// Couleurs et icônes de l'application, reprises du bureau (gui/theme.py).

import 'package:flutter/material.dart';

/// Bleu principal de JobBoard Perso.
const primaryColor = Color(0xFF1769E0);
const successColor = Color(0xFF16A34A);
const dangerColor = Color(0xFFDC2626);

ThemeData buildTheme(Brightness pBrightness) {
  final rTheme = ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(seedColor: primaryColor, brightness: pBrightness),
  );

  return rTheme;
}

/// Icônes des domaines : le serveur les nomme comme sur le PC (Lucide).
const domainIcons = {
  'terminal': Icons.terminal,
  'lock': Icons.lock_outline,
  'settings': Icons.settings_outlined,
  'database': Icons.storage_outlined,
  'cpu': Icons.memory,
  'code': Icons.code,
  'globe': Icons.public,
  'cloud': Icons.cloud_outlined,
  'shield': Icons.shield_outlined,
  'zap': Icons.bolt,
  'network': Icons.lan_outlined,
  'wrench': Icons.build_outlined,
  'factory': Icons.factory_outlined,
};

IconData getDomainIcon(String? pName) {
  final rIcon = domainIcons[pName] ?? Icons.school_outlined;

  return rIcon;
}
