// Maven simulé, hors ligne : même lecture du pom.xml, même résolution des
// dépendances et mêmes messages que job/maven_sim.py. Le dépôt central réduit
// vient du PC avec le contenu des niveaux.

import 'pom_xml.dart';
import 'python_compat.dart';

const maxPomLength = 8000;
final separator = '[INFO] ${'-' * 72}';
const scopes = ['compile', 'provided', 'runtime', 'test', 'system'];
const phases = ['validate', 'compile', 'test', 'package', 'verify', 'install'];
const defaultRelease = 8;
const defaultSurefire = '3.2.5';

// Version de surefire à partir de laquelle les tests JUnit 5 sont trouvés
const surefireJunit5 = [2, 22];

// Version minimale de Java de chaque nouveauté du langage
const features = {
  'var': (10, "'var' is not allowed here"),
  'switch_expression': (14, 'switch expressions are not supported'),
  'text_block': (15, 'text blocks are not supported'),
  'record': (16, 'records are not supported'),
};

/// Erreur de lecture ou de validation du pom.xml, avec les lignes Maven.
class PomError implements Exception {
  PomError(this.lines);

  final List<String> lines;
}

/// Version comparable : [2, 17, 0].
List<int> parseVersion(String? pText) => RegExp(r'\d+')
    .allMatches(pText ?? '')
    .take(3)
    .map((pMatch) => int.parse(pMatch.group(0)!))
    .toList();

/// Compare deux versions comme des tuples Python.
int compareVersions(List<int> pFirst, List<int> pSecond) {
  for (var vIndex = 0; vIndex < pFirst.length && vIndex < pSecond.length; vIndex++) {
    if (pFirst[vIndex] != pSecond[vIndex]) {
      return pFirst[vIndex].compareTo(pSecond[vIndex]);
    }
  }

  return pFirst.length.compareTo(pSecond.length);
}

final _propertyPattern = RegExp(r'\$\{([\p{L}\p{N}\p{M}_.-]+)\}', unicode: true);

String readText(XmlElement pElement, String pPath, [Map<String, String>? pProperties]) {
  final vChild = pElement.find(pPath);
  final vText = vChild == null ? '' : pyStrip(vChild.text);

  return vText.replaceAllMapped(
    _propertyPattern,
    (pMatch) => (pProperties ?? const {})[pMatch.group(1)] ?? pMatch.group(0)!,
  );
}

/// Modèle du pom.xml ; lève PomError comme Maven le signalerait.
Map<String, dynamic> parsePom(String pText) {
  if (pText.length > maxPomLength) {
    throw PomError(['[ERROR] pom.xml trop long : $maxPomLength caractères au plus.']);
  }

  final XmlElement vRoot;

  try {
    vRoot = parseXml(pText);
  } on XmlError catch (vError) {
    throw PomError(['[ERROR] Non-parseable POM pom.xml: ${vError.message}']);
  }

  if (vRoot.tag != 'project') {
    throw PomError(['[ERROR] Non-parseable POM pom.xml: la racine doit être <project>']);
  }

  final vProperties = <String, String>{};

  for (final vChild in vRoot.find('properties')?.children ?? const <XmlElement>[]) {
    vProperties[vChild.tag] = pyStrip(vChild.text);
  }

  final rModel = <String, dynamic>{
    for (final vKey in ['modelVersion', 'groupId', 'artifactId', 'version', 'packaging'])
      vKey: readText(vRoot, vKey, vProperties),
  };

  if ((rModel['packaging'] as String).isEmpty) {
    rModel['packaging'] = 'jar';
  }

  final vErrors = [
    for (final vKey in ['modelVersion', 'groupId', 'artifactId', 'version'])
      if ((rModel[vKey] as String).isEmpty) "[ERROR]     '$vKey' is missing. @ line 1",
  ];
  final vDependencies = <Map<String, String>>[];

  rModel['properties'] = vProperties;

  for (final vDependency in vRoot.findAll('dependencies/dependency')) {
    final vItem = {
      for (final vKey in ['groupId', 'artifactId', 'version', 'scope'])
        vKey: readText(vDependency, vKey, vProperties),
    };
    final vKey = '${vItem['groupId']}:${vItem['artifactId']}';

    vItem['key'] = vKey;

    if (vItem['scope']!.isEmpty) {
      vItem['scope'] = 'compile';
    }

    if (vItem['version']!.isEmpty) {
      vErrors.add("[ERROR]     'dependencies.dependency.version' for $vKey:jar is missing.");
    }

    if (!scopes.contains(vItem['scope'])) {
      vErrors.add(
        "[ERROR]     'dependencies.dependency.scope' for $vKey:jar must be one of "
        "[${scopes.join(', ')}] but is '${vItem['scope']}'.",
      );
    }

    vDependencies.add(vItem);
  }

  rModel['dependencies'] = vDependencies;
  rModel['plugins'] = <String, Map<String, String>>{
    for (final vPlugin in vRoot.findAll('build/plugins/plugin'))
      '${readText(vPlugin, 'groupId').isEmpty ? 'org.apache.maven.plugins' : readText(vPlugin, 'groupId')}:'
          '${readText(vPlugin, 'artifactId')}': {
        'version': readText(vPlugin, 'version', vProperties),
        'release': readText(vPlugin, 'configuration/release', vProperties),
      },
  };

  if (vErrors.isNotEmpty) {
    throw PomError([
      '[ERROR] [ERROR] Some problems were encountered while processing the POMs:',
      ...vErrors,
      '[ERROR] The build could not read 1 project -> [Help 1]',
    ]);
  }

  return rModel;
}

