// Simulateur de circuits, réécrit depuis job/circuit.py : analyse nodale en courant
// continu, relais, télérupteur, protections et diodes. Les calculs suivent le même
// ordre que Python, jusqu'à la somme compensée de sum() : les nombres sont identiques.

import 'python_compat.dart';

/// Valeur réglable : (défaut, minimum, maximum, unité).
const valueRanges = <String, (double, double, double, String)>{
  'pile': (9.0, 1.5, 48.0, 'V'),
  'resistance': (1000.0, 1.0, 1000000.0, 'Ω'),
  'bobine_relais': (230.0, 5.0, 230.0, 'V'),
  'telerupteur': (230.0, 5.0, 230.0, 'V'),
};

/// Commandes manœuvrées par l'utilisateur et leur état de repos.
const operableDefaults = <String, bool>{
  'disjoncteur': true,
  'fusible': true,
  'sectionneur': false,
  'interrupteur': false,
  'bouton_marche': false,
  'bouton_arret': false,
  'va_et_vient': false,
};

const pushButtons = {'bouton_marche', 'bouton_arret'};
const protections = {'disjoncteur', 'fusible'};
const _sources = {'alimentation', 'pile'};
const _loadWatts = {'lampe_bornes': 60.0, 'moteur_mono': 750.0};
const _loads = {
  'lampe_bornes',
  'moteur_mono',
  'resistance',
  'bobine_relais',
  'telerupteur',
  'voltmetre',
};

const _mainsVolts = 230.0;
const _mainsResistance = 0.05;
const _mainsMaxCurrent = 63.0;
const _batteryResistance = 0.5;
const _batteryMaxCurrent = 3.0;
const _closedResistance = 0.01;
const _gmin = 1e-9;
const _protectionRating = 10.0;
const _coilWatts = 8.0;
const _pickupRatio = 0.7;
const _ledForward = 2.0;
const _ledSeries = 5.0;
const _ledNominalCurrent = 0.02;
const _ledMaxCurrent = 0.03;
const _ledLitCurrent = 0.002;
const _diodeForward = 0.7;
const _diodeSeries = 0.5;
const _voltmeterResistance = 1e7;
const _liveVolts = 1.0;
const _fullRatio = 0.6;
const _dimRatio = 0.1;
const _maxIterations = 40;
const _measureFloor = 1e-6;

/// Bornes d'un type de composant : (nom, x, y), dans l'ordre de la bibliothèque.
typedef PortTable = Map<String, List<(String, num, num)>>;

/// Retourne la valeur réglée d'un composant, bornée, ou sa valeur par défaut.
double getValue(String pType, String pId, Map<String, dynamic> pValues) {
  final (vDefault, vMinimum, vMaximum, _) = valueRanges[pType]!;
  final vRaw = pValues.containsKey(pId) ? pValues[pId] : vDefault;
  final double vValue;

  if (vRaw is num) {
    vValue = vRaw.toDouble();
  } else if (vRaw is bool) {
    vValue = vRaw ? 1.0 : 0.0;
  } else if (vRaw is String) {
    vValue = double.tryParse(vRaw.trim()) ?? vDefault;
  } else {
    vValue = vDefault;
  }

  final rValue = vValue.isNaN ? vDefault : vValue.clamp(vMinimum, vMaximum).toDouble();

  return rValue;
}

/// Somme compensée de Neumaier, celle de sum() en Python sur des flottants.
double pythonSum(Iterable<double> pValues) {
  var vResult = 0.0;
  var vCompensation = 0.0;

  for (final vValue in pValues) {
    final vTotal = vResult + vValue;

    if (vResult.abs() >= vValue.abs()) {
      vCompensation += (vResult - vTotal) + vValue;
    } else {
      vCompensation += (vValue - vTotal) + vResult;
    }

    vResult = vTotal;
  }

  final rResult = vCompensation != 0 && vCompensation.isFinite ? vResult + vCompensation : vResult;

  return rResult;
}

