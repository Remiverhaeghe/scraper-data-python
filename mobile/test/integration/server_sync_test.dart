// Synchronisation complète avec le vrai serveur (web/api.py), lancée par la CI.
//
// Ignoré sans les variables JOBBOARD_SERVER (adresse du tableau de bord) et
// JOBBOARD_TOKEN (jeton de l'application mobile) : flutter test seul ne le joue pas.

import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/logic/exam.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/services/revision_store.dart';

import '../support/sample_data.dart';

void main() {
  final vServer = Platform.environment['JOBBOARD_SERVER'];
  final vToken = Platform.environment['JOBBOARD_TOKEN'];

  test(
    'Contenu et offres reçus ; réponse, signalement, examen, entretien, '
    'auto-évaluation et statut envoyés au vrai serveur',
    () async {
      final vState = RevisionState(MemoryRevisionStore());

      await vState.configure(
        ServerSettings(address: '$vServer/api/v1', token: vToken!),
      );

      final vQuestions =
          vState.package!.questions.where((vQuestion) => vQuestion.type == 'qcm').toList();

      expect(vQuestions.length, greaterThan(2));

      // Offre préparée par tools/mobile_integration.py, lisible hors ligne
      final vOffer = vState.offers.single;

      expect(vOffer['description'], 'Java, SQL et Docker');
      expect(vOffer['covered'], ['Java', 'SQL']);
      expect(vOffer['missing'], ['Docker']);
      expect(vState.interviewQuestions, isNotEmpty);
      expect(vState.skillGrid, isNotEmpty);

      await vState.setOfferStatus(vOffer, 'INTERESTED');
      await vState.recordInterviewSeries('Java', [
        {
          'question_id': vState.interviewQuestions.first['id'],
          'checked': [0],
        },
      ]);
      await vState.saveSkillLevels({'Java': 6});

      await vState.answer(vQuestions[0], 0);
      await vState.flagQuestion(vQuestions[1].id);
      await vState.recordExam(
        ExamResult(
          title: 'Examen d intégration',
          finishedAt: DateTime(2026, 10, 22, 18, 30),
          correct: 3,
          count: 4,
          seconds: 120,
        ),
      );

      final vReport = await vState.synchronize();

      expect(vReport.sent, 1);
      expect(vReport.rejected, 0);
      expect(vState.pending, isEmpty);
      expect(vState.flaggedIds, isEmpty);
      expect(vState.statistics['answers'], 1);
      expect(
        vState.package!.questions.any((vQuestion) => vQuestion.id == vQuestions[1].id),
        isFalse,
      );
      expect(vState.pendingStatuses, isEmpty);
      expect(vState.pendingInterview, isEmpty);
      expect(
        vState.skillGrid.firstWhere((vItem) => vItem['skill'] == 'Java')['level'],
        6,
      );
      expect(vState.offers.single['status'], 'INTERESTED');
    },
    skip: vServer == null || vToken == null ? 'Serveur de test absent' : false,
  );
}
