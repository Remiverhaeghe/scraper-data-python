// Saisie d'une réponse selon le type de question. Chaque saisie remonte la
// réponse au format attendu par la correction, ou null tant qu'elle est incomplète.

import 'dart:convert';
import 'dart:math';

import 'package:flutter/material.dart';

import '../logic/circuit_drawing.dart';
import '../logic/circuit_editor.dart';
import '../logic/grading.dart';
import '../logic/review.dart';
import '../logic/schema_building.dart';
import '../models/quiz_package.dart';
import 'question_parts.dart';
import 'zoomable_svg.dart';

class QuestionInput extends StatelessWidget {
  const QuestionInput({
    super.key,
    required this.question,
    required this.random,
    required this.enabled,
    required this.onChanged,
  });

  final QuizQuestion question;
  final Random random;

  /// Faux une fois la réponse corrigée : elle ne peut plus être modifiée.
  final bool enabled;
  final ValueChanged<Object?> onChanged;

  @override
  Widget build(BuildContext context) {
    final Widget rInput;

    switch (question.type) {
      case 'numerique':
        rInput = NumericInput(question: question, enabled: enabled, onChanged: onChanged);
      case 'ordre':
        rInput = OrderInput(
          question: question,
          random: random,
          enabled: enabled,
          onChanged: onChanged,
        );
      case 'association':
        rInput = PairsInput(
          question: question,
          random: random,
          enabled: enabled,
          onChanged: onChanged,
        );
      case 'revue':
        rInput = ReviewInput(
          question: question,
          random: random,
          enabled: enabled,
          onChanged: onChanged,
        );
      case 'construction':
        rInput = ConstructionInput(
          question: question,
          random: random,
          enabled: enabled,
          onChanged: onChanged,
        );
      default:
        rInput = ChoiceInput(
          question: question,
          random: random,
          enabled: enabled,
          onChanged: onChanged,
        );
    }

    return rInput;
  }
}

/// QCM : la réponse est l'indice d'origine du choix, mélangé à l'affichage.
class ChoiceInput extends StatefulWidget {
  const ChoiceInput({
    super.key,
    required this.question,
    required this.random,
    required this.enabled,
    required this.onChanged,
  });

  final QuizQuestion question;
  final Random random;
  final bool enabled;
  final ValueChanged<Object?> onChanged;

  @override
  State<ChoiceInput> createState() => _ChoiceInputState();
}

class _ChoiceInputState extends State<ChoiceInput> {
  late final order = shuffledIndexes(widget.question.choices.length, widget.random);
  int? selected;

  @override
  Widget build(BuildContext context) {
    final vChoices = widget.question.choices;

    final rInput = Column(
      children: [
        for (final vIndex in order)
          Card(
            child: ListTile(
              enabled: widget.enabled,
              leading: Icon(
                selected == vIndex ? Icons.radio_button_checked : Icons.radio_button_off,
              ),
              title: Text(vChoices[vIndex]),
              onTap: () {
                setState(() => selected = vIndex);
                widget.onChanged(vIndex);
              },
            ),
          ),
      ],
    );

    return rInput;
  }
}

/// Revue de code : la réponse liste les indices d'origine des constats cochés,
/// ou null tant qu'aucun ne l'est.
class ReviewInput extends StatefulWidget {
  const ReviewInput({
    super.key,
    required this.question,
    required this.random,
    required this.enabled,
    required this.onChanged,
  });

  final QuizQuestion question;
  final Random random;
  final bool enabled;
  final ValueChanged<Object?> onChanged;

  @override
  State<ReviewInput> createState() => _ReviewInputState();
}

class _ReviewInputState extends State<ReviewInput> {
  late final order = shuffledIndexes(widget.question.choices.length, widget.random);
  final checked = <int>{};

  void toggle(int pIndex, bool pChecked) {
    setState(() => pChecked ? checked.add(pIndex) : checked.remove(pIndex));
    widget.onChanged(checked.isEmpty ? null : checked.toList());
  }

  @override
  Widget build(BuildContext context) {
    final vChoices = widget.question.choices;

    final rInput = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.only(bottom: 8),
          child: Text('Cochez tous les défauts réels de cet extrait, et eux seuls.'),
        ),
        for (final vIndex in order)
          Card(
            child: CheckboxListTile(
              enabled: widget.enabled,
              value: checked.contains(vIndex),
              title: Text(vChoices[vIndex]),
              onChanged: (pValue) => toggle(vIndex, pValue ?? false),
            ),
          ),
      ],
    );

    return rInput;
  }
}

/// Calcul : la réponse est le texte saisi, unité comprise.
class NumericInput extends StatelessWidget {
  const NumericInput({
    super.key,
    required this.question,
    required this.enabled,
    required this.onChanged,
  });

