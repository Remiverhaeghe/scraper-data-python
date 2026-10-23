// Données d'exemple communes aux tests, au format envoyé par le serveur.

import 'package:jobboard_revision/services/revision_store.dart';

Map<String, dynamic> buildPackageJson({String pVersion = 'v1'}) {
  final rPackage = <String, dynamic>{
    'api_version': 1,
    'version': pVersion,
    'generated_at': '2026-10-19T10:00:00',
    'themes': [
      {
        'key': 'docker',
        'label': 'Docker',
        'domain': 'Informatique',
        'subdomain': 'Exploitation et DevOps',
        'skills': ['Docker'],
        'guide': 'docker.md',
      },
      {
        'key': 'electricite',
        'label': 'Électricité',
        'domain': 'Industrie',
        'subdomain': 'Électricité',
        'skills': [],
        'guide': null,
      },
    ],
    'questions': [
      {
        'id': 'docker-image',
        'theme': 'docker',
        'level': 'débutant',
        'question': 'Quelle différence entre une image et un conteneur ?',
        'choices': ['Aucune', "L'image est le modèle", 'Le conteneur est sur Docker Hub'],
        'answer': 1,
        'explanation': 'Une image se lance en conteneurs.',
      },
    ],
    'interactive_questions': [
      {
        'id': 'ohm-courant',
        'theme': 'electricite',
        'type': 'numerique',
        'level': 'débutant',
        'question': 'Courant dans 100 Ω sous 0,23 V ?',
        'value': 0.0023,
        'unit': 'A',
        'tolerance': 2,
        'explanation': 'I = U / R.',
      },
      {
        'id': 'consignation',
        'theme': 'electricite',
        'type': 'ordre',
        'level': 'intermédiaire',
        'question': 'Remettre la consignation dans l’ordre.',
        'items': ['Séparer', 'Condamner', 'Identifier', 'Vérifier'],
        'explanation': 'Séparer, condamner, identifier, vérifier.',
      },
      {
        'id': 'unites',
        'theme': 'electricite',
        'type': 'association',
        'level': 'débutant',
        'question': 'Associer chaque grandeur à son unité.',
        'pairs': [
          ['Tension', 'V'],
          ['Courant', 'A'],
        ],
        'explanation': 'Volt, ampère.',
      },
      {
        'id': 'futur-type',
        'theme': 'electricite',
        'type': 'zone',
        'question': 'Type pas encore pris en charge.',
      },
    ],
    'interactive_types': ['numerique', 'ordre', 'association'],
    'assets': {'schema.svg': '<svg xmlns="http://www.w3.org/2000/svg"></svg>'},
    'guides': [
      {'name': 'docker.md', 'theme': 'docker', 'title': 'Guide Docker', 'content': '# Docker'},
    ],
    'levels': ['débutant', 'intermédiaire', 'confirmé', 'expert'],
    'leitner_intervals': [1, 3, 7, 21, 60],
    'icons': {'Informatique': 'terminal', 'Industrie': 'settings'},
  };

  return rPackage;
}

Map<String, dynamic> buildProgressJson({Map<String, dynamic>? pQuestions}) {
  final rProgress = <String, dynamic>{
    'api_version': 1,
    'generated_at': '2026-10-19T10:00:00',
    'questions': pQuestions ?? <String, dynamic>{},
    'statistics': {'acquired': 0, 'total': 5, 'answers': 0, 'rate': null, 'streak': 0},
  };

  return rProgress;
}

/// Stockage en mémoire, à la place des fichiers et du stockage chiffré.
class MemoryRevisionStore implements RevisionStore {
  ServerSettings? settings;
  String? package;
  Map<String, dynamic>? progress;
  List<Map<String, dynamic>> pending = [];

  @override
  Future<ServerSettings?> loadSettings() async => settings;

  @override
  Future<void> saveSettings(ServerSettings pSettings) async => settings = pSettings;

  @override
  Future<String?> loadPackage() async => package;

  @override
  Future<void> savePackage(String pContent) async => package = pContent;

  @override
  Future<Map<String, dynamic>?> loadProgress() async => progress;

  @override
  Future<void> saveProgress(Map<String, dynamic> pProgress) async => progress = pProgress;

  @override
  Future<List<Map<String, dynamic>>> loadPending() async => pending;

  @override
  Future<void> savePending(List<Map<String, dynamic>> pAnswers) async => pending = pAnswers;

  List<Map<String, dynamic>> examResults = [];
  Map<String, dynamic> preferences = {};

  List<Map<String, dynamic>> offers = [];

  bool syncLocked = false;

  @override
  Future<bool> acquireSyncLock() async {
    final rAcquired = !syncLocked;

    syncLocked = true;

    return rAcquired;
  }

  @override
  Future<void> releaseSyncLock() async => syncLocked = false;

  @override
  Future<List<Map<String, dynamic>>> loadOffers() async => offers;

  @override
  Future<void> saveOffers(List<Map<String, dynamic>> pOffers) async => offers = pOffers;

  @override
  Future<List<Map<String, dynamic>>> loadExamResults() async => examResults;

  @override
  Future<void> saveExamResults(List<Map<String, dynamic>> pResults) async => examResults = pResults;

  @override
  Future<Map<String, dynamic>> loadPreferences() async => preferences;

  @override
  Future<void> savePreferences(Map<String, dynamic> pPreferences) async =>
      preferences = pPreferences;
}
