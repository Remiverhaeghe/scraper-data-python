// Célébration : confettis et carte au centre, pour un niveau gagné ou un record.
// Courte, fermée d'un toucher ; sans confettis si le téléphone demande de
// réduire les animations.

import 'dart:math';

import 'package:flutter/material.dart';

const celebrationDuration = Duration(milliseconds: 2600);
const confettiCount = 90;
const confettiColors = [
  Color(0xFF3B82F6),
  Color(0xFFF59E0B),
  Color(0xFF8B5CF6),
  Color(0xFF10B981),
  Color(0xFFEC4899),
  Color(0xFF06B6D4),
];

/// Affiche la célébration par-dessus l'écran courant.
Future<void> showCelebration(
  BuildContext pContext, {
  required String title,
  required String subtitle,
  String detail = '',
}) {
  final rShown = showGeneralDialog<void>(
    context: pContext,
    barrierDismissible: true,
    barrierLabel: 'Fermer',
    barrierColor: Colors.black45,
    transitionDuration: const Duration(milliseconds: 350),
    pageBuilder: (_, __, ___) => CelebrationView(title: title, subtitle: subtitle, detail: detail),
    transitionBuilder: (_, pAnimation, __, pChild) => ScaleTransition(
      scale: CurvedAnimation(parent: pAnimation, curve: Curves.easeOutBack),
      child: pChild,
    ),
  );

  return rShown;
}

class CelebrationView extends StatefulWidget {
  const CelebrationView({super.key, required this.title, required this.subtitle, this.detail = ''});

  final String title;
  final String subtitle;
  final String detail;

  @override
  State<CelebrationView> createState() => _CelebrationViewState();
}

class _CelebrationViewState extends State<CelebrationView> with SingleTickerProviderStateMixin {
  late final AnimationController controller =
      AnimationController(vsync: this, duration: celebrationDuration);
  final pieces = List.generate(confettiCount, (_) => ConfettiPiece(Random()));

  @override
  void initState() {
    super.initState();

    controller.forward().whenComplete(() {
      if (mounted && (ModalRoute.of(context)?.isCurrent ?? false)) {
        Navigator.of(context).pop();
      }
    });
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final vTheme = Theme.of(context);
    final vReduced = MediaQuery.disableAnimationsOf(context);

    final rView = GestureDetector(
      onTap: () => Navigator.of(context).pop(),
      child: Material(
        type: MaterialType.transparency,
        child: Stack(
          children: [
            if (!vReduced)
              Positioned.fill(
                child: AnimatedBuilder(
                  animation: controller,
                  builder: (_, __) => CustomPaint(
                    painter: ConfettiPainter(pieces, controller.value),
                  ),
                ),
              ),
            Center(
              child: Card(
                margin: const EdgeInsets.all(32),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        widget.title,
                        style: vTheme.textTheme.displaySmall?.copyWith(
                          color: vTheme.colorScheme.primary,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(widget.subtitle, style: vTheme.textTheme.titleLarge),
                      if (widget.detail.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Text(widget.detail, textAlign: TextAlign.center),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );

    return rView;
  }
}

/// Un confetti : départ, vitesse, dérive et rotation tirés au hasard.
class ConfettiPiece {
  ConfettiPiece(Random pRandom)
      : x = pRandom.nextDouble(),
        y = -pRandom.nextDouble() * 0.6,
        speed = 0.5 + pRandom.nextDouble() * 0.7,
        drift = (pRandom.nextDouble() - 0.5) * 0.3,
        spin = (pRandom.nextDouble() - 0.5) * 20,
        size = 6 + pRandom.nextDouble() * 6,
        color = confettiColors[pRandom.nextInt(confettiColors.length)];

  final double x;
  final double y;
  final double speed;
  final double drift;
  final double spin;
  final double size;
  final Color color;
}

class ConfettiPainter extends CustomPainter {
  ConfettiPainter(this.pieces, this.progress);

  final List<ConfettiPiece> pieces;
  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final vPaint = Paint();
    // Les confettis s'effacent pendant le dernier cinquième de l'animation.
    final vOpacity = progress < 0.8 ? 1.0 : (1 - progress) / 0.2;

    for (final vPiece in pieces) {
      vPaint.color = vPiece.color.withValues(alpha: vOpacity);
      canvas
        ..save()
        ..translate(
          (vPiece.x + vPiece.drift * progress) * size.width,
          (vPiece.y + vPiece.speed * progress * 1.6) * size.height,
        )
        ..rotate(vPiece.spin * progress)
        ..drawRect(
          Rect.fromCenter(center: Offset.zero, width: vPiece.size, height: vPiece.size / 2),
          vPaint,
        )
        ..restore();
    }
  }

  @override
  bool shouldRepaint(ConfettiPainter oldDelegate) => oldDelegate.progress != progress;
}
