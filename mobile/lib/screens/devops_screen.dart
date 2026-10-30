// Maven et Docker, hors ligne : corriger un pom.xml ou un Dockerfile et lancer
// les commandes dans une console simulée. Un niveau réussi part au PC, qui
// rejoue les étapes à la synchronisation.

import 'package:flutter/material.dart';

import '../logic/devops.dart';
import '../revision_state.dart';

const maxConsoleLines = 300;

/// Débuts de commande proposés sous le champ, selon l'outil.
const quickCommands = {
  'maven': ['mvn compile', 'mvn test', 'mvn package', 'mvn clean package', 'mvn dependency:tree'],
  'docker': [
    'docker build -t ',
    'docker run -d --name ',
    'docker ps -a',
    'docker logs ',
    'docker rm -f ',
    'curl http://localhost:',
  ],
};

class DevopsListScreen extends StatelessWidget {
  const DevopsListScreen({super.key, required this.state});

  final RevisionState state;

  @override
  Widget build(BuildContext pContext) => Scaffold(
        appBar: AppBar(title: const Text('Maven et Docker')),
        body: ListenableBuilder(
          listenable: state,
          builder: (pContext, _) {
            final vSeries = <String, List<Map<String, dynamic>>>{};

            for (final vLevel in state.devopsLevels) {
              vSeries.putIfAbsent(vLevel['series'] as String, () => []).add(vLevel);
            }

            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                for (final vEntry in vSeries.entries) ...[
                  Padding(
                    padding: const EdgeInsets.only(top: 12, bottom: 4),
                    child: Text(vEntry.key, style: Theme.of(pContext).textTheme.titleMedium),
                  ),
                  for (final vLevel in vEntry.value)
                    Card(
                      child: ListTile(
                        leading: Icon(
                          state.devopsPassed.contains(vLevel['id'])
                              ? Icons.check_circle
                              : (vLevel['tool'] == 'maven' ? Icons.code : Icons.dns_outlined),
                        ),
                        title: Text(vLevel['title'] as String),
                        subtitle: Text(vLevel['goal'] as String,
                            maxLines: 3, overflow: TextOverflow.ellipsis),
                        onTap: () => Navigator.of(pContext).push(
                          MaterialPageRoute<void>(
                              builder: (_) => DevopsScreen(state: state, level: vLevel)),
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

class DevopsScreen extends StatefulWidget {
  const DevopsScreen({super.key, required this.state, required this.level});

  final RevisionState state;
  final Map<String, dynamic> level;

  @override
  State<DevopsScreen> createState() => _DevopsScreenState();
}

class _DevopsScreenState extends State<DevopsScreen> {
  late final DevopsLab lab = widget.state.devopsLab;
  late final TextEditingController file;
  final command = TextEditingController();
  late Map<String, dynamic> host;
  List<String> console = [];
  List<Map<String, dynamic>> steps = [];
  String message = '';
  bool reached = false;
  bool showHint = false;
  bool showSolution = false;

  Map<String, dynamic> get level => widget.level;

  String get levelId => level['id'] as String;

  @override
  void initState() {
    super.initState();

    final vSession = widget.state.devopsSession(levelId);

    file = TextEditingController(text: vSession?['file'] as String? ?? level['file'] as String);
    host = (vSession?['host'] as Map?)?.cast<String, dynamic>() ?? lab.newHost(level);
    console = List<String>.from(vSession?['console'] as List? ?? const []);
    steps = [
      for (final vStep in vSession?['steps'] as List? ?? const [])
        Map<String, dynamic>.from(vStep as Map),
    ];
  }

  @override
  void dispose() {
    file.dispose();
    command.dispose();
    super.dispose();
  }

  Future<void> save() => widget.state.saveDevopsSession(levelId, {
        'file': file.text,
        'host': host,
        'console': console,
        'steps': steps,
      });

  Future<void> run() async {
    final vCommand = cleanCommand(command.text);

    if (vCommand.isEmpty) {
      setState(() => message = 'Saisissez une commande.');
      return;
    }

    final vFile = file.text.length > maxDevopsFileLength
        ? file.text.substring(0, maxDevopsFileLength)
        : file.text;
    final (vLines, vReached, vMessage) = lab.playStep(level, vFile, vCommand, host);
    var vText = vMessage;

    steps = [
      ...steps,
      {'file': vFile, 'command': vCommand}
    ].take(maxDevopsSteps).toList();
    console = [...console, '\$ $vCommand', ...vLines];

    if (console.length > maxConsoleLines) {
      console = console.sublist(console.length - maxConsoleLines);
    }

    if (vReached && !reached) {
      final vFirst = await widget.state.recordDevops(levelId, steps);

      vText =
          'Objectif atteint${vFirst ? ' · +${widget.state.devopsXp} XP au retour sur le PC' : ''}. '
          '${level['explanation']}';
    }

    setState(() {
      reached = reached || vReached;
      message = vText;
      command.clear();
    });
    await save();
  }

  Future<void> restart() async {
    setState(() {
      file.text = level['file'] as String;
      host = lab.newHost(level);
      console = [];
      steps = [];
      message = '';
      reached = false;
    });
    await widget.state.saveDevopsSession(levelId, null);
  }

  @override
  Widget build(BuildContext pContext) {
    final vTheme = Theme.of(pContext);
    const vMono = TextStyle(fontFamily: 'monospace', fontSize: 12);

    return Scaffold(
      appBar: AppBar(title: Text(level['title'] as String)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(level['goal'] as String),
          const SizedBox(height: 8),
          TextField(
            controller: file,
            minLines: 6,
            maxLines: 16,
            style: vMono,
            autocorrect: false,
            enableSuggestions: false,
            decoration: InputDecoration(
              labelText: fileNames[level['tool']],
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: command,
            style: vMono,
            autocorrect: false,
            enableSuggestions: false,
            decoration: InputDecoration(
              labelText: 'Commande',
              border: const OutlineInputBorder(),
              suffixIcon:
                  IconButton(icon: const Icon(Icons.send), tooltip: 'Exécuter', onPressed: run),
            ),
            onSubmitted: (_) => run(),
          ),
          Wrap(
            spacing: 6,
            children: [
              for (final vQuick in quickCommands[level['tool']] ?? const <String>[])
                ActionChip(
                  label: Text(vQuick.trim()),
                  onPressed: () => setState(() {
                    command.text = vQuick;
                    command.selection = TextSelection.collapsed(offset: vQuick.length);
                  }),
                ),
            ],
          ),
          if (message.isNotEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Text(
                message,
                style: TextStyle(color: reached ? Colors.green.shade700 : Colors.orange.shade800),
              ),
            ),
          if (console.isNotEmpty)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                  color: const Color(0xFF0F172A), borderRadius: BorderRadius.circular(8)),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: SelectableText(
                  console.join('\n'),
                  style: vMono.copyWith(color: const Color(0xFFE2E8F0)),
                ),
              ),
            ),
          Wrap(
            spacing: 8,
            children: [
              TextButton(onPressed: restart, child: const Text('Recommencer')),
              TextButton(
                  onPressed: () => setState(() => showHint = true), child: const Text('Indice')),
              TextButton(
                onPressed: () => setState(() {
                  showSolution = true;
                  file.text = level['solution'] as String;
                }),
                child: const Text('Solution'),
              ),
            ],
          ),
          if (showHint) Text('Indice : ${level['hint']}', style: vTheme.textTheme.bodySmall),
          if (showSolution)
            Text(
              'Commandes de la solution : ${(level['commands'] as List).join(' · ')}',
              style: vTheme.textTheme.bodySmall,
            ),
        ],
      ),
    );
  }
}
