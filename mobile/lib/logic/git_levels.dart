// Niveaux Git et graphe des commits, hors ligne : même comparaison par la forme
// (job/git_levels.py) et même dessin SVG (job/git_graph.py) que sur le PC.

import 'dart:convert';

import 'git_sandbox.dart';
import 'python_compat.dart';

const columnWidth = 78;
const rowHeight = 74;
const margin = 34;
const radius = 15;
const laneColors = ['#2563eb', '#16a34a', '#d97706', '#9333ea', '#0891b2', '#dc2626'];
const headColor = '#0f172a';
const fadedOpacity = '0.3';

/// Position (colonne, ligne) de chaque commit.
Map<String, (int, int)> computeLayout(Repository pRepository) {
  final rLayout = <String, (int, int)>{};
  final vLaneTaken = <String>{};
  var vLaneCount = 0;

  for (final vEntry in pRepository.commits.entries) {
    final vParents = vEntry.value.parents;
    final vColumn = vParents.isEmpty
        ? 0
        : vParents.map((pParent) => rLayout[pParent]!.$1 + 1).reduce((pA, pB) => pA > pB ? pA : pB);
    int vLane;

    if (vParents.isNotEmpty && !vLaneTaken.contains(vParents.first)) {
      vLane = rLayout[vParents.first]!.$2;
      vLaneTaken.add(vParents.first);
    } else {
      vLane = vLaneCount;
      vLaneCount++;
    }

    rLayout[vEntry.key] = (vColumn, vLane);
  }

  return rLayout;
}

/// Étiquette de chaque commit : ses branches, HEAD marqué d'une *.
Map<String, List<String>> buildLabels(Repository pRepository, [bool pShowHead = true]) {
  final rLabels = <String, List<String>>{};

  for (final vName in sortedOf(pRepository.branches.keys)) {
    final vCurrent = pShowHead && !pRepository.detached && pRepository.head == vName;

    rLabels.putIfAbsent(pRepository.branches[vName]!, () => []).add(vCurrent ? '$vName*' : vName);
  }

  if (pShowHead && pRepository.detached) {
    rLabels.putIfAbsent(pRepository.head, () => []).add('HEAD');
  }

  return rLabels;
}

(int, int) positionOf((int, int) pCell) =>
    (margin + pCell.$1 * columnWidth, margin + pCell.$2 * rowHeight);

String drawEdge((int, int) pFrom, (int, int) pTo, String pOpacity) {
  final vMiddle = (pFrom.$1 + pTo.$1) / 2;

  return '<path d="M${pFrom.$1} ${pFrom.$2} C$vMiddle ${pFrom.$2} $vMiddle ${pTo.$2} ${pTo.$1} ${pTo.$2}" '
      'fill="none" stroke="#94a3b8" stroke-width="2.5" opacity="$pOpacity"/>';
}

String drawCommit(
    String pCommit, (int, int) pPosition, String pColor, bool pIsHead, List<String>? pLabels) {
  final (vX, vY) = pPosition;
  var rSvg =
      '<circle cx="$vX" cy="$vY" r="$radius" fill="$pColor" stroke="${pIsHead ? headColor : pColor}" '
      'stroke-width="${pIsHead ? 4 : 2}"/>'
      '<text x="$vX" y="${vY + 4}" text-anchor="middle" font-size="11" font-weight="600" '
      'fill="#ffffff">${escapeHtml(pCommit)}</text>';

  if (pLabels != null && pLabels.isNotEmpty) {
    rSvg += '<text x="$vX" y="${vY + radius + 15}" text-anchor="middle" font-size="11" '
        'font-weight="600" fill="$headColor">${escapeHtml(pLabels.join(', '))}</text>';
  }

  return rSvg;
}

/// SVG du graphe ; les commits devenus invisibles sont estompés.
String renderGraph(Repository pRepository, String pTitle, [bool pShowHead = true]) {
  final vLayout = computeLayout(pRepository);
  final vPositions = {for (final vEntry in vLayout.entries) vEntry.key: positionOf(vEntry.value)};
  final vLabels = buildLabels(pRepository, pShowHead);
  final vReachable = pRepository.reachable();
  final vEdges = <String>[];
  final vNodes = <String>[];

  for (final vEntry in pRepository.commits.entries) {
    final vOpacity = vReachable.contains(vEntry.key) ? '1' : fadedOpacity;

    vEdges.addAll([
      for (final vParent in vEntry.value.parents)
        drawEdge(vPositions[vParent]!, vPositions[vEntry.key]!, vOpacity),
    ]);
    vNodes.add(
      '<g opacity="$vOpacity">'
      '${drawCommit(vEntry.key, vPositions[vEntry.key]!, laneColors[vLayout[vEntry.key]!.$2 % laneColors.length], pShowHead && vEntry.key == pRepository.headCommit(), vLabels[vEntry.key])}'
      '</g>',
    );
  }

  final vWidth =
      vPositions.values.map((pPosition) => pPosition.$1).reduce((pA, pB) => pA > pB ? pA : pB) +
          margin +
          60;
  final vHeight =
      vPositions.values.map((pPosition) => pPosition.$2).reduce((pA, pB) => pA > pB ? pA : pB) +
          margin +
          24;

  return '<svg xmlns="http://www.w3.org/2000/svg" width="$vWidth" height="$vHeight" '
      'viewBox="0 0 $vWidth $vHeight" role="img" font-family="Segoe UI, Arial, sans-serif">'
      '<title>${escapeHtml(pTitle)}</title>'
      '<rect width="$vWidth" height="$vHeight" fill="#ffffff"/>'
      '${vEdges.join()}${vNodes.join()}</svg>';
}

