// Bac à sable SQL, hors ligne : requêtes sur la base d'une usine, en MySQL ou en
// SQL Server, comparées au résultat attendu. Une requête réussie part au PC,
// qui la réexécute à la synchronisation.

import 'package:flutter/material.dart';

import '../logic/sql_levels.dart';
import '../logic/sql_sandbox.dart';
import '../revision_state.dart';

/// Choix du dialecte, enregistré sur le téléphone.
class DialectSelector extends StatelessWidget {
  const DialectSelector({super.key, required this.state});

  final RevisionState state;

  @override
  Widget build(BuildContext pContext) {
    final vDialects = Map<String, dynamic>.from(
      (state.sqlPackage['rules'] as Map?)?['dialects'] as Map? ?? const {'mysql': 'MySQL'},
    );

    return SegmentedButton<String>(
      segments: [
        for (final vEntry in vDialects.entries)
          ButtonSegment(value: vEntry.key, label: Text(vEntry.value as String)),
      ],
      selected: {state.sqlDialect},
      onSelectionChanged: (pSelection) => state.setSqlDialect(pSelection.first),
    );
  }
}

class SqlListScreen extends StatelessWidget {
  const SqlListScreen({super.key, required this.state});

  final RevisionState state;

  @override
  Widget build(BuildContext pContext) => Scaffold(
        appBar: AppBar(title: const Text('Bac à sable SQL')),
        body: ListenableBuilder(
          listenable: state,
          builder: (pContext, _) {
            final vSeries = <String, List<Map<String, dynamic>>>{};

            for (final vLevel in state.sqlLevelList) {
              vSeries.putIfAbsent(vLevel['series'] as String, () => []).add(vLevel);
            }

            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                DialectSelector(state: state),
                for (final vEntry in vSeries.entries) ...[
                  Padding(
                    padding: const EdgeInsets.only(top: 12, bottom: 4),
                    child: Text(vEntry.key, style: Theme.of(pContext).textTheme.titleMedium),
                  ),
                  for (final vLevel in vEntry.value)
                    Card(
                      child: ListTile(
                        leading: Icon(
                          state.sqlPassed.contains(vLevel['id']) ? Icons.check_circle : Icons.storage_outlined,
                        ),
                        title: Text(vLevel['title'] as String),
                        subtitle: Text(vLevel['goal'] as String, maxLines: 3, overflow: TextOverflow.ellipsis),
                        onTap: () => Navigator.of(pContext).push(
                          MaterialPageRoute<void>(builder: (_) => SqlScreen(state: state, level: vLevel)),
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

/// Résultat en tableau, défilant à l'horizontale.
class ResultTable extends StatelessWidget {
  const ResultTable({super.key, required this.columns, required this.rows});

  final List columns;
  final List rows;

  @override
  Widget build(BuildContext pContext) => SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          headingRowHeight: 36,
          dataRowMinHeight: 28,
          dataRowMaxHeight: 40,
          columns: [for (final vColumn in columns) DataColumn(label: Text('$vColumn'))],
          rows: [
            for (final vRow in rows)
              DataRow(cells: [for (final vValue in vRow as List) DataCell(Text(formatValue(vValue)))]),
          ],
        ),
      );
}

class SqlScreen extends StatefulWidget {
  const SqlScreen({super.key, required this.state, required this.level});

  final RevisionState state;
  final Map<String, dynamic> level;

  @override
  State<SqlScreen> createState() => _SqlScreenState();
}

class _SqlScreenState extends State<SqlScreen> {
  late final TextEditingController editor;
  Map<String, dynamic>? run;
  bool running = false;
  bool first = false;
  bool showHint = false;

  Map<String, dynamic> get level => widget.level;

  String get dialect => widget.state.sqlDialect;

  @override
  void initState() {
    super.initState();
    editor = TextEditingController(text: widget.state.sqlQuery(level));
  }

  @override
  void dispose() {
    editor.dispose();
    super.dispose();
  }

  Future<void> execute() async {
    final vLevels = widget.state.sqlLevels;

    if (vLevels == null || running) {
      return;
    }

    setState(() => running = true);

    final vQuery = editor.text;
    final vDialect = dialect;
    final vRun = await vLevels.runLevel(level, vQuery, vDialect);
    var vFirst = false;

    await widget.state.saveSqlQuery(level['id'] as String, vQuery);

    if (vRun['passed'] == true) {
      vFirst = await widget.state.recordSql(level['id'] as String, vQuery, vDialect);
    }

    if (mounted) {
      setState(() {
        run = vRun;
        first = vFirst;
        running = false;
      });
    }
  }

  Widget buildRun() {
    final vRun = run!;
    final vTheme = Theme.of(context);
    final vResult = vRun['result'] as Map<String, dynamic>;
    final vExpected = vRun['expected'] as Map<String, dynamic>;
    final vRows = (vResult['rows'] as List).length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (vRun['passed'] == true) ...[
          Text(
            'Niveau réussi${first ? ' · +${widget.state.sqlXp} XP au retour sur le PC' : ''}',
            style: vTheme.textTheme.titleMedium?.copyWith(color: Colors.green.shade700),
          ),
          Text(level['explanation'] as String? ?? ''),
        ] else ...[
          Text(vRun['message'] as String, style: TextStyle(color: vTheme.colorScheme.error)),
          for (final vAdvice in vRun['advice'] as List) Text('Conseil : $vAdvice'),
        ],
        const SizedBox(height: 8),
        Text(
          'Votre résultat · ${vResult['changed'] != null ? '${vResult['changed']} ligne(s) modifiée(s) · ' : ''}'
          '${vResult['truncated'] == true ? '200 premières lignes' : '$vRows ligne(s)'}',
          style: vTheme.textTheme.labelLarge,
        ),
        ResultTable(columns: vResult['columns'] as List, rows: vResult['rows'] as List),
        const SizedBox(height: 8),
        Text('Résultat attendu', style: vTheme.textTheme.labelLarge),
        ResultTable(columns: vExpected['columns'] as List, rows: vExpected['rows'] as List),
      ],
    );
  }

  @override
  Widget build(BuildContext pContext) {
    final vTheme = Theme.of(pContext);
    final vSolution = pick(level, 'solution', dialect) as String;

    return Scaffold(
      appBar: AppBar(title: Text(level['title'] as String)),
      body: ListenableBuilder(
        listenable: widget.state,
        builder: (pContext, _) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            DialectSelector(state: widget.state),
            const SizedBox(height: 8),
            Text(level['goal'] as String),
            ExpansionTile(
              title: const Text('Tables de la base'),
              tilePadding: EdgeInsets.zero,
              children: [
                for (final vTable in widget.state.sqlPackage['schema'] as List? ?? const [])
                  ListTile(
                    dense: true,
                    title: Text('${(vTable as Map)['name']} (${(vTable['columns'] as List).join(', ')})'),
                    subtitle: Text(vTable['label'] as String),
                  ),
              ],
            ),
            TextField(
              controller: editor,
              minLines: 4,
              maxLines: 12,
              style: const TextStyle(fontFamily: 'monospace', fontSize: 13),
              autocorrect: false,
              enableSuggestions: false,
              decoration: InputDecoration(
                labelText: 'Requête ${widget.state.sqlDialect == 'sqlserver' ? 'SQL Server' : 'MySQL'}',
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                FilledButton.icon(
                  onPressed: running ? null : execute,
                  icon: running
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.play_arrow),
                  label: const Text('Exécuter'),
                ),
                TextButton(onPressed: () => setState(() => showHint = true), child: const Text('Indice')),
                TextButton(onPressed: () => setState(() => editor.text = vSolution), child: const Text('Voir la solution')),
              ],
            ),
            if (showHint) Text('Indice : ${pick(level, 'hint', dialect)}', style: vTheme.textTheme.bodySmall),
            if (run != null) buildRun(),
          ],
        ),
      ),
    );
  }
}