/// Version de Java visée par le compilateur.
int getRelease(Map<String, dynamic> pModel) {
  final vCompiler = (pModel['plugins']
      as Map<String, Map<String, String>>)['org.apache.maven.plugins:maven-compiler-plugin'];
  final vProperties = pModel['properties'] as Map<String, String>;
  final vText = [
    vCompiler?['release'],
    vProperties['maven.compiler.release'],
    vProperties['maven.compiler.source'],
  ].firstWhere((pValue) => pValue != null && pValue.isNotEmpty, orElse: () => null);
  final vVersion = parseVersion(vText);

  if (vVersion.isEmpty) {
    return defaultRelease;
  }

  return vVersion[0] == 1 && vVersion.length > 1 ? vVersion[1] : vVersion[0];
}

/// Simulateur Maven avec son dépôt central réduit.
class MavenSimulator {
  MavenSimulator(this.central);

  /// Artefact « groupe:nom » : versions, paquets, dépendances, versions minimales attendues.
  final Map<String, dynamic> central;

  Map<String, dynamic> entry(String pKey) => central[pKey] as Map<String, dynamic>;

  /// Dépendances résolues : clé → [version, scope, parent ou null, versions écartées].
  Map<String, List<Object?>> resolve(Map<String, dynamic> pModel) {
    final rResolved = <String, List<Object?>>{};
    final vMissing = <String>[];

    for (final vItem in pModel['dependencies'] as List<Map<String, String>>) {
      final vEntry = central[vItem['key']] as Map<String, dynamic>?;

      if (vEntry == null || !(vEntry['versions'] as List).contains(vItem['version'])) {
        vMissing.add('${vItem['key']}:jar:${vItem['version']}');
        continue;
      }

      rResolved[vItem['key']!] = [vItem['version'], vItem['scope'], null, <List<String>>[]];
    }

    if (vMissing.isNotEmpty) {
      throw PomError([
        '[ERROR] Failed to execute goal on project ${pModel['artifactId']}: Could not resolve dependencies',
        for (final vName in vMissing)
          '[ERROR]   Could not find artifact $vName in central (https://repo.maven.apache.org/maven2)',
      ]);
    }

    for (final vEntry in rResolved.entries.toList()) {
      final vScope = vEntry.value[1] as String;

      if (vScope == 'provided') {
        continue;
      }

      for (final vChild in entry(vEntry.key)['dependencies'] as List? ?? const []) {
        final vChildKey = (vChild as List)[0] as String;
        final vChildVersion = vChild[1] as String;

        if (rResolved.containsKey(vChildKey)) {
          if (rResolved[vChildKey]![0] != vChildVersion) {
            (rResolved[vChildKey]![3] as List<List<String>>).add([vEntry.key, vChildVersion]);
          }

          continue;
        }

        rResolved[vChildKey] = [vChildVersion, vScope, vEntry.key, <List<String>>[]];
      }
    }

    return rResolved;
  }