/// Résout le système linéaire par élimination de Gauss avec pivot partiel.
List<double> solve(List<List<double>> pMatrix, List<double> pVector) {
  final vSize = pVector.length;
  final vRows = [
    for (var vIndex = 0; vIndex < vSize; vIndex++) [...pMatrix[vIndex], pVector[vIndex]],
  ];

  for (var vColumn = 0; vColumn < vSize; vColumn++) {
    var vPivot = vColumn;

    for (var vRow = vColumn + 1; vRow < vSize; vRow++) {
      if (vRows[vRow][vColumn].abs() > vRows[vPivot][vColumn].abs()) {
        vPivot = vRow;
      }
    }

    final vSwap = vRows[vColumn];
    vRows[vColumn] = vRows[vPivot];
    vRows[vPivot] = vSwap;
    final vDivisor = vRows[vColumn][vColumn];

    if (vDivisor == 0) {
      continue;
    }

    for (var vRow = vColumn + 1; vRow < vSize; vRow++) {
      final vFactor = vRows[vRow][vColumn] / vDivisor;

      if (vFactor != 0) {
        final vTarget = vRows[vRow];
        final vSource = vRows[vColumn];

        for (var vIndex = vColumn; vIndex <= vSize; vIndex++) {
          vTarget[vIndex] -= vFactor * vSource[vIndex];
        }
      }
    }
  }

  final rSolution = List<double>.filled(vSize, 0.0);

  for (var vRow = vSize - 1; vRow >= 0; vRow--) {
    final vSum = vRows[vRow][vSize] -
        pythonSum([
          for (var vIndex = vRow + 1; vIndex < vSize; vIndex++)
            vRows[vRow][vIndex] * rSolution[vIndex],
        ]);
    rSolution[vRow] = vRows[vRow][vRow] != 0 ? vSum / vRows[vRow][vRow] : 0.0;
  }

  return rSolution;
}

/// Retourne une mesure lisible en français : 230 V, 3,33 V, 14,7 mA, 8 µA.
String formatMeasure(double pValue, String pUnit) {
  var vValue = pValue.abs();

  // Arrondi avant le choix de l'unité : 0,9996 A s'écrit 1 A, pas 1e+03 mA
  if (vValue < 100) {
    vValue = double.parse(formatGeneral(vValue, 3));
  }

  final String vText;
  final String vUnit;

  if (vValue < _measureFloor) {
    (vText, vUnit) = ('0', pUnit);
  } else if (vValue < 0.001) {
    (vText, vUnit) = (formatGeneral(vValue * 1e6, 3), 'µ$pUnit');
  } else if (vValue < 1) {
    (vText, vUnit) = (formatGeneral(vValue * 1000, 3), 'm$pUnit');
  } else if (vValue >= 100) {
    (vText, vUnit) = (roundHalfEven(vValue).toString(), pUnit);
  } else {
    (vText, vUnit) = (formatGeneral(vValue, 3), pUnit);
  }

  final rText = '${pValue < 0 && vText != '0' ? '-' : ''}$vText $vUnit'.replaceAll('.', ',');

  return rText;
}

/// Branche du circuit : courant de a vers b = G·(Va − Vb − E).
typedef _Branch = (String, int, int, double, double);

/// Un schéma prêt à simuler : composants, nœuds, valeurs réglées.
class Circuit {
  Circuit(
      this.ports, this.labels, List<Map<String, dynamic>> pComponents, List<List<String>> pWires,
      [Map<String, dynamic>? pValues])
      : values = pValues ?? {} {
    for (final vItem in pComponents) {
      if (ports.containsKey(vItem['type'])) {
        types[vItem['id'] as String] = vItem['type'] as String;
      }
    }

    _buildNets(pWires);
    ground = _findGround();
    coil = _findFirst('bobine_relais');
    remote = _findFirst('telerupteur');
  }

  final PortTable ports;
  final Map<String, String> labels;
  final Map<String, dynamic> values;
  final types = <String, String>{};

  /// Numéro de nœud de chaque borne, clé « id|borne ».
  final nets = <String, int>{};
  late final int ground;
  late final String? coil;
  late final String? remote;

  static String key(String pId, String pPort) => '$pId|$pPort';

