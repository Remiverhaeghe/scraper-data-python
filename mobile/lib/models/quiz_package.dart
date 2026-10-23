// Contenu de révision téléchargé : thèmes, questions, schémas et guides.
// Le format suit job/mobile_sync.py, version 1 de l'API.

/// Version du format que l'application sait lire.
const apiVersion = 1;

/// Types de questions affichés et corrigés par l'application.
const supportedTypes = {'qcm', 'numerique', 'ordre', 'association'};

/// Tolérance d'un calcul sans tolérance précisée, en pourcentage.
const defaultTolerance = 1.0;

/// Thème de révision, rangé dans un domaine et un sous-domaine.
class QuizTheme {
  const QuizTheme({
    required this.key,
    required this.label,
    required this.domain,
    required this.subdomain,
    this.guide,
  });

  factory QuizTheme.fromJson(Map<String, dynamic> pJson) {
    final rTheme = QuizTheme(
      key: pJson['key'] as String,
      label: pJson['label'] as String,
      domain: (pJson['domain'] as String?) ?? 'Autres',
      subdomain: (pJson['subdomain'] as String?) ?? '',
      guide: pJson['guide'] as String?,
    );

    return rTheme;
  }

  final String key;
  final String label;
  final String domain;
  final String subdomain;

  /// Nom du guide pratique du thème, s'il en a un.
  final String? guide;
}

/// Guide pratique livré avec les questions, en texte Markdown.
class QuizGuide {
  const QuizGuide({required this.name, required this.title, required this.content});

  final String name;
  final String title;
  final String content;
}

/// Question de révision ; les champs propres à son type restent dans [data].
class QuizQuestion {
  const QuizQuestion(this.data);

  final Map<String, dynamic> data;

  String get id => data['id'] as String;
  String get theme => data['theme'] as String;
  String get type => (data['type'] as String?) ?? 'qcm';
  String get level => (data['level'] as String?) ?? '';
  String get text => data['question'] as String;
  String get explanation => (data['explanation'] as String?) ?? '';
  String? get code => data['code'] as String?;

  List<String> get choices => List<String>.from(data['choices'] as List? ?? const []);
  int get answer => (data['answer'] as num?)?.toInt() ?? 0;

  double get value => (data['value'] as num).toDouble();
  String get unit => (data['unit'] as String?) ?? '';
  double get tolerance => (data['tolerance'] as num?)?.toDouble() ?? defaultTolerance;

  /// Étapes d'une remise en ordre, dans l'ordre correct.
  List<String> get items => List<String>.from(data['items'] as List? ?? const []);

  /// Paires d'une association : élément de gauche et sa correspondance.
  List<List<String>> get pairs => [
        for (final vPair in data['pairs'] as List? ?? const [])
          List<String>.from(vPair as List),
      ];

  Map<String, dynamic>? get visual => data['visual'] as Map<String, dynamic>?;

  /// Un schéma à reconnaître se montre avec la question, sinon à la correction.
  bool get visualOnQuestion => visual?['show'] == 'question';
}

/// Tout le contenu de révision, tel que téléchargé depuis le serveur.
class QuizPackage {
  const QuizPackage({
    required this.version,
    required this.themes,
    required this.questions,
    required this.assets,
    required this.guides,
    required this.leitnerIntervals,
    required this.icons,
  });

  /// Lit le contenu ; lève FormatException si son format n'est pas pris en charge.
  factory QuizPackage.fromJson(Map<String, dynamic> pJson) {
    if (pJson['api_version'] != apiVersion) {
      throw const FormatException(
        "Format de contenu non pris en charge : mettez l'application à jour.",
      );
    }

    final vQuestions = <QuizQuestion>[
      for (final vItem in pJson['questions'] as List? ?? const [])
        QuizQuestion(Map<String, dynamic>.from(vItem as Map)),
      // Un type ajouté plus tard sur le serveur est ignoré sans erreur.
      for (final vItem in pJson['interactive_questions'] as List? ?? const [])
        if (supportedTypes.contains((vItem as Map)['type']))
          QuizQuestion(Map<String, dynamic>.from(vItem)),
    ];

    final vGuides = <String, QuizGuide>{
      for (final vItem in pJson['guides'] as List? ?? const [])
        if (vItem is Map)
          vItem['name'] as String: QuizGuide(
            name: vItem['name'] as String,
            title: (vItem['title'] as String?) ?? vItem['name'] as String,
            content: (vItem['content'] as String?) ?? '',
          ),
    };

    final rPackage = QuizPackage(
      version: pJson['version'] as String,
      themes: [
        for (final vItem in pJson['themes'] as List? ?? const [])
          QuizTheme.fromJson(Map<String, dynamic>.from(vItem as Map)),
      ],
      questions: vQuestions,
      assets: Map<String, String>.from(pJson['assets'] as Map? ?? const {}),
      guides: vGuides,
      leitnerIntervals: List<int>.from(
        pJson['leitner_intervals'] as List? ?? const [1, 3, 7, 21, 60],
      ),
      icons: Map<String, String>.from(pJson['icons'] as Map? ?? const {}),
    );

    return rPackage;
  }

  final String version;
  final List<QuizTheme> themes;
  final List<QuizQuestion> questions;

  /// Schémas SVG, par nom.
  final Map<String, String> assets;
  final Map<String, QuizGuide> guides;

  /// Jours avant la prochaine révision, selon la boîte de Leitner.
  final List<int> leitnerIntervals;

  /// Icône de chaque domaine, nommée comme sur le PC.
  final Map<String, String> icons;

  /// Même contenu sans les questions signalées, retirées de tous les tirages.
  QuizPackage withoutQuestions(Set<String> pQuestionIds) {
    final rPackage = pQuestionIds.isEmpty
        ? this
        : QuizPackage(
            version: version,
            themes: themes,
            questions: [
              for (final vQuestion in questions)
                if (!pQuestionIds.contains(vQuestion.id)) vQuestion,
            ],
            assets: assets,
            guides: guides,
            leitnerIntervals: leitnerIntervals,
            icons: icons,
          );

    return rPackage;
  }

  /// Questions d'un thème.
  List<QuizQuestion> questionsOf(String pThemeKey) {
    final rQuestions = [
      for (final vQuestion in questions)
        if (vQuestion.theme == pThemeKey) vQuestion,
    ];

    return rQuestions;
  }
}
