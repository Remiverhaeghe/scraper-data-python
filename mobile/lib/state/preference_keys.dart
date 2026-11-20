part of '../revision_state.dart';

/// Le serveur refuse plus de 500 réponses par envoi.
const maxAnswersPerUpload = 500;

/// Réponses accumulées avant un envoi automatique, si le réseau le permet.
const autoSyncEvery = 10;

/// Préférence du rappel quotidien
const reminderPreference = 'reminder_enabled';
const offerAlertPreference = 'offer_alerts';

/// Réponses de recruteurs déjà notifiées, par identifiant.
const notifiedRepliesPreference = 'notified_replies';

/// Offres suivies retirées déjà notifiées, par source et identifiant.
const notifiedWithdrawnPreference = 'notified_withdrawn';

/// Apparence choisie : system (celle du téléphone), light ou dark.
const appearancePreference = 'appearance';
const appearances = ['system', 'light', 'dark'];

/// Questions signalées, pas encore envoyées au PC
const flaggedPreference = 'flagged_questions';

/// Objectif de réponses par jour, et réponses déjà données ce jour-là
const dailyGoalPreference = 'daily_goal';
const goalDayPreference = 'goal_day';
const goalCountPreference = 'goal_count';
const defaultDailyGoal = 15;
const dailyGoals = [10, 15, 25, 40];

/// Statuts donnés aux offres sur le téléphone, pas encore envoyés au PC
const pendingStatusPreference = 'pending_status';

/// Notes rapides prises sur une offre, pas encore envoyées au PC
const pendingNotesPreference = 'pending_notes';

/// Candidatures en cours et fiches des entretiens à venir, lisibles hors ligne
const trackingPreference = 'tracking';

/// Progression reçue du PC (niveau, série, quêtes) et dernier niveau fêté ici
const gamePreference = 'game';
const celebratedLevelPreference = 'celebrated_level';

/// Semaine du dernier bilan annoncé : une seule notification par saison.
const notifiedSeasonPreference = 'notified_season';

/// Meilleur score du jeu « Contre la montre »
const timeAttackBestPreference = 'time_attack_best';

/// Avant un entretien, la fiche de préparation est proposée sur l'accueil.
const interviewSheetLead = Duration(hours: 24);

/// Taille d'une note rapide, la même limite que côté PC
const maxNoteLength = 1000;

/// Simulation d'entretien : questions reçues du PC et séries pas encore envoyées
const interviewPreference = 'interview_content';
const pendingInterviewPreference = 'pending_interview';
const labsPreference = 'labs_content';
const pendingLabsPreference = 'pending_labs';
const labScoresPreference = 'lab_scores';
const ladderPassedPreference = 'ladder_passed';
const ladderProgramsPreference = 'ladder_programs';
const gitBestPreference = 'git_best';
const gitHistoriesPreference = 'git_histories';
const devopsPassedPreference = 'devops_passed';
const devopsSessionsPreference = 'devops_sessions';
const sqlDialectPreference = 'sql_dialect';
const sqlPassedPreference = 'sql_passed';
const sqlQueriesPreference = 'sql_queries';
const excelPassedPreference = 'excel_passed';
const excelFormulasPreference = 'excel_formulas';
const circuitPassedPreference = 'circuit_passed';
const circuitDraftsPreference = 'circuit_drafts';
const puzzleProgressPreference = 'puzzle_progress';
const puzzleSeriesPreference = 'puzzle_series';
const puzzleRecapPreference = 'puzzle_recap';

/// Auto-évaluation : grille reçue du PC et niveaux saisis pas encore envoyés
const skillGridPreference = 'skill_grid';
const pendingSkillsPreference = 'pending_skills';

/// Statuts qu'une offre peut recevoir sur le téléphone, avec leur libellé
const offerStatuses = {
  'INTERESTED': 'Intéressé',
  'APPLIED': 'Postulé',
  'IGNORED': 'Ignorée',
};

/// Libellés affichés, entretien compris : ce statut se donne sur le PC
const offerStatusLabels = {...offerStatuses, 'INTERVIEW': 'Entretien'};

/// Offres retenues, gardées par le PC sur le téléphone même anciennes
const retainedStatuses = {'INTERESTED', 'APPLIED', 'INTERVIEW'};

/// Vibration à la correction : courte si juste, appuyée si faux
const hapticsPreference = 'haptics';

/// Agrandissement du texte, en plus de celui réglé sur le téléphone.
const textScalePreference = 'text_scale';
const textScales = [1.0, 1.15, 1.3];

/// Carnet de plongée : réponses et réponses justes, jour par jour, sur huit semaines.
const diveLogPreference = 'dive_log';