  void _buildNets(List<List<String>> pWires) {
    final vParents = <String, String>{};

    String find(String pKey) {
      var vKey = pKey;

      while (vParents[vKey] != vKey) {
        vParents[vKey] = vParents[vParents[vKey]!]!;
        vKey = vParents[vKey]!;
      }

      return vKey;
    }

    for (final vEntry in types.entries) {
      for (final vPort in ports[vEntry.value]!) {
        final vKey = key(vEntry.key, vPort.$1);
        vParents[vKey] = vKey;
      }
    }

    for (final vWire in pWires) {
      final vA = key(vWire[0], vWire[1]);
      final vB = key(vWire[2], vWire[3]);

      if (vParents.containsKey(vA) && vParents.containsKey(vB)) {
        final vRootB = find(vB);
        vParents[find(vA)] = vRootB;
      }
    }

    final vNumbers = <String, int>{};

    for (final vKey in vParents.keys) {
      nets[vKey] = vNumbers.putIfAbsent(find(vKey), () => vNumbers.length);
    }
  }

  /// Premier composant d'un type, celui que suivent les contacts.
  String? _findFirst(String pType) {
    final vIds = types.keys.toList()..sort();

    for (final vId in vIds) {
      if (types[vId] == pType) {
        return vId;
      }
    }

    return null;
  }

  /// Nœud de référence : neutre, masse, sinon moins d'une pile.
  int _findGround() {
    for (final (vType, vPort) in [('alimentation', 'N'), ('masse', 'masse'), ('pile', '−')]) {
      final vId = _findFirst(vType);

      if (vId != null) {
        return nets[key(vId, vPort)]!;
      }
    }

    return 0;
  }

  /// Nœuds des bornes d'un composant, dans l'ordre de la bibliothèque.
  List<int> portNets(String pId) =>
      [for (final vPort in ports[types[pId]]!) nets[key(pId, vPort.$1)]!];

  bool _isClosed(String pId, Map<String, dynamic> pInputs, _State pState) {
    final vType = types[pId]!;
    final vInput = pInputs.containsKey(pId) ? pInputs[pId] : (operableDefaults[vType] ?? false);
    final vOn = vInput == true;

    if (protections.contains(vType)) {
      return vOn && !pState.tripped.contains(pId);
    }

    return switch (vType) {
      'bouton_arret' => !vOn,
      'contact_relais' || 'contacteur' => coil != null && pState.coils[coil] == true,
      'contact_relais_nf' => !(coil != null && pState.coils[coil] == true),
      'contact_telerupteur' => remote != null && pState.latches[remote] == true,
      'relais_thermique' || 'amperemetre' => true,
      _ => vOn,
    };
  }

  double _resistance(String pId) {
    final vType = types[pId]!;

    if (vType == 'resistance') {
      return getValue('resistance', pId, values);
    }

    if (vType == 'bobine_relais' || vType == 'telerupteur') {
      final vVolts = getValue(vType, pId, values);

      return vVolts * vVolts / _coilWatts;
    }

    if (vType == 'voltmetre') {
      return _voltmeterResistance;
    }

    return _mainsVolts * _mainsVolts / _loadWatts[vType]!;
  }

  List<_Branch> _branches(Map<String, dynamic> pInputs, _State pState) {
    final rBranches = <_Branch>[];

    for (final MapEntry(key: vId, value: vType) in types.entries) {
      final vPorts = portNets(vId);

      if (vType == 'alimentation') {
        rBranches.add((vId, vPorts[0], vPorts[1], 1 / _mainsResistance, _mainsVolts));
      } else if (vType == 'pile') {
        rBranches.add(
            (vId, vPorts[0], vPorts[1], 1 / _batteryResistance, getValue('pile', vId, values)));
      } else if (vType == 'masse') {
        rBranches.add((vId, vPorts[0], ground, 1 / _closedResistance, 0.0));
      } else if (vType == 'va_et_vient') {
        final vSide = pInputs[vId] == true ? vPorts[1] : vPorts[0];
        rBranches.add((vId, vPorts[2], vSide, 1 / _closedResistance, 0.0));
      } else if (vType == 'led' || vType == 'diode') {
        if (pState.diodes[vId] == true) {
          final (vForward, vSeries) =
              vType == 'led' ? (_ledForward, _ledSeries) : (_diodeForward, _diodeSeries);
          rBranches.add((vId, vPorts[0], vPorts[1], 1 / vSeries, vForward));
        }
      } else if (_loads.contains(vType)) {
        rBranches.add((vId, vPorts[0], vPorts[1], 1 / _resistance(vId), 0.0));
      } else if (_isClosed(vId, pInputs, pState)) {
        rBranches.add((vId, vPorts[0], vPorts[1], 1 / _closedResistance, 0.0));
      }
    }

    return rBranches;
  }