  Set<String> packagesOf(Map<String, List<Object?>> pResolved, List<String> pScopes) => {
        for (final vEntry in pResolved.entries)
          if (pScopes.contains(vEntry.value[1]))
            for (final vPackage in entry(vEntry.key)['packages'] as List) vPackage as String,
      };

  /// Erreurs de compilation de fichiers sources, au format javac.
  List<String> checkImports(List pFiles, Set<String> pPackages, int pRelease) {
    final rErrors = <String>[];

    for (final vFile in pFiles.cast<Map<String, dynamic>>()) {
      final vImports = (vFile['imports'] as List? ?? const []).cast<String>();

      for (var vIndex = 0; vIndex < vImports.length; vIndex++) {
        final vImport = vImports[vIndex];
        final vDot = vImport.lastIndexOf('.');
        final vPackage = vDot < 0 ? vImport : vImport.substring(0, vDot);

        if (!pPackages.contains(vPackage) && !vPackage.startsWith('java.')) {
          rErrors.add(
            '[ERROR] /${vFile['path']}:[${vIndex + 3},${8 + vPackage.length}] package $vPackage does not exist',
          );
        }
      }

      for (final vFeature in (vFile['features'] as List? ?? const []).cast<String>()) {
        final (vMinimum, vMessage) = features[vFeature]!;

        if (pRelease < vMinimum) {
          rErrors.add('[ERROR] /${vFile['path']}:[5,8] $vMessage in -source $pRelease');
          rErrors.add('[ERROR]   (use -source $vMinimum or higher to enable it)');
        }
      }
    }

    return rErrors;
  }

  /// Erreur d'exécution due à une dépendance trop ancienne : (exception, piste), ou null.
  (String, String)? findRuntimeErrors(Map<String, List<Object?>> pResolved) {
    for (final vKey in pResolved.keys) {
      for (final vNeed in (entry(vKey)['needs'] as Map? ?? const {}).entries) {
        final vMinimum = (vNeed.value as List).cast<int>();
        final vFound = pResolved[vNeed.key];

        if (vFound != null && compareVersions(parseVersion(vFound[0] as String), vMinimum) < 0) {
          return (
            'java.lang.NoClassDefFoundError: com/fasterxml/jackson/core/exc/StreamConstraintsException',
            '$vKey attend ${vNeed.key} ${vMinimum.join('.')} au moins, mais ${vFound[0]} a été retenue.',
          );
        }
      }
    }

    return null;
  }

  /// Arbre des dépendances, comme mvn dependency:tree.
  List<String> formatTree(Map<String, dynamic> pModel, Map<String, List<Object?>> pResolved) {
    final vRoot = [
      for (final vEntry in pResolved.entries)
        if (vEntry.value[2] == null) vEntry,
    ];
    final rLines = ['[INFO] ${pModel['groupId']}:${pModel['artifactId']}:jar:${pModel['version']}'];

    for (var vIndex = 0; vIndex < vRoot.length; vIndex++) {
      final vKey = vRoot[vIndex].key;
      final vScope = vRoot[vIndex].value[1];
      final vLast = vIndex == vRoot.length - 1;

      rLines.add('[INFO] ${vLast ? r'\-' : '+-'} $vKey:jar:${vRoot[vIndex].value[0]}:$vScope');

      final vChildren = <(String, List<Object?>?)>[
        for (final vEntry in pResolved.entries)
          if (vEntry.value[2] == vKey) (vEntry.key, vEntry.value),
        for (final vEntry in pResolved.entries)
          for (final vOmitted in vEntry.value[3] as List<List<String>>)
            if (vOmitted[0] == vKey) (vEntry.key, null),
      ];

      for (var vChildIndex = 0; vChildIndex < vChildren.length; vChildIndex++) {
        final (vChild, vValue) = vChildren[vChildIndex];
        final vBranch = vChildIndex == vChildren.length - 1 ? r'\-' : '+-';
        final vPrefix = vLast ? '   ' : '|  ';

        if (vValue == null) {
          final vWanted = (pResolved[vChild]![3] as List<List<String>>)
              .firstWhere((pItem) => pItem[0] == vKey)[1];

          rLines.add(
            '[INFO] $vPrefix$vBranch ($vChild:jar:$vWanted:$vScope - omitted for conflict with ${pResolved[vChild]![0]})',
          );
        } else {
          rLines.add('[INFO] $vPrefix$vBranch $vChild:jar:${vValue[0]}:${vValue[1]}');
        }
      }
    }

    return rLines;
  }

