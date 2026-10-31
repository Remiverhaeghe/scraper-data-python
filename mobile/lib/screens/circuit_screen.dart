// Schémas électriques, hors ligne : montages guidés et mode libre. Le schéma se
// construit au toucher sur le même dessin que le PC ; un montage réussi part au
// PC, qui le resimule à la synchronisation.

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../logic/circuit.dart';
import '../logic/circuit_editor.dart';
import '../logic/circuit_levels.dart';
import '../logic/python_compat.dart';
import '../revision_state.dart';

class CircuitListScreen extends StatelessWidget {
  const CircuitListScreen({super.key, required this.state});

  final RevisionState state;

  void open(BuildContext pContext, Map<String, dynamic>? pLevel) => Navigator.of(pContext).push(
        MaterialPageRoute<void>(builder: (_) => CircuitScreen(state: state, level: pLevel)),
      );

  @override
  Widget build(BuildContext pContext) => Scaffold(
        appBar: AppBar(title: const Text('Schémas électriques')),
        body: ListenableBuilder(
          listenable: state,
          builder: (pContext, _) => ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Card(
                child: ListTile(
                  leading: const Icon(Icons.draw_outlined),
                  title: const Text('Schéma libre'),
                  subtitle: const Text('Tous les composants, pour essayer vos propres montages'),
                  onTap: () => open(pContext, null),
                ),
              ),
              for (final vLevel in state.circuitLevels)
                Card(
                  child: ListTile(
                    leading: Icon(
                      state.circuitPassed.contains(vLevel['id'])
                          ? Icons.check_circle
                          : Icons.electrical_services,
                    ),
                    title: Text(vLevel['title'] as String),
                    subtitle: Text(vLevel['goal'] as String,
                        maxLines: 3, overflow: TextOverflow.ellipsis),
                    onTap: () => open(pContext, vLevel),
                  ),
                ),
            ],
          ),
        ),
      );
}

/// Dessin SVG zoomable, ajusté à la largeur au départ ; pOnTap reçoit les coordonnées du dessin.
class ZoomableSvg extends StatefulWidget {
  const ZoomableSvg({super.key, required this.svg, this.onTap});

  final String svg;
  final void Function(Offset pPosition)? onTap;

  @override
  State<ZoomableSvg> createState() => _ZoomableSvgState();
}

class _ZoomableSvgState extends State<ZoomableSvg> {
  final viewer = TransformationController();
  double? fitted;

  double _size(String pName) =>
      double.parse(RegExp('$pName="([0-9.]+)"').firstMatch(widget.svg)!.group(1)!);

  @override
  void dispose() {
    viewer.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext pContext) {
    final vWidth = _size('width');
    final vHeight = _size('height');

    return LayoutBuilder(builder: (pContext, pConstraints) {
      final vScale = pConstraints.maxWidth / vWidth;

      if (fitted != vScale) {
        fitted = vScale;
        viewer.value = Matrix4.diagonal3Values(vScale, vScale, 1);
      }

      return SizedBox(
        height: vHeight * vScale,
        child: ClipRect(
          child: InteractiveViewer(
            transformationController: viewer,
            constrained: false,
            minScale: vScale,
            maxScale: 3,
            child: GestureDetector(
              onTapUp:
                  widget.onTap == null ? null : (pDetails) => widget.onTap!(pDetails.localPosition),
              child: SvgPicture.string(widget.svg, width: vWidth, height: vHeight),
            ),
          ),
        ),
      );
    });
  }
}

class CircuitScreen extends StatefulWidget {
  const CircuitScreen({super.key, required this.state, this.level});

  final RevisionState state;

  /// Montage guidé, ou null pour le mode libre.
  final Map<String, dynamic>? level;

  @override
  State<CircuitScreen> createState() => _CircuitScreenState();
}

class _CircuitScreenState extends State<CircuitScreen> {
  late final CircuitDraft draft;
  final fields = <String, TextEditingController>{};
  String message = '';
  bool showHint = false;
  Map<String, dynamic>? run;
  bool first = false;
  Map<String, dynamic>? result;
  Map<String, dynamic> inputs = {};

  Map<String, dynamic>? get level => widget.level;

  String get key => level?['id'] as String? ?? '';