/// Forme de chaque commit, indépendante des identifiants des nouveaux commits.
Map<String, Object> buildSignatures(Repository pRepository, Set<String> pBaseCommits) {
  final rSignatures = <String, Object>{};

  for (final vEntry in pRepository.commits.entries) {
    final vData = vEntry.value;

    rSignatures[vEntry.key] = pBaseCommits.contains(vEntry.key)
        ? vEntry.key
        : [
            vData.kind,
            rSignatures[vData.origin] ?? '',
            [for (final vParent in vData.parents) rSignatures[vParent]!],
            [
              for (final vFile in vData.tree.entries) [vFile.key, vFile.value]
            ],
          ];
  }

  return rSignatures;
}

List<Object> signReferences(Map<String, String> pReferences, Map<String, Object> pSignatures) => [
      for (final vName in sortedOf(pReferences.keys)) [vName, pSignatures[pReferences[vName]]!],
    ];

/// Ce qui définit l'état d'un dépôt, en texte comparable : branches, serveur, HEAD, fichiers.
String describe(Repository pRepository, Set<String> pBaseCommits) {
  final vSignatures = buildSignatures(pRepository, pBaseCommits);

  return jsonEncode([
    signReferences(pRepository.branches, vSignatures),
    signReferences(pRepository.remote, vSignatures),
    signReferences(pRepository.tracking, vSignatures),
    pRepository.detached
        ? ['détaché', vSignatures[pRepository.head]]
        : ['branche', pRepository.head],
    [
      for (final vFile in sortedOf(pRepository.changes.keys)) [vFile, pRepository.changes[vFile]]
    ],
    sortedOf(pRepository.staged),
    [
      for (final vEntry in pRepository.stash)
        [
          for (final vFile in sortedOf((vEntry['changes'] as Map<String, String>).keys))
            [vFile, (vEntry['changes'] as Map<String, String>)[vFile]],
        ],
    ],
    pRepository.conflict?['operation'],
  ]);
}

List<String> setupOf(Map<String, dynamic> pLevel) => List<String>.from(pLevel['setup'] as List);

List<String> solutionOf(Map<String, dynamic> pLevel) =>
    List<String>.from(pLevel['solution'] as List);

/// Dépôt attendu à la fin du niveau : mise en place puis solution de référence.
Repository goalOf(Map<String, dynamic> pLevel) =>
    replay([...setupOf(pLevel), ...solutionOf(pLevel)]);

bool isGoalReached(Map<String, dynamic> pLevel, Repository pRepository) {
  final vBaseCommits = replay(setupOf(pLevel)).commits.keys.toSet();

  return describe(pRepository, vBaseCommits) == describe(goalOf(pLevel), vBaseCommits);
}

/// Dépôt du niveau après les commandes déjà saisies.
Repository replayLevel(Map<String, dynamic> pLevel, List<String> pHistory) {
  if (pHistory.length > maxHistory) {
    throw GitError('Plus de $maxHistory commandes : recommencez le niveau.');
  }

  final rRepository = replay(setupOf(pLevel));

  for (final vCommand in pHistory) {
    runCommand(rRepository, vCommand);
  }

  return rRepository;
}

/// Joue une commande dans un niveau ; (historique, message, couleur).
(List<String>, String, String) runLevelCommand(
    Map<String, dynamic> pLevel, List<String> pHistory, String pCommand) {
  final vRepository = replayLevel(pLevel, pHistory);

  if (isGoalReached(pLevel, vRepository)) {
    return (List.of(pHistory), 'Niveau déjà réussi : recommencez-le.', 'warning');
  }

  final vCommand = pCommand.split(RegExp(r'\s+')).where((pWord) => pWord.isNotEmpty).join(' ');
  String vMessage;

  try {
    vMessage = runCommand(vRepository, vCommand);
  } on GitError catch (vError) {
    return (List.of(pHistory), vError.message, 'danger');
  }

  final vHistory = [...pHistory, vCommand];

  if (vHistory.length > maxHistory) {
    return (List.of(pHistory), 'Limite de $maxHistory commandes atteinte.', 'warning');
  }

  if (isGoalReached(pLevel, vRepository)) {
    final vPar = solutionOf(pLevel).length;

    return (
      vHistory,
      'Niveau réussi en ${vHistory.length} commande(s)'
          '${vHistory.length <= vPar ? ' : parcours optimal.' : ', la solution de référence en utilise $vPar.'}',
      'success',
    );
  }

  return (vHistory, vMessage, 'info');
}
