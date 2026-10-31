// Guides pratiques et schémas du contenu reçu, consultables sans réseau, avec
// une recherche dans leur texte.

import 'package:flutter/material.dart';

import '../logic/library.dart';
import '../models/quiz_package.dart';
import '../widgets/question_parts.dart';
import 'guide_screen.dart';

class LibraryScreen extends StatefulWidget {
  const LibraryScreen({super.key, required this.package});

  final QuizPackage package;

  @override
  State<LibraryScreen> createState() => _LibraryScreenState();
}

class _LibraryScreenState extends State<LibraryScreen> {
  late final List<LibraryEntry> entries = buildLibrary(widget.package);

  String query = '';

  void open(Widget pScreen) {
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => pScreen));
  }

  @override
  Widget build(BuildContext context) {
    final vTheme = Theme.of(context);
    final vEntries = [
      for (final vEntry in entries)
        if (vEntry.matches(query)) vEntry,
    ];

    final rScreen = Scaffold(
      appBar: AppBar(title: const Text('Guides et schémas')),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          TextField(
            decoration: const InputDecoration(
              prefixIcon: Icon(Icons.search),
              hintText: 'Chercher un thème, un mot du guide…',
              border: OutlineInputBorder(),
            ),
            onChanged: (pValue) => setState(() => query = pValue),
          ),
          const SizedBox(height: 8),
          if (entries.isEmpty)
            const Padding(
              padding: EdgeInsets.all(24),
              child: Text(
                "Aucun guide ni schéma reçu : synchronisez depuis l'accueil.",
                textAlign: TextAlign.center,
              ),
            )
          else if (vEntries.isEmpty)
            const Padding(
              padding: EdgeInsets.all(24),
              child: Text('Aucun résultat.', textAlign: TextAlign.center),
            ),
          for (final (vIndex, vEntry) in vEntries.indexed) ...[
            if (vIndex == 0 || vEntries[vIndex - 1].domain != vEntry.domain)
              Padding(
                padding: const EdgeInsets.fromLTRB(4, 16, 4, 4),
                child: Text(vEntry.domain, style: vTheme.textTheme.titleMedium),
              ),
            Card(
              clipBehavior: Clip.antiAlias,
              child: ExpansionTile(
                leading: Icon(
                  vEntry.guide != null ? Icons.menu_book_outlined : Icons.schema_outlined,
                  color: vTheme.colorScheme.primary,
                ),
                title: Text(vEntry.label),
                subtitle: Text(describeEntry(vEntry)),
                children: [
                  if (vEntry.guide case final vGuide?)
                    ListTile(
                      leading: const Icon(Icons.article_outlined),
                      title: Text(vGuide.title),
                      onTap: () => open(GuideScreen(guide: vGuide)),
                    ),
                  for (final vSchema in vEntry.schemas)
                    ListTile(
                      leading: const Icon(Icons.image_outlined),
                      title: Text(vSchema.description),
                      onTap: () => open(
                        SchemaScreen(content: vSchema.content, description: vSchema.description),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ],
      ),
    );

    return rScreen;
  }
}

/// Résumé d'une entrée : « Guide · 3 schémas ».
String describeEntry(LibraryEntry pEntry) {
  final vCount = pEntry.schemas.length;

  final rText = [
    if (pEntry.guide != null) 'Guide',
    if (vCount > 0) '$vCount schéma${vCount > 1 ? 's' : ''}',
  ].join(' · ');

  return rText;
}