  /// Exécute une commande mvn ; (lignes, compte rendu de la construction).
  (List<String>, Map<String, dynamic>) run(
      Map<String, dynamic> pProject, String pPomText, String pCommand) {
    final vReport = <String, dynamic>{
      'success': false,
      'phase': null,
      'tests_run': 0,
      'skipped_tests': false,
      'jar': null,
      'scopes': <String, String>{},
    };
    final List<String> vGoals;
    final bool vSkipTests;

    try {
      (vGoals, vSkipTests) = parseCommand(pCommand);
    } on PomError catch (vError) {
      return (vError.lines, vReport);
    }

    final Map<String, dynamic> vModel;
    final List<String> vLines;
    final Map<String, List<Object?>> vResolved;

    try {
      vModel = parsePom(pPomText);
      vLines = header(vModel);
      vResolved = resolve(vModel);
    } on PomError catch (vError) {
      return (['[INFO] Scanning for projects...', ...vError.lines], vReport);
    }

    vReport['scopes'] = {for (final vEntry in vResolved.entries) vEntry.key: vEntry.value[1]};

    if (vGoals.contains('dependency:tree')) {
      vLines
        ..add('[INFO] --- dependency:3.6.1:tree (default-cli) ---')
        ..addAll(formatTree(vModel, vResolved))
        ..addAll(footer(true));
      vReport['success'] = true;

      return (vLines, vReport);
    }

    final vArtifact = vModel['artifactId'] as String;

    if (vGoals.contains('clean')) {
      vLines
        ..add('[INFO] --- clean:3.2.0:clean (default-clean) @ $vArtifact ---')
        ..add('[INFO] Deleting target');
    }

    final vTarget = vGoals
        .where(phases.contains)
        .map(phases.indexOf)
        .fold(-1, (pMax, pIndex) => pIndex > pMax ? pIndex : pMax);
    final vRelease = getRelease(vModel);
    final vProject = pProject;

    if (vTarget >= phases.indexOf('compile')) {
      vLines.add('[INFO] --- compiler:3.13.0:compile (default-compile) @ $vArtifact ---');

      final vErrors = checkImports(
        vProject['sources'] as List,
        packagesOf(vResolved, ['compile', 'provided', 'system']),
        vRelease,
      );

      if (vErrors.isNotEmpty) {
        vLines
          ..add('[ERROR] COMPILATION ERROR : ')
          ..addAll(vErrors)
          ..addAll(footer(false, ['[ERROR] Failed to execute goal compiler:3.13.0:compile']));

        return (vLines, vReport);
      }

      vLines.add(
        '[INFO] Compiling ${(vProject['sources'] as List).length} source files with javac '
        '[debug release $vRelease] to target/classes',
      );
      vReport['phase'] = 'compile';
    }

    if (vTarget >= phases.indexOf('test')) {
      final vTests = (vProject['tests'] as List).cast<Map<String, dynamic>>();

      vLines.add('[INFO] --- compiler:3.13.0:testCompile (default-testCompile) @ $vArtifact ---');

      final vErrors = checkImports(vTests, packagesOf(vResolved, scopes), vRelease);

      if (vErrors.isNotEmpty) {
        vLines
          ..add('[ERROR] COMPILATION ERROR : ')
          ..addAll(vErrors)
          ..addAll(footer(false, ['[ERROR] Failed to execute goal compiler:3.13.0:testCompile']));

        return (vLines, vReport);
      }

      final vDeclared = (vModel['plugins'] as Map<String, Map<String, String>>)[
              'org.apache.maven.plugins:maven-surefire-plugin']?['version'] ??
          '';
      final vSurefire = vDeclared.isEmpty ? defaultSurefire : vDeclared;
      final vCount = vTests.fold<int>(0, (pSum, pFile) => pSum + ((pFile['count'] as int?) ?? 0));
      const vBanner = [
        '[INFO] -------------------------------------------------------',
        '[INFO]  T E S T S',
        '[INFO] -------------------------------------------------------',
      ];

      vLines.add('[INFO] --- surefire:$vSurefire:test (default-test) @ $vArtifact ---');

      if (vSkipTests) {
        vLines.add('[INFO] Tests are skipped.');
        vReport['skipped_tests'] = true;
      } else if (compareVersions(parseVersion(vSurefire).take(2).toList(), surefireJunit5) < 0 &&
          vTests.any((pFile) =>
              (pFile['imports'] as List? ?? const []).contains('org.junit.jupiter.api.Test'))) {
        vLines
          ..addAll(vBanner)
          ..add('[INFO] Tests run: 0, Failures: 0, Errors: 0, Skipped: 0');
      } else {
        final vFailure = findRuntimeErrors(vResolved);

        vLines.addAll(vBanner);

        if (vFailure != null) {
          vLines
            ..add('[ERROR] Tests run: $vCount, Failures: 0, Errors: $vCount, Skipped: 0')
            ..add('[ERROR]   ${vFailure.$1}')
            ..addAll(footer(false, [
              '[ERROR] Failed to execute goal surefire: There are test failures.',
              '[ERROR] Piste : ${vFailure.$2} Voir mvn dependency:tree.',
            ]));

          return (vLines, vReport);
        }

        vLines.add('[INFO] Tests run: $vCount, Failures: 0, Errors: 0, Skipped: 0');
        vReport['tests_run'] = vCount;
      }

      vReport['phase'] = 'test';
    }

    if (vTarget >= phases.indexOf('package')) {
      final vJar = '$vArtifact-${vModel['version']}.${vModel['packaging']}';

      vLines
        ..add('[INFO] --- jar:3.4.1:jar (default-jar) @ $vArtifact ---')
        ..add('[INFO] Building jar: target/$vJar');
      vReport['jar'] = vJar;
      vReport['phase'] = 'package';
    }

    if (vTarget >= phases.indexOf('install')) {
      vLines.add(
        '[INFO] Installing target/${vReport['jar']} to ~/.m2/repository/'
        '${(vModel['groupId'] as String).replaceAll('.', '/')}/$vArtifact/${vModel['version']}',
      );
      vReport['phase'] = 'install';
    }

    vLines.addAll(footer(true));
    vReport['success'] = true;

    return (vLines, vReport);
  }
}

