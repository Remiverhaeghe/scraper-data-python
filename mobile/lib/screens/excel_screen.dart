// Atelier Excel, hors ligne : formules en français sur les tableaux d'une usine,
// recopiées sur la plage du niveau et comparées au résultat attendu. Une formule
// réussie part au PC, qui la recalcule à la synchronisation.

import 'package:flutter/material.dart';

import '../revision_state.dart';

class ExcelListScreen extends StatelessWidget {
  const ExcelListScreen({super.key, required this.state});

  final RevisionState state;

  @override
  Widget build(BuildContext pContext) => Scaffold(
        appBar: AppBar(title: const Text('Atelier Excel')),
        body: ListenableBuilder(
          listenable: state,
          builder: (pContext, _) {
            final vSeries = <String, List<Map<String, dynamic>>>{};

            for (final vLevel in state.excelLevelList) {
              vSeries.putIfAbsent(vLevel['series'] as String, () => []).add(vLevel);
            }

            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text(
                  "Noms de fonctions et point-virgule d'Excel en français : =SOMME(B2:B6), "
                  '=SI(B2>0;"oui";"non").',
                  style: Theme.of(pContext).textTheme.bodySmall,
                ),
                for (final vEntry in vSeries.entries) ...[
                  Padding(
                    padding: const EdgeInsets.only(top: 12, bottom: 4),
                    child: Text(vEntry.key, style: Theme.of(pContext).textTheme.titleMedium),
                  ),
                  for (final vLevel in vEntry.value)
                    Card(
                      child: ListTile(
                        leading: Icon(
                          state.excelPassed.contains(vLevel['id'])
                              ? Icons.check_circle
                              : Icons.table_chart_outlined,
                        ),
                        title: Text(vLevel['title'] as String),
                        subtitle: Text(vLevel['goal'] as String,
                            maxLines: 3, overflow: TextOverflow.ellipsis),
                        onTap: () => Navigator.of(pContext).push(
                          MaterialPageRoute<void>(
                              builder: (_) => ExcelScreen(state: state, level: vLevel)),
                        ),
                      ),
                    ),
                ],
              ],
            );
          },
        ),
      );
}

/// Feuille du niveau, défilant à l'horizontale : cibles surlignées, vertes ou rouges.
class SheetTable extends StatelessWidget {
  const SheetTable({super.key, required this.grid, required this.states});

  final Map<String, dynamic> grid;
  final Map<String, bool> states;

  @override
  Widget build(BuildContext pContext) {
    final vScheme = Theme.of(pContext).colorScheme;
    final vColumns = grid['columns'] as List;
    final vRows = grid['rows'] as List;
    final vTargets = {for (final vName in grid['targets'] as List) vName as String};

    Color? background(String pName) {
      if (!vTargets.contains(pName)) {
        return null;
      }

      return switch (states[pName]) {
        true => Colors.green.withValues(alpha: 0.18),
        false => vScheme.errorContainer,
        _ => vScheme.primaryContainer,
      };
    }

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        headingRowHeight: 32,
        dataRowMinHeight: 28,
        dataRowMaxHeight: 36,
        columnSpacing: 16,
        horizontalMargin: 8,
        columns: [
          const DataColumn(label: Text('')),
          for (final vColumn in vColumns) DataColumn(label: Text('$vColumn')),
        ],
        rows: [
          for (var vRow = 0; vRow < vRows.length; vRow++)
            DataRow(
              cells: [
                DataCell(Text('${vRow + 1}', style: TextStyle(color: vScheme.outline))),
                for (var vColumn = 0; vColumn < vColumns.length; vColumn++)
                  DataCell(
                    Container(
                      color: background('${vColumns[vColumn]}${vRow + 1}'),
                      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                      child: Text(
                        '${(vRows[vRow] as List)[vColumn]}',
                        style: vRow == 0 ? const TextStyle(fontWeight: FontWeight.w600) : null,
                      ),
                    ),
                  ),
              ],
            ),
        ],
      ),
    );
  }
}

