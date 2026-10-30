// Docker simulé, hors ligne : même hôte (images, conteneurs, volumes), mêmes
// messages et même curl que job/docker_sim.py. Le catalogue des images publiques
// vient du PC avec le contenu des niveaux.

import 'dart:convert';

import 'python_compat.dart';

const maxDockerfileLength = 4000;
const maxContainers = 20;
const instructions = [
  'FROM',
  'WORKDIR',
  'COPY',
  'ADD',
  'RUN',
  'ENV',
  'EXPOSE',
  'CMD',
  'ENTRYPOINT',
  'USER',
  'ARG',
  'LABEL'
];
const shellTools = ['sh', 'mkdir', 'echo', 'ls', 'cp', 'chmod', 'rm', 'cat', 'true'];

// Version du format de classe Java, affichée par UnsupportedClassVersionError
const classVersions = {17: 61, 21: 65};
final portPattern = RegExp(r'^(\d{1,5}):(\d{1,5})$');
final urlPattern = RegExp(
  r'^(?:https?://)?(?:localhost|127\.0\.0\.1):(\d{1,5})(/[\p{L}\p{N}\p{M}_/-]*)?$',
  unicode: true,
);

/// Erreur d'une commande Docker simulée, avec le message affiché.
class DockerError implements Exception {
  DockerError(this.message);

  final String message;

  @override
  String toString() => message;
}

String hex12(int pValue) => pValue.toRadixString(16).padLeft(12, '0');

String imageName(String pName) => pName.contains(':') ? pName : '$pName:latest';

String resolvePath(String pWorkdir, String pPath) => posixNormpath(posixJoin(pWorkdir, pPath));