/// (phases et buts, sauter les tests) d'une commande mvn ; lève PomError avec le message.
(List<String>, bool) parseCommand(String pCommand) {
  final vWords = pySplit(pCommand);

  if (vWords.isEmpty || vWords.first != 'mvn') {
    throw PomError(['[ERROR] Commande inconnue : seules les commandes mvn sont simulées.']);
  }

  final vGoals = <String>[];
  var vSkipTests = false;

  for (final vWord in vWords.skip(1)) {
    if (vWord == '-DskipTests' || vWord == '-Dmaven.test.skip=true') {
      vSkipTests = true;
    } else if (['-q', '-B', '--batch-mode', '-U'].contains(vWord)) {
      continue;
    } else if (phases.contains(vWord) || vWord == 'clean' || vWord == 'dependency:tree') {
      vGoals.add(vWord);
    } else {
      throw PomError([
        '[ERROR] Unknown lifecycle phase "$vWord". Phases simulées : clean, ${phases.join(', ')}, et dependency:tree.',
      ]);
    }
  }

  if (vGoals.isEmpty) {
    throw PomError(
        ['[ERROR] No goals have been specified for this build : par exemple mvn package.']);
  }

  return (vGoals, vSkipTests);
}

/// En-tête affiché par Maven avant la construction.
List<String> header(Map<String, dynamic> pModel) => [
      '[INFO] Scanning for projects...',
      '[INFO] ${pyCenter('< ${pModel['groupId']}:${pModel['artifactId']} >', 72, '-')}',
      '[INFO] Building ${pModel['artifactId']} ${pModel['version']}',
      '[INFO] ${pyCenter('[ ${pModel['packaging']} ]', 72, '-')}',
    ];

/// Bilan de fin de construction.
List<String> footer(bool pSuccess, [List<String> pErrors = const []]) => [
      separator,
      pSuccess ? '[INFO] BUILD SUCCESS' : '[INFO] BUILD FAILURE',
      separator,
      ...pErrors,
    ];
