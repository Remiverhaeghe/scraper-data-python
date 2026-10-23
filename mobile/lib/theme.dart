// Couleurs et icônes de l'application, reprises du bureau (gui/theme.py).

import 'package:flutter/material.dart';

/// Bleu principal de JobBoard Perso, mêmes teintes que le bureau et le web.
const primaryColor = Color(0xFF155FCC);

/// Vert et rouge lisibles en texte : foncés sur fond clair, clairs sur fond sombre.
Color successColorOf(BuildContext pContext) => Theme.of(pContext).brightness == Brightness.dark
    ? const Color(0xFF4ADE80)
    : const Color(0xFF15803D);

Color dangerColorOf(BuildContext pContext) => Theme.of(pContext).brightness == Brightness.dark
    ? const Color(0xFFF87171)
    : const Color(0xFFC81E1E);

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