  final QuizQuestion question;
  final bool enabled;
  final ValueChanged<Object?> onChanged;

  @override
  Widget build(BuildContext context) {
    final vUnit = question.unit;

    final rInput = TextField(
      enabled: enabled,
      autocorrect: false,
      decoration: InputDecoration(
        labelText: vUnit.isEmpty ? 'Valeur' : 'Valeur en $vUnit',
        helperText: vUnit.isEmpty ? null : 'Préfixe accepté : « 2,3 m$vUnit »',
        border: const OutlineInputBorder(),
      ),
      onChanged: (pText) => onChanged(pText.trim().isEmpty ? null : pText),
    );

    return rInput;
  }
}

/// Remise en ordre : la réponse liste les indices d'origine dans l'ordre choisi.
class OrderInput extends StatefulWidget {
  const OrderInput({
    super.key,
    required this.question,
    required this.random,
    required this.enabled,
    required this.onChanged,
  });

  final QuizQuestion question;
  final Random random;
  final bool enabled;
  final ValueChanged<Object?> onChanged;

  @override
  State<OrderInput> createState() => _OrderInputState();
}

class _OrderInputState extends State<OrderInput> {
  late final List<int> order = shuffledIndexes(
    widget.question.items.length,
    widget.random,
    pAvoidIdentity: true,
  );

  @override
  void initState() {
    super.initState();

    // L'ordre de départ est déjà une réponse : il peut être validé tel quel.
    WidgetsBinding.instance.addPostFrameCallback((_) => widget.onChanged(List<int>.of(order)));
  }

  /// pNewIndex est déjà la position finale, une fois l'élément retiré.
  void move(int pOldIndex, int pNewIndex) {
    setState(() => order.insert(pNewIndex, order.removeAt(pOldIndex)));

    widget.onChanged(List<int>.of(order));
  }

  @override
  Widget build(BuildContext context) {
    final vItems = widget.question.items;

    final rInput = ReorderableListView(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      buildDefaultDragHandles: widget.enabled,
      onReorderItem: move,
      children: [
        for (var vPosition = 0; vPosition < order.length; vPosition++)
          Card(
            key: ValueKey<int>(order[vPosition]),
            child: ListTile(
              leading: CircleAvatar(child: Text('${vPosition + 1}')),
              title: Text(vItems[order[vPosition]]),
              trailing: widget.enabled ? const Icon(Icons.drag_handle) : null,
            ),
          ),
      ],
    );

    return rInput;
  }
}

/// Association : pour chaque élément, l'indice d'origine de la correspondance choisie.
class PairsInput extends StatefulWidget {
  const PairsInput({
    super.key,
    required this.question,
    required this.random,
    required this.enabled,
    required this.onChanged,
  });

  final QuizQuestion question;
  final Random random;
  final bool enabled;
  final ValueChanged<Object?> onChanged;

  @override
  State<PairsInput> createState() => _PairsInputState();
}

class _PairsInputState extends State<PairsInput> {
  late final List<List<String>> pairs = widget.question.pairs;
  late final List<int> rightOrder = shuffledIndexes(pairs.length, widget.random);
  late final List<int?> selections = List<int?>.filled(pairs.length, null);

  void select(int pLeft, int? pRight) {
    setState(() => selections[pLeft] = pRight);

    widget.onChanged(
      selections.contains(null) ? null : [for (final vRight in selections) vRight!],
    );
  }

  @override
  Widget build(BuildContext context) {
    final rInput = Column(
      children: [
        for (var vLeft = 0; vLeft < pairs.length; vLeft++)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(pairs[vLeft][0], style: Theme.of(context).textTheme.titleSmall),
                  DropdownButton<int>(
                    isExpanded: true,
                    hint: const Text('Choisir la correspondance'),
                    value: selections[vLeft],
                    onChanged: widget.enabled ? (pRight) => select(vLeft, pRight) : null,
                    items: [
                      for (final vRight in rightOrder)
                        DropdownMenuItem<int>(value: vRight, child: Text(pairs[vRight][1])),
                    ],
                  ),
                ],
              ),
            ),
          ),
      ],
    );

    return rInput;
  }
}

/// Schéma à construire : la réponse est le schéma posé (composants et fils), ou
/// null tant qu'il est vide. Une fois corrigé, le schéma attendu s'affiche dessous.
class ConstructionInput extends StatefulWidget {
  const ConstructionInput({
    super.key,
    required this.question,
    required this.random,
    required this.enabled,
    required this.onChanged,
  });

  final QuizQuestion question;
  final Random random;
  final bool enabled;
  final ValueChanged<Object?> onChanged;

  @override
  State<ConstructionInput> createState() => _ConstructionInputState();
}

