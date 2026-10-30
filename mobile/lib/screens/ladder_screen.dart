// Simulateur d'automate, hors ligne : écrire un programme ladder, le vérifier sur
// le scénario de test, puis piloter la machine au doigt. Le programme réussi
// part au PC, qui le revérifie à la synchronisation.

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../logic/ladder.dart';
import '../logic/ladder_game.dart';
import '../revision_state.dart';

const cycleDuration = Duration(milliseconds: 100);

// Le dessin ladder est refait tous les N cycles : assez pour suivre à l'œil
const drawEvery = 3;

// Sorties qui font tourner le moteur dessiné, comme sur le bureau
const motorOutputs = ['moteur', 'avant', 'arriere', 'ligne', 'pompe1', 'pompe2'];

class LadderListScreen extends StatelessWidget {
  const LadderListScreen({super.key, required this.state});

  final RevisionState state;

  @override
  Widget build(BuildContext pContext) => Scaffold(
        appBar: AppBar(title: const Text("Simulateur d'automate")),
        body: ListenableBuilder(
          listenable: state,
          builder: (pContext, _) => ListView(
            padding: const EdgeInsets.all(16),
            children: [
              for (final (vIndex, vLevel) in state.ladderLevels.indexed)
                Card(
                  child: ListTile(
                    leading: Icon(
                      state.ladderPassed.contains(vLevel['id'])
                          ? Icons.check_circle
                          : Icons.memory_outlined,
                    ),
                    title: Text('${vIndex + 1}. ${vLevel['title']}'),
                    subtitle: Text(vLevel['goal'] as String,
                        maxLines: 3, overflow: TextOverflow.ellipsis),
                    onTap: () => Navigator.of(pContext).push(
                      MaterialPageRoute<void>(
                          builder: (_) => LadderScreen(state: state, level: vLevel)),
                    ),
                  ),
                ),
            ],
          ),
        ),
      );
}

/// Machine simulée en une ligne : moteur, vérin, tapis ou broche.
String describeMachine(Simulator pSimulator) {
  final vValues = pSimulator.values;
  final vPosition = pSimulator.machine['position']!;

  final rText = switch (pSimulator.kind) {
    'verin' => 'Vérin : sorti à ${100 * vPosition ~/ verinStroke} %',
    'tapis' => 'Tapis : ${vValues['tapis'] == true ? 'en marche' : 'arrêté'}, '
        '${pSimulator.machine['run']! ~/ piecePeriod} pièce(s) passée(s)',
    'percage' => 'Broche : descendue à ${100 * vPosition ~/ spindleStroke} %'
        '${vValues['rotation'] == true ? ', en rotation' : ''}',
    _ =>
      'Moteur : ${motorOutputs.any((pName) => vValues[pName] == true) ? (vValues['arriere'] == true ? 'tourne en arrière' : 'tourne') : 'arrêté'}',
  };

  return rText;
}

class LadderScreen extends StatefulWidget {
  const LadderScreen({super.key, required this.state, required this.level});

  final RevisionState state;
  final Map<String, dynamic> level;

  @override
  State<LadderScreen> createState() => _LadderScreenState();
}

class _LadderScreenState extends State<LadderScreen> {
  late final TextEditingController editor;
  Map<String, dynamic>? run;
  bool first = false;
  Simulator? simulator;
  Timer? timer;
  final pressed = <String>{};
  final switched = <String>{};

  Map<String, dynamic> get level => widget.level;

  Set<String> get inputs => namesOf(level, 'input').toSet();

  List<Map<String, dynamic>> get operatorInputs => [
        for (final vVariable in level['variables'] as List)
          if ((vVariable as Map)['kind'] == 'input' && vVariable['control'] != 'sensor')
            Map<String, dynamic>.from(vVariable),
      ];

  @override
  void initState() {
    super.initState();
    editor = TextEditingController(text: widget.state.ladderProgram(level));
  }

  @override
  void dispose() {
    timer?.cancel();
    unawaited(widget.state.saveLadderProgram(level['id'] as String, editor.text));
    editor.dispose();
    super.dispose();
  }

  Future<void> check() async {
    stop();
    final vRun = runLevel(level, editor.text);
    var vFirst = false;

    await widget.state.saveLadderProgram(level['id'] as String, editor.text);

    if (vRun['passed'] == true) {
      vFirst = await widget.state.recordLadder(level['id'] as String, editor.text);
    }

    setState(() {
      run = vRun;
      first = vFirst;
    });
  }