class ExcelScreen extends StatefulWidget {
  const ExcelScreen({super.key, required this.state, required this.level});

  final RevisionState state;
  final Map<String, dynamic> level;

  @override
  State<ExcelScreen> createState() => _ExcelScreenState();
}

class _ExcelScreenState extends State<ExcelScreen> {
  late final TextEditingController editor;
  late Map<String, dynamic> run;
  bool tried = false;
  bool first = false;
  bool showHint = false;

  Map<String, dynamic> get level => widget.level;

  @override
  void initState() {
    super.initState();
    editor = TextEditingController(text: widget.state.excelFormula(level));
    run = widget.state.excelLevels!.runLevel(level, '');
  }

  @override
  void dispose() {
    editor.dispose();
    super.dispose();
  }

  Future<void> validate() async {
    final vFormula = editor.text.trim();
    final vRun = widget.state.excelLevels!.runLevel(level, vFormula);
    var vFirst = false;

    await widget.state.saveExcelFormula(level['id'] as String, vFormula);

    if (vRun['passed'] == true) {
      vFirst = await widget.state.recordExcel(level['id'] as String, vFormula);
    }

    if (mounted) {
      setState(() {
        run = vRun;
        tried = true;
        first = vFirst;
      });
    }
  }

  Widget buildVerdict() {
    final vTheme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (run['passed'] == true) ...[
          Text(
            'Niveau réussi${first ? ' · +${widget.state.excelXp} XP au retour sur le PC' : ''}',
            style: vTheme.textTheme.titleMedium?.copyWith(color: Colors.green.shade700),
          ),
          Text(level['explanation'] as String? ?? ''),
        ] else ...[
          Text(run['message'] as String, style: TextStyle(color: vTheme.colorScheme.error)),
          for (final vAdvice in run['advice'] as List) Text('Conseil : $vAdvice'),
        ],
        for (final vCell in run['cells'] as List)
          Text(
            '${(vCell as Map)['cell']} : ${vCell['value']}'
            '${vCell['ok'] == true ? '' : ' (attendu ${vCell['expected']})'}',
            style: TextStyle(
              color: vCell['ok'] == true ? Colors.green.shade700 : vTheme.colorScheme.error,
            ),
          ),
      ],
    );
  }

  @override
  Widget build(BuildContext pContext) {
    final vTheme = Theme.of(pContext);
    final vStates = {
      for (final vCell in run['cells'] as List)
        (vCell as Map)['cell'] as String: vCell['ok'] == true,
    };

    return Scaffold(
      appBar: AppBar(title: Text(level['title'] as String)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(level['goal'] as String),
          const SizedBox(height: 8),
          SheetTable(grid: run['grid'] as Map<String, dynamic>, states: vStates),
          const SizedBox(height: 8),
          TextField(
            controller: editor,
            maxLength: widget.state.excelLevels!.rules.maxFormulaLength,
            style: const TextStyle(fontFamily: 'monospace', fontSize: 14),
            autocorrect: false,
            enableSuggestions: false,
            textInputAction: TextInputAction.done,
            onSubmitted: (_) => validate(),
            decoration: InputDecoration(
              labelText: 'Formule de ${level['cell']}',
              prefixText: 'fx  ',
              border: const OutlineInputBorder(),
            ),
          ),
          Wrap(
            spacing: 8,
            children: [
              FilledButton.icon(
                onPressed: validate,
                icon: const Icon(Icons.check),
                label: const Text('Valider'),
              ),
              TextButton(
                  onPressed: () => setState(() => showHint = true), child: const Text('Indice')),
              TextButton(
                  onPressed: () => setState(() => editor.text = level['solution'] as String),
                  child: const Text('Voir la solution')),
            ],
          ),
          if (showHint) Text('Indice : ${level['hint']}', style: vTheme.textTheme.bodySmall),
          if (tried) buildVerdict(),
        ],
      ),
    );
  }
}
