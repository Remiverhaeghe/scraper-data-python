part of '../revision_state.dart';

/// Puzzles de code : séries de dix, progression par niveau et bilan de la dernière série.
mixin PuzzleSimulation on LabsState {
  Map<String, dynamic> get puzzleContent =>
      Map<String, dynamic>.from(labs['puzzles'] as Map? ?? const {});

  List<Map<String, dynamic>> get puzzles => [
        for (final vItem in puzzleContent['puzzles'] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  PuzzleRules get puzzleRules =>
      PuzzleRules(Map<String, dynamic>.from(puzzleContent['rules'] as Map? ?? const {}));

  /// Niveau, réponses justes d'affilée et statistiques : celles du téléphone depuis
  /// la dernière synchronisation, sinon celles du PC.
  Map<String, dynamic> get puzzleProgress {
    final vLocal = preferences[puzzleProgressPreference] as Map?;

    return jsonDecode(jsonEncode(vLocal ??
        {
          'level': puzzleContent['level'] ?? 1,
          'streak': puzzleContent['streak'] ?? 0,
          'best_streak': puzzleContent['best_streak'] ?? 0,
          'stats': puzzleContent['stats'] ?? <String, dynamic>{},
        })) as Map<String, dynamic>;
  }

  /// Série en cours : puzzles tirés et réponses déjà données.
  Map<String, dynamic>? get puzzleSeries => preferences[puzzleSeriesPreference] == null
      ? null
      : jsonDecode(jsonEncode(preferences[puzzleSeriesPreference])) as Map<String, dynamic>;

  /// Bilan de la dernière série terminée sur le téléphone.
  Map<String, dynamic>? get puzzleRecap =>
      (preferences[puzzleRecapPreference] as Map?)?.cast<String, dynamic>();

  Future<void> startPuzzleSeries(Random pRandom) {
    final vProgress = puzzleProgress;
    final vIds = puzzleRules.drawSeries(
      puzzles,
      vProgress['level'] as int,
      Map<String, dynamic>.from(vProgress['stats'] as Map),
      pRandom,
    );

    return savePreference(puzzleSeriesPreference, {'ids': vIds, 'answers': <Object>[]});
  }

  /// Corrige la réponse au puzzle en cours ; une série finie part au PC, qui la recorrige.
  ///
  /// Lève PuzzleAnswerError si la réponse est incomplète.
  Future<(bool, String, String)> answerPuzzle(Object? pResponse) async {
    final vSeries = puzzleSeries!;
    final vAnswers = vSeries['answers'] as List;
    final vIds = List<String>.from(vSeries['ids'] as List);
    final vPuzzle = puzzles.firstWhere((pPuzzle) => pPuzzle['id'] == vIds[vAnswers.length]);
    final rGrade = gradePuzzle(vPuzzle, pResponse);
    final (vCorrect, vGiven, vExpected) = rGrade;
    final vProgress = puzzleProgress;
    final vStats = vProgress['stats'] as Map<String, dynamic>;
    final vStat =
        Map<String, dynamic>.from(vStats[vPuzzle['id']] as Map? ?? {'right': 0, 'wrong': 0});
    final vKey = vCorrect ? 'right' : 'wrong';

    vStat[vKey] = (vStat[vKey] as int) + 1;
    vStat['last'] = vCorrect;
    vStats[vPuzzle['id'] as String] = vStat;
    vProgress['streak'] = vCorrect ? (vProgress['streak'] as int) + 1 : 0;
    vProgress['best_streak'] = max(vProgress['best_streak'] as int, vProgress['streak'] as int);
    vAnswers.add({
      'id': vPuzzle['id'],
      'response': pResponse,
      'correct': vCorrect,
      'given': vGiven,
      'expected': vExpected,
    });

    final vFinished = vAnswers.length == vIds.length;
    final vNext = {
      ...preferences,
      puzzleProgressPreference: vProgress,
      puzzleSeriesPreference: vSeries
    };

    if (vFinished) {
      final vScore = vAnswers.where((pAnswer) => (pAnswer as Map)['correct'] == true).length;

      vProgress['level'] = puzzleRules.nextLevel(vProgress['level'] as int, vScore);
      vNext
        ..remove(puzzleSeriesPreference)
        ..[puzzleRecapPreference] = {
          'score': vScore,
          'total': vIds.length,
          'mistakes': [
            for (final vAnswer in vAnswers)
              if ((vAnswer as Map)['correct'] != true) vAnswer,
          ],
        }
        ..[pendingLabsPreference] = [
          ...pendingLabs,
          newLab('puzzles', {
            'answers': [
              for (final vAnswer in vAnswers)
                {'id': (vAnswer as Map)['id'], 'response': vAnswer['response']},
            ],
          }),
        ];
    }

    preferences = vNext;
    await store.savePreferences(preferences);
    notifyListeners();

    return rGrade;
  }
}