  @override
  void initState() {
    super.initState();

    final vLibrary = widget.state.circuitLibrary!;
    final vDraft = widget.state.circuitDraft(key);

    draft = CircuitDraft(
      vLibrary,
      Map<String, dynamic>.from(level?['palette'] as Map? ?? vLibrary.limits),
      vDraft?['schema'] as Map<String, dynamic>?,
    );

    for (final vEntry in (vDraft?['values'] as Map? ?? const {}).entries) {
      fields[vEntry.key as String] = TextEditingController(text: vEntry.value.toString());
    }
  }

  @override
  void dispose() {
    for (final vField in fields.values) {
      vField.dispose();
    }

    super.dispose();
  }

  Map<String, dynamic> get raw => {
        for (final vEntry in fields.entries)
          vEntry.key: vEntry.value.text.trim().replaceAll(',', '.'),
      };

  Map<String, double> get values => buildValues(
        draft.components,
        raw,
        (level?['values'] as Map?)?.cast<String, dynamic>(),
        level == null ? null : level!['editable'] as List? ?? const [],
      );

  TextEditingController field(String pId) =>
      fields.putIfAbsent(pId, () => TextEditingController(text: formatG(values[pId] ?? 0)));

  /// Le schéma a changé : les résultats ne valent plus, le brouillon est gardé.
  void changed([String pMessage = '']) {
    setState(() {
      message = pMessage;
      run = null;
      result = null;
    });
    widget.state.saveCircuitDraft(key, {'schema': draft.toSchema(), 'values': raw});
  }

  void add(String pType) {
    final vId = draft.add(pType);

    changed(vId == null ? '' : '${draft.label(vId)} placé : touchez ses bornes pour le relier.');
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

  void showSolution() {
    final (vComponents, vWires, vValues) = getSolution(level!);

    draft.clear();
    draft.components.addAll(vComponents);
    draft.wires.addAll(vWires);

    for (final vEntry in vValues.entries) {
      field(vEntry.key).text = formatG(vEntry.value);
    }

    changed('Solution affichée : vérifiez-la, ou simulez pour la manœuvrer.');
  }

  Future<void> check() async {
    if (draft.components.isEmpty) {
      setState(() => message = 'Placez au moins un composant.');
      return;
    }

    final vValues = values;
    final vRun = runCircuitLevel(draft.library, level!, draft.components, draft.wires, vValues);
    var vFirst = false;

    if (vRun['passed'] == true) {
      vFirst = await widget.state.recordCircuit(key, draft.toSchema(), vValues);
    }

    if (mounted) {
      setState(() {
        run = vRun;
        first = vFirst;
        result = vRun['result'] as Map<String, dynamic>?;
        inputs = Map<String, dynamic>.from(vRun['inputs'] as Map);
        message = '';
      });
    }
  }

  void simulate() {
    if (draft.components.isEmpty) {
      setState(() => message = 'Placez au moins un composant.');
      return;
    }

    setState(() {
      run = null;
      inputs = {};
      result = draft.library.circuit(draft.components, draft.wires, values).simulate(inputs);
    });
  }

  /// Manœuvre une commande ; une protection réarmée oublie son déclenchement.
  void operate(String pId, String pType) {
    final vInputs = {...inputs, pId: !((inputs[pId] ?? operableDefaults[pType]) as bool)};
    final vMemory = jsonDecode(jsonEncode(result!['memory'])) as Map<String, dynamic>;

    if (protections.contains(pType) && vInputs[pId] == true) {
      vMemory['tripped'] = [
        for (final vId in vMemory['tripped'] as List)
          if (vId != pId) vId
      ];
    }

    setState(() {
      inputs = vInputs;
      result =
          draft.library.circuit(draft.components, draft.wires, values).simulate(vInputs, vMemory);
    });
  }

  Widget buildPalette() => Wrap(
        spacing: 6,
        runSpacing: 2,
        children: [
          for (final vType in draft.limits.keys)
            if (draft.library.components.containsKey(vType))
              ActionChip(
                visualDensity: VisualDensity.compact,
                label: Text(
                  '${draft.library.components[vType]!['label']}'
                  '${draft.limit(vType) > 1 ? ' (${draft.count(vType)}/${draft.limit(vType)})' : ''}',
                ),
                onPressed: draft.canAdd(vType) ? () => add(vType) : null,
              ),
        ],
      );

  Widget buildValueFields() {
    final vEditable = getEditable(draft.components, level);

    return Column(
      children: [
        for (final vItem in vEditable)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: TextField(
              controller: field(vItem['id'] as String),
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              onChanged: (_) => changed(),
              decoration: InputDecoration(
                labelText: draft.label(vItem['id'] as String),
                suffixText: valueRanges[vItem['type']]!.$4,
                helperText: 'De ${formatG(valueRanges[vItem['type']]!.$2)} '
                    'à ${formatG(valueRanges[vItem['type']]!.$3)}',
                border: const OutlineInputBorder(),
                isDense: true,
              ),
            ),
          ),
      ],
    );
  }

