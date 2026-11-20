// Couleurs, formes et transitions de l'application.
//
// Tremplin, c'est l'élan : une nuit indigo qui s'éclaircit vers un lever de soleil
// ambré, et la courbe d'un saut qui revient sur l'accueil, la connexion et l'icône.

import 'package:flutter/material.dart';

/// Indigo de la nuit avant le saut : couleur principale.
const primaryColor = Color(0xFF3B3A9E);

/// Ambre du lever de soleil : ce qui avance, l'objectif, la réussite du jour.
const sunriseColor = Color(0xFFF2A33A);

/// Corail : l'accent des moments forts (entretien proche, record).
const coralColor = Color(0xFFE8604C);

/// Nuit profonde, fond des en-têtes en dégradé.
const nightColor = Color(0xFF1A1847);

/// Dégradé des en-têtes : de la nuit vers l'indigo, avec une pointe de violet.
const elanGradient = LinearGradient(
  begin: Alignment.topLeft,
  end: Alignment.bottomRight,
  colors: [nightColor, primaryColor, Color(0xFF6A4FC8)],
);

/// Vert et rouge lisibles en texte : foncés sur fond clair, clairs sur fond sombre.
Color successColorOf(BuildContext pContext) => Theme.of(pContext).brightness == Brightness.dark
    ? const Color(0xFF4ADE80)
    : const Color(0xFF15803D);

Color dangerColorOf(BuildContext pContext) => Theme.of(pContext).brightness == Brightness.dark
    ? const Color(0xFFF87171)
    : const Color(0xFFC81E1E);

/// Durée des animations courtes ; zéro quand le téléphone demande de les réduire.
Duration motionOf(BuildContext pContext,
        [Duration pDuration = const Duration(milliseconds: 450)]) =>
    MediaQuery.maybeDisableAnimationsOf(pContext) ?? false ? Duration.zero : pDuration;

/// Passage d'un écran à l'autre : le nouvel écran monte un peu en apparaissant.
class ElanPageTransitionsBuilder extends PageTransitionsBuilder {
  const ElanPageTransitionsBuilder();

  @override
  Widget buildTransitions<T>(
    PageRoute<T> route,
    BuildContext context,
    Animation<double> animation,
    Animation<double> secondaryAnimation,
    Widget child,
  ) {
    final vCurve = CurvedAnimation(parent: animation, curve: Curves.easeOutCubic);
    final rTransition = FadeTransition(
      opacity: vCurve,
      child: SlideTransition(
        position: Tween(begin: const Offset(0, 0.04), end: Offset.zero).animate(vCurve),
        child: child,
      ),
    );

    return rTransition;
  }
}

ThemeData buildTheme(Brightness pBrightness) {
  final vScheme = ColorScheme.fromSeed(
    seedColor: primaryColor,
    brightness: pBrightness,
    secondary: pBrightness == Brightness.light ? const Color(0xFFB86E0B) : sunriseColor,
    tertiary: coralColor,
  );
  final vShape = RoundedRectangleBorder(borderRadius: BorderRadius.circular(18));
  final rTheme = ThemeData(
    useMaterial3: true,
    colorScheme: vScheme,
    scaffoldBackgroundColor:
        pBrightness == Brightness.light ? const Color(0xFFF5F5FB) : const Color(0xFF111127),
    cardTheme: CardThemeData(elevation: 0, shape: vShape, color: vScheme.surfaceContainerLow),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size(48, 52),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      indicatorColor: sunriseColor.withValues(alpha: 0.35),
      labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
    ),
    pageTransitionsTheme: const PageTransitionsTheme(
      builders: {
        TargetPlatform.android: ElanPageTransitionsBuilder(),
        TargetPlatform.iOS: ElanPageTransitionsBuilder(),
        TargetPlatform.linux: ElanPageTransitionsBuilder(),
      },
    ),
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
  'languages': Icons.translate,
};

IconData getDomainIcon(String? pName) {
  final rIcon = domainIcons[pName] ?? Icons.school_outlined;

  return rIcon;
}
