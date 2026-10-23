// Éléments d'une question : extrait de code, schéma SVG et résultat corrigé.

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../logic/grading.dart';
import '../theme.dart';

/// Extrait de code en police à chasse fixe, défilant horizontalement.
class CodeBlock extends StatelessWidget {
  const CodeBlock({super.key, required this.code});

  final String code;

  @override
  Widget build(BuildContext context) {
    final rBlock = Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: SelectableText(code, style: const TextStyle(fontFamily: 'monospace')),
      ),
    );

    return rBlock;
  }
}

/// Indique si un schéma est nettement plus large que haut, d'après son viewBox.
bool isWideSchema(String pContent) {
  final vMatch = RegExp(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"').firstMatch(pContent);
  final vWidth = double.tryParse(vMatch?.group(1) ?? '') ?? 0;
  final vHeight = double.tryParse(vMatch?.group(2) ?? '') ?? 0;

  final rWide = vHeight > 0 && vWidth / vHeight > 1.3;

  return rWide;
}

/// Schéma SVG livré avec la question, avec sa description ; un appui l'ouvre en
/// plein écran, où il se lit à la taille d'un écran de PC.
class SchemaView extends StatelessWidget {
  const SchemaView({super.key, required this.content, required this.description});

  final String content;
  final String description;

  void openFullScreen(BuildContext pContext) {
    Navigator.of(pContext).push(
      MaterialPageRoute<void>(
        fullscreenDialog: true,
        builder: (_) => SchemaScreen(content: content, description: description),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final vTheme = Theme.of(context);

    final rView = Semantics(
      label: description,
      button: true,
      child: InkWell(
        onTap: () => openFullScreen(context),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Stack(
              children: [
                ConstrainedBox(
                  constraints: const BoxConstraints(maxHeight: 280),
                  child: SvgPicture.string(content, fit: BoxFit.contain),
                ),
                Positioned(
                  right: 4,
                  bottom: 4,
                  child: Icon(Icons.open_in_full, size: 20, color: vTheme.colorScheme.primary),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              "Touchez le schéma pour l'agrandir. $description",
              style: vTheme.textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );

    return rView;
  }
}

/// Schéma en plein écran : un schéma large est tourné pour occuper la longueur
/// du téléphone tenu droit, et se zoome du bout des doigts.
class SchemaScreen extends StatefulWidget {
  const SchemaScreen({super.key, required this.content, required this.description});

  final String content;
  final String description;

  @override
  State<SchemaScreen> createState() => _SchemaScreenState();
}

class _SchemaScreenState extends State<SchemaScreen> {
  late bool rotated = isWideSchema(widget.content);

  @override
  Widget build(BuildContext context) {
    final vPortrait = MediaQuery.orientationOf(context) == Orientation.portrait;

    final rScreen = Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('Schéma'),
        actions: [
          IconButton(
            tooltip: 'Tourner le schéma',
            icon: const Icon(Icons.screen_rotation_alt),
            onPressed: () => setState(() => rotated = !rotated),
          ),
        ],
      ),
      body: Semantics(
        label: widget.description,
        child: InteractiveViewer(
          maxScale: 6,
          child: Center(
            child: RotatedBox(
              quarterTurns: rotated && vPortrait ? 1 : 0,
              child: SvgPicture.string(widget.content, fit: BoxFit.contain),
            ),
          ),
        ),
      ),
    );

    return rScreen;
  }
}

/// Correction : verdict, réponse donnée, réponse attendue et explication.
class ResultPanel extends StatelessWidget {
  const ResultPanel({super.key, required this.grade, required this.explanation});

  final Grade grade;
  final String explanation;

  @override
  Widget build(BuildContext context) {
    final vColor = grade.correct ? successColorOf(context) : dangerColorOf(context);

    final rPanel = Card(
      shape: RoundedRectangleBorder(
        side: BorderSide(color: vColor, width: 1.5),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(grade.correct ? Icons.check_circle : Icons.cancel, color: vColor),
                const SizedBox(width: 8),
                Text(
                  grade.correct ? 'Bonne réponse' : 'Réponse incorrecte',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(color: vColor),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (!grade.correct) Text('Votre réponse : ${grade.given}'),
            Text(
              'Réponse : ${grade.expected}',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            if (explanation.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(explanation),
            ],
          ],
        ),
      ),
    );

    return rPanel;
  }
}