  void toggleSimulation() {
    if (timer != null) {
      stop();
      return;
    }

    try {
      final vRungs = parseProgram(editor.text, inputs);

      setState(() {
        simulator = Simulator(level, vRungs);
        pressed.clear();
        switched.clear();
      });
      timer = Timer.periodic(cycleDuration, (_) => step());
    } on LadderError catch (vError) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(vError.message)));
    }
  }

  void stop() {
    timer?.cancel();
    setState(() => timer = null);
  }

  /// Un cycle : boutons de l'opérateur, programme, machine, puis dessin.
  void step() {
    final vSimulator = simulator!;

    for (final vVariable in operatorInputs) {
      final vName = vVariable['name'] as String;
      final vControl = vVariable['control'] as String?;
      final vActive = vControl == 'switch' || vControl == 'switch_nc'
          ? switched.contains(vName)
          : pressed.contains(vName);

      // Bouton à ouverture et contact de défaut : 1 au repos, 0 actionnés
      vSimulator.setInput(
          vName, vControl == 'button_nc' || vControl == 'switch_nc' ? !vActive : vActive);
    }

    vSimulator.step();

    if (vSimulator.cycle % drawEvery == 0 && mounted) {
      setState(() {});
    }
  }

  Widget buildDrawing(String pSvg) => SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: SvgPicture.string(pSvg),
      );

  Widget buildProgramDrawing() {
    try {
      final vRungs = parseProgram(editor.text, inputs);

      return vRungs.isEmpty
          ? const SizedBox.shrink()
          : buildDrawing(renderSvg(vRungs, timer == null ? null : simulator?.values));
    } on LadderError catch (vError) {
      return Text(vError.message, style: TextStyle(color: Theme.of(context).colorScheme.error));
    }
  }

  Widget buildControls() {
    final vSimulator = simulator!;
    final vTheme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(describeMachine(vSimulator), style: vTheme.textTheme.titleSmall),
        Wrap(
          spacing: 8,
          children: [
            for (final vVariable in level['variables'] as List)
              if ((vVariable as Map)['kind'] == 'output')
                Chip(
                  avatar: Icon(
                    Icons.circle,
                    size: 14,
                    color: vSimulator.values[vVariable['name']] == true
                        ? ((vVariable['name'] as String).contains('defaut')
                            ? Colors.red
                            : Colors.green)
                        : Colors.grey,
                  ),
                  label: Text(vVariable['name'] as String),
                ),
          ],
        ),
        Wrap(
          spacing: 8,
          children: [
            for (final vVariable in operatorInputs)
              if (vVariable['control'] == 'switch' || vVariable['control'] == 'switch_nc')
                FilterChip(
                  label: Text(
                    vVariable['control'] == 'switch_nc'
                        ? 'Déclencher ${vVariable['name']}'
                        : vVariable['name'] as String,
                  ),
                  selected: switched.contains(vVariable['name']),
                  onSelected: (pOn) => setState(
                    () => pOn
                        ? switched.add(vVariable['name'] as String)
                        : switched.remove(vVariable['name']),
                  ),
                )
              else
                Listener(
                  onPointerDown: (_) => setState(() => pressed.add(vVariable['name'] as String)),
                  onPointerUp: (_) => setState(() => pressed.remove(vVariable['name'])),
                  onPointerCancel: (_) => setState(() => pressed.remove(vVariable['name'])),
                  child: ActionChip(
                    label: Text(vVariable['name'] as String),
                    backgroundColor: pressed.contains(vVariable['name'])
                        ? vTheme.colorScheme.primaryContainer
                        : null,
                    onPressed: () {},
                  ),
                ),
          ],
        ),
      ],
    );
  }

  Widget buildResults() {
    final vRun = run!;
    final vTheme = Theme.of(context);

    if (vRun['error'] != null) {
      return Text(vRun['error'] as String, style: TextStyle(color: vTheme.colorScheme.error));
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          vRun['passed'] == true
              ? 'Niveau réussi${first ? ' · +${widget.state.ladderXp} XP au retour sur le PC' : ''}'
              : 'Pas encore : regardez les vérifications en rouge',
          style: vTheme.textTheme.titleMedium,
        ),
        for (final vCheck in vRun['checks'] as List)
          ListTile(
            dense: true,
            leading: Icon(
              (vCheck as Map)['passed'] == true ? Icons.check : Icons.close,
              color: vCheck['passed'] == true ? Colors.green : vTheme.colorScheme.error,
            ),
            title: Text('${vCheck['at']} s : ${vCheck['message']}'),
          ),
        for (final vMessage in vRun['violations'] as List)
          ListTile(
            dense: true,
            leading: Icon(Icons.warning_amber, color: vTheme.colorScheme.error),
            title: Text(vMessage as String),
          ),
        const Text('Chronogramme : entrées en bleu, sorties en vert'),
        buildDrawing(
          renderChronogram(
            List<String>.from(vRun['signals'] as List),
            List<Map<String, int>>.from(vRun['samples'] as List),
            inputs,
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext pContext) {
    final vTheme = Theme.of(pContext);

    return Scaffold(
      appBar: AppBar(title: Text(level['title'] as String)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(level['goal'] as String),
          const SizedBox(height: 8),
          for (final vVariable in level['variables'] as List)
            Text(
              '${(vVariable as Map)['name']} (${vVariable['kind'] == 'input' ? 'entrée' : 'sortie'}) : '
              '${vVariable['label']}',
              style: vTheme.textTheme.bodySmall,
            ),
          ExpansionTile(
            title: const Text('Indice'),
            tilePadding: EdgeInsets.zero,
            children: [Text(level['hint'] as String)],
          ),
          TextField(
            controller: editor,
            minLines: 5,
            maxLines: null,
            style: const TextStyle(fontFamily: 'monospace'),
            decoration: const InputDecoration(
              labelText: 'Programme, un barreau par ligne',
              border: OutlineInputBorder(),
            ),
            autocorrect: false,
            enableSuggestions: false,
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              FilledButton.icon(
                  onPressed: check, icon: const Icon(Icons.check), label: const Text('Vérifier')),
              OutlinedButton.icon(
                onPressed: toggleSimulation,
                icon: Icon(timer == null ? Icons.play_arrow : Icons.stop),
                label: Text(timer == null ? 'Simuler' : 'Arrêter'),
              ),
              TextButton(
                onPressed: () => setState(() => editor.text = level['solution'] as String),
                child: const Text('Voir la solution'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          buildProgramDrawing(),
          if (timer != null && simulator != null) buildControls(),
          if (run != null) buildResults(),
        ],
      ),
    );
  }
}