/// Instructions du Dockerfile : (numéro de ligne, mot-clé, arguments).
List<(int, String, String)> joinLines(String pText) {
  final rInstructions = <(int, String, String)>[];
  var vBuffer = '';
  var vStart = 0;
  final vLines = splitLines(pText);

  for (var vNumber = 1; vNumber <= vLines.length; vNumber++) {
    final vStripped = pyStrip(vLines[vNumber - 1]);

    if (vBuffer.isEmpty && (vStripped.isEmpty || vStripped.startsWith('#'))) {
      continue;
    }

    if (vBuffer.isEmpty) {
      vStart = vNumber;
    }

    if (vStripped.endsWith(r'\')) {
      vBuffer += '${vStripped.substring(0, vStripped.length - 1)} ';
      continue;
    }

    vBuffer += vStripped;

    final (vKeyword, _, vArguments) = pyPartition(vBuffer, ' ');

    rInstructions.add((vStart, vKeyword.toUpperCase(), pyStrip(vArguments)));
    vBuffer = '';
  }

  if (vBuffer.isNotEmpty) {
    final (vKeyword, _, vArguments) = pyPartition(vBuffer, ' ');

    rInstructions.add((vStart, vKeyword.toUpperCase(), pyStrip(vArguments)));
  }

  return rInstructions;
}

/// Commande CMD ou ENTRYPOINT : forme JSON, sinon forme shell.
List<String> readCommand(String pArguments) {
  if (pArguments.startsWith('[')) {
    Object? vCommand;

    try {
      vCommand = jsonDecode(pArguments);
    } on FormatException {
      throw DockerError('forme JSON invalide : $pArguments (guillemets doubles obligatoires)');
    }

    if (vCommand is! List || vCommand.any((pWord) => pWord is! String)) {
      throw DockerError('forme JSON invalide : $pArguments');
    }

    return vCommand.cast<String>();
  }

  return ['/bin/sh', '-c', pArguments];
}

/// Simulateur Docker avec son catalogue d'images publiques.
class DockerSimulator {
  DockerSimulator(this.registry);

  /// Image publique : version de Java, outils présents, commande et port fournis.
  final Map<String, dynamic> registry;

  Map<String, dynamic> base(String pImage) => registry[pImage] as Map<String, dynamic>;

  List<String> toolsOf(String pImage) => (base(pImage)['tools'] as List).cast<String>();

  Map<String, dynamic> buildBase(String pImage) => {
        'base': pImage,
        'workdir': '/',
        'files': <String, dynamic>{},
        'env': <String, dynamic>{},
        'expose': <int>[],
        'cmd': List<String>.from(base(pImage)['cmd'] as List? ?? const []),
        'entrypoint': <String>[],
        'requirements': false,
      };

  /// Hôte vide, avec les conteneurs déjà présents du niveau.
  Map<String, dynamic> newHost([List pSetup = const []]) {
    final rHost = <String, dynamic>{
      'images': <String, dynamic>{},
      'containers': <Map<String, dynamic>>[],
      'volumes': <String, dynamic>{},
      'events': <Map<String, dynamic>>[],
      'sequence': 0,
    };

    for (final vItem in pSetup.cast<Map>()) {
      final vImage = vItem['image'] as String;

      (rHost['images'] as Map)[vImage] = buildBase(vImage);
      startContainer(
        rHost,
        createContainer(rHost, vImage, vItem['name'] as String?,
            vItem['ports'] as List? ?? const [], const [], const {}),
        null,
      );
    }

    return rHost;
  }

  void copyFiles(Map<String, dynamic> pSpec, List<String> pContext, String pArguments, int pLine) {
    final vWords = pySplit(pArguments);

    if (vWords.length < 2) {
      throw DockerError(
          'dockerfile parse error on line $pLine: COPY requires at least two arguments');
    }

    final vSources = vWords.sublist(0, vWords.length - 1);
    final vDestination = vWords.last;
    final vMatched = <(String, String)>[];

    for (final vRaw in vSources) {
      final vSource =
          vRaw == '.' || vRaw == './' ? '.' : (vRaw.startsWith('./') ? vRaw.substring(2) : vRaw);
      final List<(String, String)> vFiles;

      if (vSource == '.') {
        vFiles = [for (final vPath in pContext) (vPath, vPath)];
      } else {
        final vFolder = '${vSource.replaceFirst(RegExp(r'/+$'), '')}/';

        vFiles = [
          for (final vPath in pContext)
            if (fnmatchCase(vPath, vSource)) (vPath, posixBasename(vPath)),
          for (final vPath in pContext)
            if (vPath.startsWith(vFolder))
              (vPath, vPath.substring(vSource.length).replaceFirst(RegExp(r'^/+'), '')),
        ];
      }

      if (vFiles.isEmpty) {
        throw DockerError(
          'failed to compute cache key: "/$vSource": not found '
          "(ligne $pLine : ce fichier n'est pas dans le contexte de construction)",
        );
      }

      vMatched.addAll(vFiles);
    }

    final vTarget = resolvePath(pSpec['workdir'] as String, vDestination);
    final vIsFolder = vDestination.endsWith('/') ||
        vDestination == '.' ||
        vDestination == './' ||
        vMatched.length > 1 ||
        vSources.first == '.' ||
        vSources.first == './';

    for (final (vContextPath, vName) in vMatched) {
      (pSpec['files'] as Map)[vIsFolder ? posixJoin(vTarget, vName) : vTarget] = vContextPath;
    }
  }

  void runInstruction(
      Map<String, dynamic> pSpec, String pArguments, int pLine, List<String> pTools) {
    final vWords = pySplit(pArguments);
    final vTool = vWords.isEmpty ? '' : vWords.first;

    if (!pTools.contains(vTool) && !shellTools.contains(vTool)) {
      throw DockerError(
        'process "/bin/sh -c $pArguments" did not complete successfully: '
        'exit code: 127 (/bin/sh: 1: $vTool: not found, ligne $pLine)',
      );
    }

    if (vTool == 'pip' && vWords.contains('-r')) {
      final vIndex = vWords.indexOf('-r') + 1;
      final vName = vIndex < vWords.length ? vWords[vIndex] : '';
      final vFile = resolvePath(pSpec['workdir'] as String, vName);

      if (!(pSpec['files'] as Map).containsKey(vFile)) {
        throw DockerError(
          'process "/bin/sh -c $pArguments" did not complete successfully: '
          "exit code: 1 (ERROR: Could not open requirements file: No such file or directory: '$vName')",
        );
      }

      pSpec['requirements'] = true;
    }
  }

  /// Construit une image : (lignes, spécification).
  (List<String>, Map<String, dynamic>) buildImage(String pDockerfile, List<String> pContext) {
    if (pDockerfile.length > maxDockerfileLength) {
      throw DockerError('Dockerfile trop long : $maxDockerfileLength caractères au plus.');
    }

    final vInstructions = joinLines(pDockerfile);

    if (vInstructions.isEmpty || !['FROM', 'ARG'].contains(vInstructions.first.$2)) {
      throw DockerError(
          'dockerfile parse error : no build stage in current context (FROM manquant)');
    }

    Map<String, dynamic>? vSpec;
    var vTools = <String>[];
    final rLines = <String>[];

    for (var vIndex = 1; vIndex <= vInstructions.length; vIndex++) {
      final (vLine, vKeyword, vArguments) = vInstructions[vIndex - 1];

      if (!instructions.contains(vKeyword)) {
        throw DockerError('dockerfile parse error on line $vLine: unknown instruction: $vKeyword');
      }

      rLines.add(' => [$vIndex/${vInstructions.length}] $vKeyword $vArguments');

      if (vKeyword == 'FROM') {
        final vWords = pySplit(vArguments);
        final vImage = imageName(vWords.isEmpty ? '' : vWords.first);

        if (!registry.containsKey(vImage)) {
          throw DockerError(
            'failed to resolve source metadata for docker.io/library/$vImage: not found '
            '(images simulées : ${registry.keys.join(', ')})',
          );
        }

        vSpec = buildBase(vImage);
        vTools = toolsOf(vImage);
      } else if (vSpec == null) {
        continue;
      } else if (vKeyword == 'WORKDIR') {
        vSpec['workdir'] = resolvePath(vSpec['workdir'] as String, vArguments);
      } else if (vKeyword == 'COPY' || vKeyword == 'ADD') {
        copyFiles(vSpec, pContext, vArguments, vLine);
      } else if (vKeyword == 'RUN') {
        runInstruction(vSpec, vArguments, vLine, vTools);
      } else if (vKeyword == 'ENV') {
        var (vName, vSeparator, vValue) = pyPartition(vArguments, '=');

        if (vSeparator.isEmpty) {
          (vName, _, vValue) = pyPartition(vArguments, ' ');
        }

        (vSpec['env'] as Map)[pyStrip(vName)] = pyStrip(pyStrip(vValue), '"');
      } else if (vKeyword == 'EXPOSE') {
        vSpec['expose'] = [
          for (final vPort in pySplit(vArguments))
            if (RegExp(r'^\d+$').hasMatch(vPort.split('/').first))
              int.parse(vPort.split('/').first),
        ];
      } else if (vKeyword == 'CMD') {
        vSpec['cmd'] = readCommand(vArguments);
      } else if (vKeyword == 'ENTRYPOINT') {
        vSpec['entrypoint'] = readCommand(vArguments);
      }
    }

    if (vSpec == null) {
      throw DockerError(
          'dockerfile parse error : no build stage in current context (FROM manquant)');
    }

    return (rLines, vSpec);
  }

  List<Map<String, dynamic>> containersOf(Map<String, dynamic> pHost) =>
      (pHost['containers'] as List).cast<Map<String, dynamic>>();

  Map<String, dynamic> findContainer(Map<String, dynamic> pHost, String pName) {
    for (final vContainer in containersOf(pHost)) {
      if (pName.isNotEmpty &&
          (vContainer['name'] == pName || (vContainer['id'] as String).startsWith(pName))) {
        return vContainer;
      }
    }

    throw DockerError('Error response from daemon: No such container: $pName');
  }

  Map<String, dynamic> createContainer(
    Map<String, dynamic> pHost,
    String pImage,
    String? pName,
    List pPorts,
    List pVolumes,
    Map pEnv,
  ) {
    if (containersOf(pHost).length >= maxContainers) {
      throw DockerError('$maxContainers conteneurs au plus : supprimez-en avec docker rm.');
    }

    pHost['sequence'] = (pHost['sequence'] as int) + 1;

    final vSequence = pHost['sequence'] as int;
    final vName = pName == null || pName.isEmpty ? 'conteneur_$vSequence' : pName;

    if (containersOf(pHost).any((pContainer) => pContainer['name'] == vName)) {
      throw DockerError(
        'Error response from daemon: Conflict. The container name "/$vName" is already in use. '
        'You have to remove (or rename) that container to be able to reuse that name.',
      );
    }

    final rContainer = <String, dynamic>{
      'id': hex12(vSequence * 7919),
      'name': vName,
      'image': pImage,
      'ports': [for (final vPort in pPorts) List<Object>.from(vPort as List)],
      'volumes': [for (final vVolume in pVolumes) List<Object>.from(vVolume as List)],
      'env': Map<String, dynamic>.from(pEnv),
      'status': 'created',
      'logs': <String>[],
      'records': 0,
      'listen': null,
    };

    (pHost['containers'] as List).add(rContainer);

    for (final vVolume in pVolumes) {
      (pHost['volumes'] as Map).putIfAbsent(
          (vVolume as List).first, () => <String, dynamic>{'records': 0, 'writer': null});
    }

    return rContainer;
  }

  Map<int, String> usedPorts(Map<String, dynamic> pHost, [Map<String, dynamic>? pExcept]) => {
        for (final vContainer in containersOf(pHost))
          if (vContainer['status'] == 'running' && !identical(vContainer, pExcept))
            for (final vPort in vContainer['ports'] as List)
              (vPort as List).first as int: vContainer['name'] as String,
      };

  /// (en marche, journaux, port écouté) du processus du conteneur.
  (bool, List<String>, int?) startProcess(
      Map<String, dynamic> pImage, Map<String, dynamic> pContainer, Map pApp) {
    final vOwn = (pContainer['command'] as List?)?.cast<String>() ?? const <String>[];
    var vCommand = [
      ...(pImage['entrypoint'] as List).cast<String>(),
      ...(vOwn.isNotEmpty ? vOwn : (pImage['cmd'] as List).cast<String>()),
    ];
    final vEnv = {...pImage['env'] as Map, ...pContainer['env'] as Map};
    final vBase = base(pImage['base'] as String);
    final vTools = toolsOf(pImage['base'] as String);
    final vFiles = pImage['files'] as Map;

    if (vCommand.isEmpty) {
      return (false, ['docker: Error response from daemon: no command specified.'], null);
    }

    if (vCommand.length >= 2 && vCommand[0] == '/bin/sh' && vCommand[1] == '-c') {
      vCommand = vCommand.length > 2 ? pySplit(vCommand[2]) : [];
    }

    if (vCommand.isEmpty) {
      return (false, ['/bin/sh: commande vide'], null);
    }

    if (vCommand.first == 'nginx') {
      return (true, ['nginx: start worker processes'], 80);
    }

    if (vCommand.first == 'java') {
      if (!vTools.contains('java')) {
        return (false, ['/bin/sh: 1: java: not found'], null);
      }

      final vJarIndex = vCommand.sublist(0, vCommand.length - 1).indexOf('-jar');
      final vJar = vJarIndex < 0 ? '' : vCommand[vJarIndex + 1];

      if (vJar.isEmpty || !vFiles.containsKey(resolvePath(pImage['workdir'] as String, vJar))) {
        return (
          false,
          ['Error: Unable to access jarfile ${vJar.isEmpty ? '(aucun)' : vJar}'],
          null
        );
      }

      final vMinimum = (pApp['java_min'] as int?) ?? 0;

      if (vMinimum > (vBase['java'] as int)) {
        return (
          false,
          [
            'Error: LinkageError occurred while loading main class fr.atelier.Application',
            'java.lang.UnsupportedClassVersionError: compiled by a more recent version of the Java '
                'Runtime (class file version ${classVersions[vMinimum]}.0), this version of the Java '
                'Runtime only recognizes class file versions up to ${classVersions[vBase['java']]}.0',
          ],
          null,
        );
      }
    } else if (vCommand.first == 'python' || vCommand.first == 'python3') {
      if (!vTools.contains('python')) {
        return (false, ['/bin/sh: 1: ${vCommand.first}: not found'], null);
      }

      final vScript =
          resolvePath(pImage['workdir'] as String, vCommand.length > 1 ? vCommand[1] : '');

      if (!vFiles.containsKey(vScript)) {
        return (
          false,
          ["python: can't open file '$vScript': [Errno 2] No such file or directory"],
          null
        );
      }

      if (pApp['requirements'] == true && pImage['requirements'] != true) {
        return (
          false,
          [
            'Traceback (most recent call last):',
            '  File "$vScript", line 1, in <module>',
            "ModuleNotFoundError: No module named 'flask'",
          ],
          null,
        );
      }
    } else {
      return (false, [], null);
    }

    final vMissing = [
      for (final vName in (pApp['env_required'] as List? ?? const []).cast<String>())
        if ((vEnv[vName] as String? ?? '').isEmpty) vName,
    ];

    if (vMissing.isNotEmpty) {
      return (
        false,
        [
          'APPLICATION FAILED TO START',
          "Description: la variable d'environnement ${vMissing.first} est absente : "
              'impossible de joindre la base de données.',
        ],
        null,
      );
    }

    final vSetting = '${vEnv['SERVER_PORT'] ?? pApp['port']}';
    final vPort = RegExp(r'^\d+$').hasMatch(vSetting) ? int.parse(vSetting) : pApp['port'] as int;

    return (
      true,
      vCommand.first == 'java'
          ? ['Tomcat started on port $vPort (http)', 'Started Application in 2.1 seconds']
          : [' * Running on http://0.0.0.0:$vPort'],
      vPort,
    );
  }

  /// Démarre un conteneur : ports libres, puis processus.
  List<String> startContainer(
      Map<String, dynamic> pHost, Map<String, dynamic> pContainer, Map? pApp) {
    final vUsed = usedPorts(pHost, pContainer);

    for (final vPort in pContainer['ports'] as List) {
      final vHostPort = (vPort as List).first as int;

      if (vUsed.containsKey(vHostPort)) {
        throw DockerError(
          'Error response from daemon: driver failed programming external connectivity on endpoint '
          '${pContainer['name']}: Bind for 0.0.0.0:$vHostPort failed: port is already allocated '
          '(utilisé par ${vUsed[vHostPort]})',
        );
      }
    }

    final vImage = (pHost['images'] as Map)[pContainer['image']] as Map<String, dynamic>;
    final (vRunning, vLogs, vPort) = startProcess(vImage, pContainer, pApp ?? const {});

    (pContainer['logs'] as List).addAll(vLogs);
    pContainer['status'] = vRunning ? 'running' : 'exited (1)';
    pContainer['listen'] = vPort;

    return [pContainer['id'] as String];
  }

  Map<String, dynamic> parseRun(List<String> pWords) {
    final rOptions = <String, dynamic>{
      'name': null,
      'ports': <List<int>>[],
      'volumes': <List<String>>[],
      'env': <String, dynamic>{},
      'image': null,
      'command': <String>[],
    };
    var vIndex = 0;

    while (vIndex < pWords.length) {
      final vWord = pWords[vIndex];

      if (rOptions['image'] != null) {
        (rOptions['command'] as List).add(vWord);
      } else if (['-d', '--detach', '--rm', '-it', '-i', '-t'].contains(vWord)) {
        // Sans effet sur la simulation
      } else if (['--name', '-p', '--publish', '-v', '--volume', '-e', '--env'].contains(vWord)) {
        vIndex++;

        if (vIndex >= pWords.length) {
          throw DockerError('flag needs an argument: $vWord');
        }

        final vValue = pWords[vIndex];

        if (vWord == '--name') {
          rOptions['name'] = vValue;
        } else if (vWord == '-p' || vWord == '--publish') {
          final vMatch = portPattern.firstMatch(vValue);

          if (vMatch == null) {
            throw DockerError(
                'invalid argument "$vValue" for "-p" : écrivez -p PORT_HÔTE:PORT_CONTENEUR');
          }

          (rOptions['ports'] as List)
              .add([int.parse(vMatch.group(1)!), int.parse(vMatch.group(2)!)]);
        } else if (vWord == '-v' || vWord == '--volume') {
          final (vSource, vSeparator, vTarget) = pyPartition(vValue, ':');

          if (vSeparator.isEmpty || !vTarget.startsWith('/')) {
            throw DockerError(
                "invalid volume specification: '$vValue' : écrivez -v VOLUME:/chemin");
          }

          final vClean = vTarget.replaceFirst(RegExp(r'/+$'), '');

          (rOptions['volumes'] as List).add([vSource, vClean.isEmpty ? '/' : vClean]);
        } else {
          final (vName, _, vSetting) = pyPartition(vValue, '=');

          (rOptions['env'] as Map)[vName] = vSetting;
        }
      } else if (vWord.startsWith('-')) {
        throw DockerError('unknown flag: $vWord');
      } else {
        rOptions['image'] = vWord;
      }

      vIndex++;
    }

    if (rOptions['image'] == null) {
      throw DockerError('"docker run" requires at least 1 argument : l\'image à lancer.');
    }

    return rOptions;
  }

  String formatPorts(Map<String, dynamic> pContainer) => pContainer['status'] != 'running'
      ? ''
      : [
          for (final vPort in pContainer['ports'] as List)
            '0.0.0.0:${(vPort as List)[0]}->${vPort[1]}/tcp'
        ].join(', ');

  List<String> listContainers(Map<String, dynamic> pHost, bool pAll) => [
        '${'CONTAINER ID'.padRight(14)}${'IMAGE'.padRight(26)}${'STATUS'.padRight(14)}${'PORTS'.padRight(28)}NAMES',
        for (final vContainer in containersOf(pHost))
          if (pAll || vContainer['status'] == 'running')
            '${(vContainer['id'] as String).padRight(14)}${(vContainer['image'] as String).padRight(26)}'
                '${(vContainer['status'] as String).padRight(14)}${formatPorts(vContainer).padRight(28)}'
                '${vContainer['name']}',
      ];

  Map<String, dynamic> dataTarget(
      Map<String, dynamic> pHost, Map<String, dynamic> pContainer, Map pApp) {
    for (final vVolume in pContainer['volumes'] as List) {
      if ((vVolume as List)[1] == pApp['data_dir']) {
        return (pHost['volumes'] as Map)[vVolume[0]] as Map<String, dynamic>;
      }
    }

    return pContainer;
  }

  List<String> runCurl(Map<String, dynamic> pHost, List<String> pWords, Map pApp) {
    var vMethod = 'GET';
    String? vUrl;
    var vIndex = 0;

    while (vIndex < pWords.length) {
      if (pWords[vIndex] == '-X' && vIndex + 1 < pWords.length) {
        vMethod = pWords[vIndex + 1].toUpperCase();
        vIndex++;
      } else if (!pWords[vIndex].startsWith('-')) {
        vUrl = pWords[vIndex];
      }

      vIndex++;
    }

    final vMatch = urlPattern.firstMatch(vUrl ?? '');

    if (vMatch == null) {
      throw DockerError('curl : écrivez par exemple curl http://localhost:8080/');
    }

    final vPort = int.parse(vMatch.group(1)!);
    final vPath = vMatch.group(2) == null || vMatch.group(2)!.isEmpty ? '/' : vMatch.group(2)!;
    final vContainer = containersOf(pHost)
        .where(
          (pItem) =>
              pItem['status'] == 'running' &&
              (pItem['ports'] as List).any((pPort) => (pPort as List)[0] == vPort),
        )
        .firstOrNull;

    if (vContainer == null) {
      return ['curl: (7) Failed to connect to localhost port $vPort: Connection refused'];
    }

    final vInside =
        (vContainer['ports'] as List).firstWhere((pPort) => (pPort as List)[0] == vPort)[1];

    if (vInside != vContainer['listen']) {
      return ['curl: (56) Recv failure: Connection reset by peer'];
    }

    final vRunning = [
      for (final vItem in containersOf(pHost))
        if (vItem['status'] == 'running') vItem['name'] as String,
    ];
    final vEvents = pHost['events'] as List;

    if (vContainer['listen'] == 80 && (vContainer['image'] as String).startsWith('nginx')) {
      return ["<h1>Ancien site de l'atelier</h1>"];
    }

    if (vPath == '/mesures' &&
        pApp['data_dir'] != null &&
        (pApp['data_dir'] as String).isNotEmpty) {
      final vTarget = dataTarget(pHost, vContainer, pApp);

      if (vMethod == 'POST') {
        vTarget['records'] = (vTarget['records'] as int) + 1;
        vTarget['writer'] = vContainer['id'];

        return [
          pyJsonObject({'enregistrees': vTarget['records']})
        ];
      }

      vEvents.add({
        'kind': 'read',
        'records': vTarget['records'],
        'other': vTarget['writer'] != null && vTarget['writer'] != vContainer['id'],
        'running': vRunning,
      });

      return [
        pyJsonObject({'mesures': vTarget['records']})
      ];
    }

    vEvents
        .add({'kind': 'reach', 'port': vPort, 'image': vContainer['image'], 'running': vRunning});

    return [
      pyJsonObject({'application': pApp['name'] ?? 'atelier', 'statut': 'ok'})
    ];
  }

  /// Exécute une commande sur l'hôte, modifié sur place ; lève DockerError si elle est refusée.
  List<String> run(Map<String, dynamic> pHost, Map<String, dynamic> pLevel, String pDockerfile,
      String pCommand) {
    final List<String> vWords;

    try {
      vWords = splitCommand(pCommand);
    } on ShlexError catch (vError) {
      throw DockerError('commande illisible : ${vError.message}');
    }

    final vApp = pLevel['app'] as Map? ?? const {};

    if (vWords.isNotEmpty && vWords.first == 'curl') {
      return runCurl(pHost, vWords.sublist(1), vApp);
    }

    if (vWords.isEmpty || vWords.first != 'docker' || vWords.length < 2) {
      throw DockerError('Commandes simulées : docker … et curl http://localhost:PORT/');
    }

    final vVerb = vWords[1];
    final vRest = vWords.sublist(2);
    final vImages = pHost['images'] as Map;

    if (vVerb == 'build') {
      String? vTag;

      for (var vIndex = 0; vIndex < vRest.length; vIndex++) {
        if ((vRest[vIndex] == '-t' || vRest[vIndex] == '--tag') && vIndex + 1 < vRest.length) {
          vTag = imageName(vRest[vIndex + 1]);
        }
      }

      if (vRest.isEmpty || !['.', './'].contains(vRest.last)) {
        throw DockerError(
            '"docker build" requires exactly 1 argument : le contexte, souvent « . »');
      }

      final (vLines, vSpec) =
          buildImage(pDockerfile, (pLevel['context'] as List? ?? const []).cast<String>());
      final vName = vTag ?? '<none>:<none>';

      vImages[vName] = vSpec;
      (pHost['events'] as List).add({'kind': 'build', 'image': vName});

      return [
        ...vLines,
        ' => naming to docker.io/library/$vName',
        ' => DONE',
        if (vTag == null) "Astuce : sans -t, l'image n'a pas de nom pour docker run.",
      ];
    }

    if (vVerb == 'images') {
      final vNames = vImages.keys.cast<String>().toList();

      return [
        '${'REPOSITORY'.padRight(24)}${'TAG'.padRight(12)}IMAGE ID',
        for (var vIndex = 0; vIndex < vNames.length; vIndex++)
          '${vNames[vIndex].split(':')[0].padRight(24)}${vNames[vIndex].split(':')[1].padRight(12)}'
              '${hex12((vIndex + 1) * 48271)}',
      ];
    }

    if (vVerb == 'pull') {
      final vName = vRest.isEmpty ? '' : imageName(vRest.first);

      if (!registry.containsKey(vName)) {
        throw DockerError(
            'pull access denied for ${vName.isEmpty ? '(rien)' : vName}, repository does not exist');
      }

      vImages[vName] = buildBase(vName);

      return ['Status: Downloaded newer image for $vName'];
    }

    if (vVerb == 'run') {
      final vOptions = parseRun(vRest);
      final vImage = imageName(vOptions['image'] as String);

      if (!vImages.containsKey(vImage)) {
        if (!registry.containsKey(vImage)) {
          throw DockerError(
            "Unable to find image '$vImage' locally : construisez-la avec docker build -t NOM . ou vérifiez son nom",
          );
        }

        vImages[vImage] = buildBase(vImage);
      }

      final vContainer = createContainer(
        pHost,
        vImage,
        vOptions['name'] as String?,
        vOptions['ports'] as List,
        vOptions['volumes'] as List,
        vOptions['env'] as Map,
      );

      vContainer['command'] = vOptions['command'];

      return startContainer(pHost, vContainer, vApp);
    }

    if (vVerb == 'ps') {
      return listContainers(pHost, vRest.contains('-a') || vRest.contains('--all'));
    }

    if (vVerb == 'logs') {
      final vLogs =
          (findContainer(pHost, vRest.isEmpty ? '' : vRest.last)['logs'] as List).cast<String>();

      return vLogs.isEmpty ? ['(aucun journal)'] : List.of(vLogs);
    }

    if (['stop', 'start', 'restart', 'rm'].contains(vVerb)) {
      final vForce = vRest.contains('-f') || vRest.contains('--force');
      final vNames = [
        for (final vWord in vRest)
          if (!vWord.startsWith('-')) vWord
      ];

      if (vNames.isEmpty) {
        throw DockerError('"docker $vVerb" requires at least 1 argument');
      }

      final rLines = <String>[];

      for (final vName in vNames) {
        final vContainer = findContainer(pHost, vName);

        if (vVerb == 'rm') {
          if (vContainer['status'] == 'running' && !vForce) {
            throw DockerError(
              'Error response from daemon: You cannot remove a running container ${vContainer['id']}. '
              'Stop the container before attempting removal or force remove (docker rm -f)',
            );
          }

          (pHost['containers'] as List).remove(vContainer);
        } else if (vVerb == 'stop') {
          vContainer['status'] = 'exited (143)';
        } else {
          vContainer['status'] = 'exited (0)';
          startContainer(pHost, vContainer, vApp);
        }

        rLines.add(vName);
      }

      return rLines;
    }

    if (vVerb == 'volume') {
      if (vRest.isNotEmpty && vRest.first == 'ls') {
        return [
          'DRIVER    VOLUME NAME',
          for (final vName in (pHost['volumes'] as Map).keys) 'local     $vName'
        ];
      }

      if (vRest.length == 2 && vRest.first == 'create') {
        (pHost['volumes'] as Map)
            .putIfAbsent(vRest[1], () => <String, dynamic>{'records': 0, 'writer': null});

        return [vRest[1]];
      }

      throw DockerError(
          'Commandes de volume simulées : docker volume ls, docker volume create NOM');
    }

    throw DockerError(
      "docker: '$vVerb' n'est pas simulée. Commandes : build, images, pull, run, ps, logs, stop, start, "
      'restart, rm, volume ; et curl.',
    );
  }
}

/// Indique si l'objectif du niveau est atteint d'après les événements notés.
bool isDockerGoalReached(Map<String, dynamic> pHost, Map pGoal) {
  for (final vEvent in (pHost['events'] as List).cast<Map>()) {
    if (pGoal['type'] == 'persist' && vEvent['kind'] == 'read') {
      if ((vEvent['records'] as int) > 0 && vEvent['other'] == true) {
        return true;
      }
    } else if (pGoal['type'] == 'reach' && vEvent['kind'] == 'reach') {
      if (vEvent['port'] == (pGoal['port'] ?? vEvent['port']) &&
          vEvent['image'] == (pGoal['image'] ?? vEvent['image']) &&
          (pGoal['keep'] as List? ?? const [])
              .every((pName) => (vEvent['running'] as List).contains(pName)) &&
          !(vEvent['image'] as String).startsWith('nginx')) {
        return true;
      }
    }
  }

  return false;
}
