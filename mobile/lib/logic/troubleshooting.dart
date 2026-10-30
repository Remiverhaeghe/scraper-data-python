// Pannes à résoudre, jouées hors ligne : même logique que job/troubleshooting.py,
// gardée identique par les cas de tests/fixtures/shared_lab_cases.json.

import 'python_compat.dart';

const checkPrefix = 'check:';
const repairPrefix = 'repair:';

/// Règles reçues du PC : pénalité, plafond sans preuve, seuils des étoiles, points.
class TroubleshootingRules {
  const TroubleshootingRules({
    this.wrongPenalty = 15,
    this.unprovenScore = 50,
    this.starThresholds = const [80, 50, 0],
    this.xpBase = 20,
    this.xpPerTen = 2,
  });

  factory TroubleshootingRules.fromJson(Map<String, dynamic> pJson) => TroubleshootingRules(
        wrongPenalty: pJson['wrong_penalty'] as int? ?? 15,
        unprovenScore: pJson['unproven_score'] as int? ?? 50,
        starThresholds: List<int>.from(pJson['star_thresholds'] as List? ?? const [80, 50, 0]),
        xpBase: pJson['xp_base'] as int? ?? 20,
        xpPerTen: pJson['xp_per_ten'] as int? ?? 2,
      );

  final int wrongPenalty;
  final int unprovenScore;
  final List<int> starThresholds;
  final int xpBase;
  final int xpPerTen;
}

/// Nombre d'étoiles d'un score, de 1 à 3.
int starsOf(int pScore, TroubleshootingRules pRules) {
  var rStars = 1;

  for (var vIndex = 0; vIndex < pRules.starThresholds.length; vIndex++) {
    if (pScore >= pRules.starThresholds[vIndex]) {
      rStars = 3 - vIndex;
      break;
    }
  }

  return rStars;
}

/// Score sur 100 : temps comparé au meilleur, moins les erreurs, plafonné sans preuve.
int scoreOf(
  Map<String, dynamic> pScenario,
  int pMinutes,
  int pWrongCount,
  bool pProven,
  TroubleshootingRules pRules,
) {
  final vBest = pScenario['best_minutes'] as int;
  var vScore = roundHalfEven(100 * vBest / (pMinutes < 1 ? 1 : pMinutes));

  vScore = (vScore > 100 ? 100 : vScore) - pRules.wrongPenalty * pWrongCount;

  if (!pProven && vScore > pRules.unprovenScore) {
    vScore = pRules.unprovenScore;
  }

  final rScore = vScore < 0 ? 0 : vScore;

  return rScore;
}

/// Points gagnés par une panne résolue : un forfait plus un bonus selon le score.
int xpOf(int pScore, TroubleshootingRules pRules) =>
    pRules.xpBase + pRules.xpPerTen * (pScore ~/ 10);

/// Rejoue les actions sur un scénario et retourne l'état de la partie.
///
/// Une mesure qui demande une consignation non faite est refusée sans coûter de
/// temps ; la partie s'arrête à la bonne réparation.
Map<String, dynamic> playScenario(
  Map<String, dynamic> pScenario,
  List<String> pActions, [
  TroubleshootingRules pRules = const TroubleshootingRules(),
]) {
  final vChecks = {
    for (final vCheck in pScenario['checks'] as List) (vCheck as Map)['id'] as String: vCheck,
  };
  final vCauses = {
    for (final vCause in pScenario['causes'] as List) (vCause as Map)['id'] as String: vCause,
  };
  final vDone = <String>[];
  final vWrong = <String>[];
  final vLog = <Map<String, dynamic>>[];
  var vMinutes = 0;
  var vSolved = false;

  for (final vAction in pActions) {
    if (vSolved) {
      break;
    }

    if (vAction.startsWith(checkPrefix)) {
      final vCheck = vChecks[vAction.substring(checkPrefix.length)];

      if (vCheck == null || vDone.contains(vCheck['id'])) {
        continue;
      }

      final vRequires = vCheck['requires'] as String?;

      if (vRequires != null && vRequires.isNotEmpty && !vDone.contains(vRequires)) {
        vLog.add({
          'label': vCheck['label'],
          'result': "Refusé : consignez d'abord, cette mesure se fait hors tension.",
          'minutes': 0,
          'refused': true,
        });
        continue;
      }

      vDone.add(vCheck['id'] as String);
      vMinutes += vCheck['minutes'] as int;
      vLog.add(
          {'label': vCheck['label'], 'result': vCheck['result'], 'minutes': vCheck['minutes']});
    } else if (vAction.startsWith(repairPrefix)) {
      final vCause = vCauses[vAction.substring(repairPrefix.length)];

      if (vCause == null || vWrong.contains(vCause['id'])) {
        continue;
      }

      vMinutes += vCause['minutes'] as int;
      vSolved = vCause['right'] == true;

      if (!vSolved) {
        vWrong.add(vCause['id'] as String);
      }

      final vNote = vCause['note'] as String?;

      vLog.add({
        'label': vCause['label'],
        'result':
            (vSolved ? 'La machine repart : panne résolue.' : 'Essai : la panne est toujours là.') +
                (vNote != null && vNote.isNotEmpty ? ' $vNote' : ''),
        'minutes': vCause['minutes'],
        'repair': true,
        'solved': vSolved,
      });
    }
  }

  final vProven = vDone.any((pId) => vChecks[pId]?['evidence'] == true);
  final vScore = vSolved ? scoreOf(pScenario, vMinutes, vWrong.length, vProven, pRules) : null;

  final rState = <String, dynamic>{
    'done': vDone,
    'wrong': vWrong,
    'log': vLog,
    'minutes': vMinutes,
    'solved': vSolved,
    'proven': vProven,
    'score': vScore,
    'stars': vScore == null ? 0 : starsOf(vScore, pRules),
  };

  return rState;
}