class _ConstructionInputState extends State<ConstructionInput> {
  late final CircuitDraft draft = CircuitDraft(
    CircuitLibrary(widget.question.schemaLibrary),
    Map<String, dynamic>.from(widget.question.paletteLimits),
  );

  // Attendus et leurres mélangés, comme la palette du PC
  late final List<String> palette = [...widget.question.paletteLimits.keys]..shuffle(widget.random);
  String message = '';

  /// Copie détachée du brouillon, qui continue d'évoluer après l'envoi.
  void changed(String pMessage) {
    setState(() => message = pMessage);
    widget.onChanged(
      draft.components.isEmpty ? null : jsonDecode(jsonEncode(draft.toSchema())),
    );
  }

  void add(String pType) {
    final vId = draft.add(pType);

    changed(vId == null
        ? 'Plus de case libre.'
        : '${draft.label(vId)} placé : touchez ses bornes pour le relier.');
  }

  void tap(Offset pPosition) {
    final vBefore = jsonEncode(draft.toSchema());
    final vMessage = draft.tap(pPosition.dx, pPosition.dy);

    if (jsonEncode(draft.toSchema()) != vBefore) {
      changed(vMessage);
    } else {
      setState(() => message = vMessage);
    }
  }

  String renderExpected() {
    final vLabels = SchemaGrader(widget.question).labels;

    final rSvg = draft.library.renderSchema(
      {
        for (final vItem in widget.question.components)
          (vItem['id'] ?? vItem['type']) as String: (
            vItem['type'] as String,
            (vItem['x'] as int, vItem['y'] as int),
            vLabels[vItem['id'] ?? vItem['type']]!,
          ),
      },
      widget.question.connections,
      'Schéma attendu',
    );

    return rSvg;
  }

  /// Schéma construit à la correction : chaque composant porte le nom de son
  /// équivalent attendu, les fils absents du schéma attendu sont en rouge.
  String renderAnswer() {
    final vGrader = SchemaGrader(widget.question);
    String rSvg;

    try {
      final vMatch = vGrader.matchAnswer(draft.toSchema());
      final vLabels = vGrader.answerLabels(vMatch);

      rSvg = draft.library.renderSchema(
        {
          for (final vEntry in vMatch.answer.instances.entries)
            vEntry.key: (vEntry.value, vMatch.answer.positions[vEntry.key]!, vLabels[vEntry.key]!),
        },
        vMatch.answer.wires,
        'Votre schéma',
        vGrader.findWrongWires(vMatch),
      );
    } on UnreadableAnswer {
      rSvg = draft.render();
    }

    return rSvg;
  }

  @override
  Widget build(BuildContext context) {
    final vTheme = Theme.of(context);
    final vSelected = draft.selected;

    final rInput = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          spacing: 6,
          runSpacing: 2,
          children: [
            for (final vType in palette)
              ActionChip(
                visualDensity: VisualDensity.compact,
                label: Text(
                  '${draft.library.components[vType]!['label']}'
                  '${draft.limit(vType) > 1 ? ' (${draft.count(vType)}/${draft.limit(vType)})' : ''}',
                ),
                onPressed: widget.enabled && draft.canAdd(vType) ? () => add(vType) : null,
              ),
          ],
        ),
        const SizedBox(height: 8),
        if (!widget.enabled) ...[
          Text('Votre schéma', style: vTheme.textTheme.titleSmall),
          const SizedBox(height: 4),
        ],
        Container(
          decoration: BoxDecoration(border: Border.all(color: vTheme.dividerColor)),
          child: widget.enabled
              ? ZoomableSvg(svg: draft.render(), onTap: tap)
              : ZoomableSvg(svg: renderAnswer()),
        ),
        if (widget.enabled)
          Row(
            children: [
              Expanded(
                child: Text(
                  message.isEmpty
                      ? 'Touchez un composant de la palette pour le placer, une borne puis une '
                          'autre pour tirer un fil, un fil pour le retirer. Pincez pour zoomer.'
                      : message,
                  style: vTheme.textTheme.bodySmall,
                ),
              ),
              if (vSelected != null)
                IconButton(
                  tooltip: 'Supprimer ${draft.label(vSelected)}',
                  icon: const Icon(Icons.delete_outline),
                  onPressed: () {
                    final vLabel = draft.label(vSelected);
                    draft.remove(vSelected);
                    changed('$vLabel supprimé.');
                  },
                ),
            ],
          )
        else ...[
          const SizedBox(height: 12),
          Text('Schéma attendu', style: vTheme.textTheme.titleSmall),
          const SizedBox(height: 4),
          SchemaView(content: renderExpected(), description: 'Schéma attendu'),
        ],
      ],
    );

    return rInput;
  }
}