  Widget buildRun() {
    final vRun = run!;
    final vTheme = Theme.of(context);
    final vPassed = vRun['passed'] == true;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          vPassed
              ? 'Montage réussi${first ? ' · +${widget.state.circuitXp} XP au retour sur le PC' : ''}'
              : 'Le montage ne répond pas encore à toutes les étapes.',
          style: vTheme.textTheme.titleMedium?.copyWith(
            color: vPassed ? Colors.green.shade700 : vTheme.colorScheme.error,
          ),
        ),
        for (final vCheck in vRun['checks'] as List)
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            leading: Icon(
              (vCheck as Map)['passed'] == true
                  ? Icons.check_circle_outline
                  : Icons.cancel_outlined,
              color: vCheck['passed'] == true ? Colors.green.shade700 : vTheme.colorScheme.error,
            ),
            title: Text(vCheck['message'] as String),
            subtitle: (vCheck['details'] as List).isEmpty
                ? null
                : Text((vCheck['details'] as List).join('\n')),
          ),
        if (vPassed) Text(level!['explanation'] as String? ?? ''),
      ],
    );
  }

  Widget buildSimulation() {
    final vResult = result!;
    final vParts = vResult['parts'] as Map;
    final vTheme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Circuit sous tension', style: vTheme.textTheme.titleMedium),
        for (final vFault in vResult['faults'] as List)
          Text(vFault as String, style: TextStyle(color: vTheme.colorScheme.error)),
        Wrap(
          spacing: 6,
          children: [
            for (final (vId, vType, vLabel) in getControls(draft.library, draft.components))
              FilterChip(
                label: Text('$vLabel : ${(vParts[vId] as Map)['status']}'),
                selected: (inputs[vId] ?? operableDefaults[vType]) as bool,
                onSelected: (_) => operate(vId, vType),
              ),
          ],
        ),
        const SizedBox(height: 8),
        ZoomableSvg(svg: draft.library.renderCircuit(draft.components, draft.wires, vResult)),
      ],
    );
  }

  @override
  Widget build(BuildContext pContext) {
    final vTheme = Theme.of(pContext);
    final vSelected = draft.selected;

    return Scaffold(
      appBar: AppBar(title: Text(level?['title'] as String? ?? 'Schéma libre')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(level?['goal'] as String? ??
              'Composez librement : le simulateur calcule tensions et courants.'),
          if (showHint) Text('Indice : ${level!['hint']}', style: vTheme.textTheme.bodySmall),
          const SizedBox(height: 8),
          buildPalette(),
          const SizedBox(height: 8),
          Container(
            decoration: BoxDecoration(border: Border.all(color: vTheme.dividerColor)),
            child: ZoomableSvg(svg: draft.render(), onTap: tap),
          ),
          Row(
            children: [
              Expanded(
                child: Text(
                  message.isEmpty
                      ? 'Touchez une borne puis une autre pour tirer un fil, un fil pour le retirer, '
                          'un composant puis une case vide pour le déplacer. Pincez pour zoomer.'
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
          ),
          buildValueFields(),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              if (level != null)
                FilledButton.icon(
                    onPressed: check,
                    icon: const Icon(Icons.task_alt),
                    label: const Text('Vérifier')),
              OutlinedButton.icon(
                  onPressed: simulate, icon: const Icon(Icons.bolt), label: const Text('Simuler')),
              if (level != null)
                TextButton(
                    onPressed: () => setState(() => showHint = true), child: const Text('Indice')),
              if (level != null)
                TextButton(onPressed: showSolution, child: const Text('Voir la solution')),
              TextButton(
                onPressed: () {
                  draft.clear();
                  changed();
                },
                child: const Text('Tout effacer'),
              ),
            ],
          ),
          if (run != null) buildRun(),
          if (result != null) buildSimulation(),
        ],
      ),
    );
  }
}
