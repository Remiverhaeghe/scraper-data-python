// Simulateur d'automate, hors ligne : même cycle de 100 ms, mêmes machines et même
// chronogramme que job/ladder_game.py, gardés identiques par les cas communs.

import 'ladder.dart';
import 'python_compat.dart';

const cycleSeconds = 0.1;
const cyclesPerSecond = 10;

// Vérin : une seconde de course ; tapis : une pièce par seconde, vue 0,3 s ;
// broche : deux secondes de course
const verinStroke = 10;
const piecePeriod = 10;
const pieceVisible = 3;
const spindleStroke = 20;

int toCycles(num pSeconds) => roundHalfEven(pSeconds * cyclesPerSecond.toDouble());

/// Noms des variables d'un genre : input ou output.
List<String> namesOf(Map<String, dynamic> pLevel, String pKind) => [
      for (final vVariable in pLevel['variables'] as List)
        if ((vVariable as Map)['kind'] == pKind) vVariable['name'] as String,
    ];

/// Entrées pilotées par la machine, pas par l'opérateur.
Set<String> sensorsOf(Map<String, dynamic> pLevel) => {
      for (final vVariable in pLevel['variables'] as List)
        if ((vVariable as Map)['control'] == 'sensor') vVariable['name'] as String,
    };

/// Automate et machine simulés, avancés cycle par cycle.
class Simulator {
  Simulator(this.level, this.rungs) {
    for (final vName in collectNames(rungs)) {
      values[vName] = false;
    }

    for (final vVariable in level['variables'] as List) {
      values[(vVariable as Map)['name'] as String] = (vVariable['default'] ?? 0) != 0;
    }

    readSensors();
  }

  final Map<String, dynamic> level;
  final List<Map<String, dynamic>> rungs;
  final values = <String, bool>{};
  final timers = <String, int>{};
  final counters = <String, (int, bool)>{};
  final machine = <String, int>{'position': 0, 'run': 0};
  int cycle = 0;

  String get kind => level['machine'] as String;

  void setInput(String pName, bool pValue) => values[pName] = pValue;

  void readSensors() {
    final vPosition = machine['position']!;

    if (kind == 'verin') {
      values['fin_sortie'] = vPosition >= verinStroke;
    } else if (kind == 'tapis') {
      values['piece'] = machine['run']! % piecePeriod < pieceVisible;
    } else if (kind == 'percage') {
      values['haut'] = vPosition <= 0;
      values['bas'] = vPosition >= spindleStroke;
    }
  }

  /// Exécute les barreaux dans l'ordre, chacun voyant les résultats des précédents.
  void scan() {
    for (final vRung in rungs) {
      final vInput = evaluate(vRung['expr'] as List<Object>, values);
      final vTarget = vRung['target'] as String;

      switch (vRung['kind']) {
        case 'coil':
          values[vTarget] = vInput;
        case 'set':
          if (vInput) {
            values[vTarget] = true;
          }
        case 'reset':
          if (vInput) {
            values[vTarget] = false;
          }
        case 'ton':
          final vElapsed = vInput ? (timers[vTarget] ?? 0) + 1 : 0;

          timers[vTarget] = vElapsed;
          values[vTarget] = vElapsed >= toCycles(vRung['preset'] as num);
        default:
          var (vCount, vPrevious) = counters[vTarget] ?? (0, false);

          if (vInput && !vPrevious) {
            vCount += 1;
          }

          if (vRung['reset'] != null && evaluate(vRung['reset'] as List<Object>, values)) {
            vCount = 0;
          }

          counters[vTarget] = (vCount, vInput);
          values[vTarget] = vCount >= (vRung['preset'] as int);
      }
    }
  }

  void moveMachine() {
    if (kind == 'verin') {
      final vStep = values['sortir'] == true ? 1 : -1;

      machine['position'] = (machine['position']! + vStep).clamp(0, verinStroke);
    } else if (kind == 'tapis' && values['tapis'] == true) {
      machine['run'] = machine['run']! + 1;
    } else if (kind == 'percage') {
      final vStep = (values['descendre'] == true ? 1 : 0) - (values['monter'] == true ? 1 : 0);

      machine['position'] = (machine['position']! + vStep).clamp(0, spindleStroke);
    }
  }

  /// Un cycle d'automate : capteurs, programme, machine.
  void step() {
    readSensors();
    scan();
    moveMachine();
    cycle += 1;
  }
}

