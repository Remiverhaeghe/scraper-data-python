// Guide pratique d'un thème, affiché en texte sélectionnable.

import 'package:flutter/material.dart';

import '../models/quiz_package.dart';

class GuideScreen extends StatelessWidget {
  const GuideScreen({super.key, required this.guide});

  final QuizGuide guide;

  @override
  Widget build(BuildContext context) {
    final rScreen = Scaffold(
      appBar: AppBar(title: Text(guide.title)),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: SelectableText(guide.content),
      ),
    );

    return rScreen;
  }
}
