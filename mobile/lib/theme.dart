// Couleurs, formes et transitions de l'application.
//
// Tremplin, c'est la piscine : l'eau turquoise du bassin, le jaune du plongeoir,
// le corail des bouées. Le livre ouvert sert de tremplin : on révise, on saute.

import 'package:flutter/material.dart';

/// Bleu du bassin : couleur principale.
const primaryColor = Color(0xFF0E6F8C);

/// Turquoise de l'eau en surface.
const waterColor = Color(0xFF35C2CF);

/// Jaune du plongeoir : ce qui avance, l'objectif, la réussite du jour.
const boardColor = Color(0xFFFFC23D);

/// Corail des bouées : l'accent des moments forts (entretien proche, record).
const coralColor = Color(0xFFFF6A55);

/// Bleu du grand bain, fond des en-têtes et texte sur le jaune.
const deepColor = Color(0xFF0B4F66);

/// Dégradé des en-têtes : de la surface vers le grand bain.
const poolGradient = LinearGradient(
  begin: Alignment.topCenter,
  end: Alignment.bottomCenter,
  colors: [Color(0xFF2FB8C7), primaryColor, deepColor],
  stops: [0, 0.55, 1],
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

/// Passage d'un écran à l'autre : le nouvel écran remonte à la surface en apparaissant.
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
    secondary: pBrightness == Brightness.light ? const Color(0xFF9A6A00) : boardColor,
    tertiary: coralColor,
  );
  final vShape = RoundedRectangleBorder(borderRadius: BorderRadius.circular(18));
  final rTheme = ThemeData(
    useMaterial3: true,
    colorScheme: vScheme,
    scaffoldBackgroundColor:
        pBrightness == Brightness.light ? const Color(0xFFF2FAFB) : const Color(0xFF0A1F27),
    cardTheme: CardThemeData(elevation: 0, shape: vShape, color: vScheme.surfaceContainerLow),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size(48, 52),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      indicatorColor: waterColor.withValues(alpha: 0.35),
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