  /// Tension de chaque nœud et courant de chaque branche.
  (Map<int, double>, Map<String, double>) _compute(Map<String, dynamic> pInputs, _State pState) {
    final vBranches = _branches(pInputs, pState);
    final vCount = nets.values.fold(-1, (pMax, pNet) => pNet > pMax ? pNet : pMax) + 1;
    final vIndexes = <int, int>{};

    for (var vNet = 0; vNet < vCount; vNet++) {
      if (vNet != ground) {
        vIndexes[vNet] = vIndexes.length;
      }
    }

    final vSize = vIndexes.length;
    final vMatrix = [
      for (var vIndex = 0; vIndex < vSize; vIndex++) List<double>.filled(vSize, 0.0)
    ];
    final vVector = List<double>.filled(vSize, 0.0);

    for (var vIndex = 0; vIndex < vSize; vIndex++) {
      vMatrix[vIndex][vIndex] += _gmin;
    }

    for (final (_, vNetA, vNetB, vConductance, vForce) in vBranches) {
      final vA = vIndexes[vNetA];
      final vB = vIndexes[vNetB];

      for (final (vRow, vSign) in [(vA, 1), (vB, -1)]) {
        if (vRow != null) {
          vMatrix[vRow][vRow] += vConductance;
          vVector[vRow] += vSign * vConductance * vForce;
        }
      }

      if (vA != null && vB != null) {
        vMatrix[vA][vB] -= vConductance;
        vMatrix[vB][vA] -= vConductance;
      }
    }

    final vSolution = solve(vMatrix, vVector);
    final vVoltages = {for (final vEntry in vIndexes.entries) vEntry.key: vSolution[vEntry.value]};
    vVoltages[ground] = 0.0;

    final vCurrents = <String, double>{};

    for (final (vId, vNetA, vNetB, vConductance, vForce) in vBranches) {
      // Pour une source, le courant compté est celui qu'elle débite par sa borne +
      final vCurrent = vConductance * (vVoltages[vNetA]! - vVoltages[vNetB]! - vForce);
      vCurrents[vId] = _sources.contains(types[vId]) ? -vCurrent : vCurrent;
    }

    return (vVoltages, vCurrents);
  }

  double _voltage(String pId, Map<int, double> pVoltages) {
    final vPorts = portNets(pId);

    return pVoltages[vPorts.first]! - pVoltages[vPorts.last]!;
  }

  /// Simule le circuit pour l'état des commandes ; pMemory est l'état de l'étape précédente.
  Map<String, dynamic> simulate(Map<String, dynamic> pInputs, [Map<String, dynamic>? pMemory]) {
    final vMemory = pMemory ?? const {};
    final vState = _State(
      Map<String, dynamic>.from(vMemory['coils'] as Map? ?? const {}),
      Map<String, dynamic>.from(vMemory['latches'] as Map? ?? const {}),
      {for (final vId in vMemory['tripped'] as List? ?? const []) vId as String},
    );
    final vRemoteBefore = Map<String, dynamic>.from(vMemory['remote'] as Map? ?? const {});
    final vToggled = <String>{};
    final vFaults = <String>[];
    var vStable = false;
    late Map<int, double> vVoltages;
    late Map<String, double> vCurrents;

    for (var vIteration = 0; vIteration < _maxIterations; vIteration++) {
      (vVoltages, vCurrents) = _compute(pInputs, vState);
      final vOver = [
        for (final MapEntry(key: vId, value: vType) in types.entries)
          if (protections.contains(vType) &&
              !vState.tripped.contains(vId) &&
              (vCurrents[vId] ?? 0).abs() > _protectionRating)
            vId,
      ];

      if (vOver.isNotEmpty) {
        vState.tripped.addAll(vOver);
        continue;
      }

      final vShort = _findShort(vCurrents);

      if (vShort.isNotEmpty) {
        vFaults.add(vShort);
        vStable = true;
        break;
      }

      if (!_updateState(vState, vVoltages, vCurrents, vRemoteBefore, vToggled)) {
        vStable = true;
        break;
      }
    }

    if (!vStable) {
      vFaults
          .add('Le circuit ne se stabilise pas : un relais se coupe lui-même et bat sans arrêt.');
    }

    return _describe(pInputs, vState, vVoltages, vCurrents, vFaults);
  }

