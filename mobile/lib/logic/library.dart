// Bibliothèque hors ligne : guides et schémas du contenu reçu, rangés par thème.

import '../models/quiz_package.dart';

/// Domaine des thèmes sans domaine et des guides sans thème, affiché en dernier.
const otherDomain = 'Autres';

/// Schéma de la bibliothèque, décrit par le texte de sa première question.
class LibrarySchema {
  const LibrarySchema({required this.name, required this.content, required this.description});

  final String name;
  final String content;
  final String description;
}

/// Thème qui a un guide ou des schémas ; un guide sans thème garde son titre.
class LibraryEntry {
  const LibraryEntry({
    required this.label,
    required this.domain,
    required this.guide,
    required this.schemas,
  });

  final String label;
  final String domain;
  final QuizGuide? guide;
  final List<LibrarySchema> schemas;

  /// Vrai si le thème, le guide ou un schéma contient le texte cherché.
  bool matches(String pQuery) {
    final vQuery = pQuery.trim().toLowerCase();

    final rMatches = vQuery.isEmpty ||
        label.toLowerCase().contains(vQuery) ||
        (guide?.title.toLowerCase().contains(vQuery) ?? false) ||
        (guide?.content.toLowerCase().contains(vQuery) ?? false) ||
        schemas.any((vSchema) => vSchema.description.toLowerCase().contains(vQuery));

    return rMatches;
  }
}

/// Entrées de la bibliothèque, dans l'ordre des thèmes de l'accueil.
List<LibraryEntry> buildLibrary(QuizPackage pPackage) {
  final vSchemasByTheme = <String, Map<String, LibrarySchema>>{};

  for (final vQuestion in pPackage.questions) {
    final vName = vQuestion.visual?['asset'] as String?;
    final vContent = pPackage.assets[vName];

    if (vName != null && vContent != null) {
      vSchemasByTheme.putIfAbsent(vQuestion.theme, () => {}).putIfAbsent(
            vName,
            () => LibrarySchema(
              name: vName,
              content: vContent,
              description: (vQuestion.visual!['alt'] as String?) ?? vName,
            ),
          );
    }
  }

  final vLinkedGuides = {for (final vTheme in pPackage.themes) vTheme.guide};

  // Ordre des thèmes reçu du PC, regroupé par domaine, « Autres » à la fin.
  final vByDomain = <String, List<LibraryEntry>>{};

  for (final vTheme in pPackage.themes) {
    if (pPackage.guides[vTheme.guide] != null || vSchemasByTheme[vTheme.key] != null) {
      vByDomain.putIfAbsent(vTheme.domain, () => []).add(
            LibraryEntry(
              label: vTheme.label,
              domain: vTheme.domain,
              guide: pPackage.guides[vTheme.guide],
              schemas: [...?vSchemasByTheme[vTheme.key]?.values],
            ),
          );
    }
  }

  for (final vGuide in pPackage.guides.values) {
    if (!vLinkedGuides.contains(vGuide.name)) {
      vByDomain.putIfAbsent(otherDomain, () => []).add(
            LibraryEntry(
                label: vGuide.title, domain: otherDomain, guide: vGuide, schemas: const []),
          );
    }
  }

  final rEntries = [
    for (final vEntry in vByDomain.entries)
      if (vEntry.key != otherDomain) ...vEntry.value,
    ...?vByDomain[otherDomain],
  ];

  return rEntries;
}
