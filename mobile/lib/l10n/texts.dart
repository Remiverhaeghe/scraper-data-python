import 'package:flutter/widgets.dart';

import 'gen/app_localizations.dart';

export 'gen/app_localizations.dart';

/// Textes de l'application, pris dans app_fr.arb.
extension Texts on BuildContext {
  /// Textes de la langue de l'application ; le français quand aucune n'est fournie, comme dans un
  /// test qui monte un écran seul.
  AppLocalizations get texts =>
      AppLocalizations.of(this) ?? lookupAppLocalizations(const Locale('fr'));
}