  String _findShort(Map<String, double> pCurrents) {
    for (final MapEntry(key: vId, value: vType) in types.entries) {
      if (vType == 'alimentation' && (pCurrents[vId] ?? 0).abs() > _mainsMaxCurrent) {
        return "Court-circuit sur l'alimentation, sans disjoncteur ni fusible pour couper : les câbles brûlent.";
      }

      if (vType == 'pile' && (pCurrents[vId] ?? 0).abs() > _batteryMaxCurrent) {
        return 'La pile est en court-circuit : elle chauffe et se vide.';
      }
    }

    return '';
  }

  bool _updateState(_State pState, Map<int, double> pVoltages, Map<String, double> pCurrents,
      Map<String, dynamic> pRemoteBefore, Set<String> pToggled) {
    var vChanged = false;

    for (final MapEntry(key: vId, value: vType) in types.entries) {
      if (vType == 'bobine_relais' || vType == 'telerupteur') {
        final vEnergized =
            _voltage(vId, pVoltages).abs() >= _pickupRatio * getValue(vType, vId, values);

        if (vType == 'bobine_relais') {
          vChanged |= (pState.coils[vId] ?? false) != vEnergized;
          pState.coils[vId] = vEnergized;
        } else if (vEnergized && pRemoteBefore[vId] != true && !pToggled.contains(vId)) {
          // Le télérupteur change d'état à chaque impulsion, une seule fois
          pToggled.add(vId);
          pState.latches[vId] = pState.latches[vId] != true;
          vChanged = true;
        }

        if (vType == 'telerupteur') {
          (pState.remote ??= {})[vId] = vEnergized;
        }
      } else if (vType == 'led' || vType == 'diode') {
        final vForward = vType == 'led' ? _ledForward : _diodeForward;
        final vOn = pState.diodes[vId] ?? false;
        final vNext = vOn ? (pCurrents[vId] ?? 0) > 0 : _voltage(vId, pVoltages) > vForward;

        if (vNext != vOn) {
          pState.diodes[vId] = vNext;
          vChanged = true;
        }
      }
    }

    return vChanged;
  }

  Map<String, dynamic> _describe(Map<String, dynamic> pInputs, _State pState,
      Map<int, double> pVoltages, Map<String, double> pCurrents, List<String> pFaults) {
    final vParts = <String, dynamic>{};
    final vFaults = [...pFaults];

    for (final MapEntry(key: vId, value: vType) in types.entries) {
      final vPart = <String, dynamic>{
        'type': vType,
        'voltage': ports[vType]!.length == 2 ? _voltage(vId, pVoltages) : 0.0,
        'current': pCurrents[vId] ?? 0.0,
        'potential': portNets(vId)
            .map((pNet) => pVoltages[pNet]!.abs())
            .reduce((pA, pB) => pB > pA ? pB : pA),
        'on': false,
        'status': '',
        'tone': '',
      };
      _describePart(vId, vPart, pInputs, pState, vFaults);
      vParts[vId] = vPart;
    }

    final vLive = [
      for (final MapEntry(key: vKey, value: vNet) in nets.entries)
        if (pVoltages[vNet]!.abs() > _liveVolts) vKey.split('|'),
    ]..sort((pA, pB) {
        final vOrder = pA[0].compareTo(pB[0]);

        return vOrder != 0 ? vOrder : pA[1].compareTo(pB[1]);
      });

    return {
      'parts': vParts,
      'live': vLive,
      'faults': vFaults,
      'memory': {
        'coils': pState.coils,
        'latches': pState.latches,
        'tripped': pState.tripped.toList()..sort(),
        'remote': pState.remote ?? <String, dynamic>{},
      },
    };
  }