/// Exécute le scénario de test d'un niveau sur un programme.
///
/// Retourne l'erreur d'écriture éventuelle, chaque vérification, les interdits
/// violés et les valeurs de chaque cycle pour le chronogramme.
Map<String, dynamic> runLevel(Map<String, dynamic> pLevel, String pProgram) {
  final vInputs = namesOf(pLevel, 'input').toSet();
  final List<Map<String, dynamic>> vRungs;

  try {
    vRungs = parseProgram(pProgram, vInputs);
  } on LadderError catch (vError) {
    return {'passed': false, 'error': vError.message, 'line': vError.line};
  }

  if (vRungs.isEmpty) {
    return {'passed': false, 'error': 'Le programme est vide.', 'line': null};
  }

  final vSimulator = Simulator(pLevel, vRungs);
  final vEvents = <int, Map<String, dynamic>>{};
  final vChecks = <int, List<Map<String, dynamic>>>{};

  for (final vEvent in pLevel['events'] as List) {
    vEvents
        .putIfAbsent(toCycles((vEvent as Map)['at'] as num), () => {})
        .addAll(Map<String, dynamic>.from(vEvent['set'] as Map));
  }

  for (final vCheck in pLevel['checks'] as List) {
    vChecks
        .putIfAbsent(toCycles((vCheck as Map)['at'] as num), () => [])
        .add(Map<String, dynamic>.from(vCheck));
  }

  final vSignals = [...namesOf(pLevel, 'input'), ...namesOf(pLevel, 'output')];
  final vSamples = <Map<String, int>>[];
  final vResults = <Map<String, dynamic>>[];
  final vViolations = <String>[];

  for (var vCycle = 0; vCycle <= toCycles(pLevel['duration'] as num); vCycle++) {
    for (final vEntry in (vEvents[vCycle] ?? const {}).entries) {
      vSimulator.setInput(vEntry.key, vEntry.value != 0 && vEntry.value != false);
    }

    for (final vCheck in vChecks[vCycle] ?? const <Map<String, dynamic>>[]) {
      final vExpected = Map<String, dynamic>.from(vCheck['expect'] as Map);
      final vGot = {
        for (final vName in vExpected.keys) vName: vSimulator.values[vName] == true ? 1 : 0,
      };

      vResults.add({
        'at': vCheck['at'],
        'message': vCheck['message'],
        'expected': vExpected,
        'got': vGot,
        'passed': vExpected.entries.every((pEntry) => vGot[pEntry.key] == pEntry.value),
      });
    }

    vSimulator.step();
    vSamples.add({for (final vName in vSignals) vName: vSimulator.values[vName] == true ? 1 : 0});

    for (final vForbidden in pLevel['forbidden'] as List? ?? const []) {
      final vMessage = (vForbidden as Map)['message'] as String;

      if ((vForbidden['all'] as List).every((pName) => vSimulator.values[pName] == true) &&
          !vViolations.contains(vMessage)) {
        vViolations.add(vMessage);
      }
    }
  }

  final rRun = {
    'passed': vResults.every((pResult) => pResult['passed'] == true) && vViolations.isEmpty,
    'error': null,
    'line': null,
    'rungs': vRungs,
    'checks': vResults,
    'violations': vViolations,
    'signals': vSignals,
    'samples': vSamples,
  };

  return rRun;
}

const chartRow = 30;
const chartLabel = 120;
const chartStep = 6;

/// Chronogramme des signaux en SVG : une ligne par signal.
String renderChronogram(List<String> pSignals, List<Map<String, int>> pSamples,
    [Set<String> pInputs = const {}]) {
  final vWidth = chartLabel + pSamples.length * chartStep + 10;
  final vHeight = pSignals.length * chartRow + 24;
  final vParts = <String>[];

  for (var vIndex = 0; vIndex < pSignals.length; vIndex++) {
    final vName = pSignals[vIndex];
    final vTop = vIndex * chartRow + 8;
    final vHigh = vTop + 4;
    final vLow = vTop + chartRow - 10;
    final vColor = pInputs.contains(vName) ? '#2563eb' : '#16a34a';
    final vPoints = [
      for (var vCycle = 0; vCycle < pSamples.length; vCycle++)
        '${chartLabel + vCycle * chartStep},${pSamples[vCycle][vName] != 0 ? vHigh : vLow} '
            '${chartLabel + vCycle * chartStep + chartStep},${pSamples[vCycle][vName] != 0 ? vHigh : vLow}',
    ];

    vParts.add(
      '<text x="4" y="$vLow" font-size="12" fill="#0f172a">${escapeHtml(vName)}</text>'
      '<polyline points="${vPoints.join(' ')}" fill="none" stroke="$vColor" stroke-width="2"/>',
    );
  }

  for (var vSecond = 0; vSecond <= pSamples.length ~/ cyclesPerSecond; vSecond++) {
    final vX = chartLabel + vSecond * cyclesPerSecond * chartStep;

    vParts.add(
      '<line x1="$vX" y1="4" x2="$vX" y2="${vHeight - 16}" stroke="#e2e8f0"/>'
      '<text x="$vX" y="${vHeight - 4}" text-anchor="middle" font-size="10" fill="#64748b">$vSecond s</text>',
    );
  }

  final rSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="$vWidth" height="$vHeight" '
      'viewBox="0 0 $vWidth $vHeight" font-family="Arial, sans-serif" role="img" '
      'aria-label="Chronogramme des entrées et sorties">'
      '<rect width="$vWidth" height="$vHeight" fill="#ffffff"/>'
      '${vParts.join()}</svg>';

  return rSvg;
}