  void _describePart(String pId, Map<String, dynamic> pPart, Map<String, dynamic> pInputs,
      _State pState, List<String> pFaults) {
    final vType = pPart['type'] as String;
    final vCurrent = (pPart['current'] as double).abs();

    if (vType == 'lampe_bornes' || vType == 'moteur_mono') {
      final vRatio = vCurrent / (_loadWatts[vType]! / _mainsVolts);
      final vWords = vType == 'lampe_bornes'
          ? ('allumée', 'faible', 'éteinte')
          : ('tourne', "n'a pas la force de démarrer", 'arrêté');
      final vOn = vRatio >= _fullRatio;
      final vDim = vRatio >= _dimRatio;

      pPart['on'] = vOn;
      pPart['status'] = vOn ? vWords.$1 : (vDim ? vWords.$2 : vWords.$3);
      pPart['tone'] = vOn ? 'lit' : (vDim ? 'dim' : '');
    } else if (vType == 'led' || vType == 'diode') {
      pPart['on'] = vType == 'led' && vCurrent >= _ledLitCurrent;
      pPart['status'] = formatMeasure(pPart['current'] as double, 'A');

      if (vType == 'led' && vCurrent > _ledMaxCurrent) {
        pPart['status'] = 'grillée';
        pPart['tone'] = 'fault';
        pPart['on'] = false;
        pFaults.add('LED grillée : ${formatMeasure(vCurrent, 'A')} pour '
            '${formatMeasure(_ledNominalCurrent, 'A')} prévus. '
            'Une résistance en série limite le courant.');
      } else if (pPart['on'] == true) {
        pPart['tone'] = 'led';
      }
    } else if (vType == 'bobine_relais' || vType == 'telerupteur') {
      final vActive =
          vType == 'bobine_relais' ? pState.coils[pId] == true : pState.remote?[pId] == true;

      pPart['on'] = vActive;
      pPart['status'] = vActive ? 'excitée' : 'au repos';
      pPart['tone'] = vActive ? 'active' : '';
    } else if (vType == 'voltmetre') {
      pPart['status'] = formatMeasure(pPart['voltage'] as double, 'V');
      pPart['tone'] = 'measure';
    } else if (vType == 'amperemetre') {
      pPart['status'] = formatMeasure(pPart['current'] as double, 'A');
      pPart['tone'] = 'measure';
    } else if (protections.contains(vType) && pState.tripped.contains(pId)) {
      pPart['status'] = vType == 'disjoncteur' ? 'déclenché' : 'fondu';
      pPart['tone'] = 'fault';
      pFaults
          .add('${labels[vType]} : surintensité de plus de ${roundHalfEven(_protectionRating)} A, '
              'il a coupé le circuit.');
    } else if (vType == 'va_et_vient') {
      pPart['status'] = pInputs[pId] == true ? 'position b' : 'position a';
    } else if (vType == 'resistance') {
      pPart['status'] = formatMeasure(pPart['current'] as double, 'A');
    } else if (!const {'alimentation', 'pile', 'masse'}.contains(vType)) {
      final vClosed = _isClosed(pId, pInputs, pState);

      pPart['on'] = vClosed;
      pPart['status'] = vClosed ? 'fermé' : 'ouvert';

      if (pushButtons.contains(vType) && pInputs[pId] == true) {
        pPart['status'] = '${pPart['status']}, appuyé';
      }
    }
  }
}

/// État d'une simulation : bobines collées, télérupteurs, protections, diodes passantes.
class _State {
  _State(this.coils, this.latches, this.tripped);

  final Map<String, dynamic> coils;
  final Map<String, dynamic> latches;
  final Set<String> tripped;
  final diodes = <String, bool>{};
  Map<String, dynamic>? remote;
}
