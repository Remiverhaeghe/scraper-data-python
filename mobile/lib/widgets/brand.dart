// Éléments de l'identité de Tremplin : la courbe du saut, l'en-tête en dégradé,
// l'anneau de l'objectif du jour et les barres de progression animées.

import 'dart:math';

import 'package:flutter/material.dart';

import '../theme.dart';

/// Le tremplin et la trajectoire d'un saut qui monte vers une étoile.
///
/// [progress], de 0 à 1, dessine la trajectoire jusque-là : l'en-tête la fait
/// monter à l'ouverture, l'icône la montre entière.
class SpringboardPainter extends CustomPainter {
  const SpringboardPainter({this.progress = 1, this.color = Colors.white});

  final double progress;
  final Color color;

  @override
  void paint(Canvas pCanvas, Size pSize) {
    final vWidth = pSize.width;
    final vHeight = pSize.height;
    final vPlank = Paint()
      ..color = color
      ..strokeWidth = vHeight * 0.06
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    // Planche du tremplin, légèrement relevée au bout
    final vBoard = Path()
      ..moveTo(vWidth * 0.08, vHeight * 0.86)
      ..quadraticBezierTo(vWidth * 0.3, vHeight * 0.86, vWidth * 0.42, vHeight * 0.74);
    pCanvas.drawPath(vBoard, vPlank);

    // Trajectoire en pointillés, de plus en plus gros vers l'étoile
    final vStart = Offset(vWidth * 0.44, vHeight * 0.7);
    final vControl = Offset(vWidth * 0.62, vHeight * 0.08);
    final vEnd = Offset(vWidth * 0.84, vHeight * 0.26);
    const vDots = 9;
    final vDot = Paint()..color = color;
    for (var vIndex = 1; vIndex <= vDots; vIndex++) {
      final vT = vIndex / (vDots + 1);
      if (vT > progress) {
        break;
      }
      final vPoint = _quadratic(vStart, vControl, vEnd, vT);
      pCanvas.drawCircle(vPoint, vHeight * (0.012 + 0.018 * vT), vDot);
    }

    if (progress >= 1) {
      _star(pCanvas, vEnd, vHeight * 0.1, Paint()..color = sunriseColor);
    }
  }

  static Offset _quadratic(Offset pA, Offset pB, Offset pC, double pT) {
    final vU = 1 - pT;
    final rPoint = pA * (vU * vU) + pB * (2 * vU * pT) + pC * (pT * pT);

    return rPoint;
  }

  static void _star(Canvas pCanvas, Offset pCentre, double pRadius, Paint pPaint) {
    final vPath = Path();
    for (var vIndex = 0; vIndex < 10; vIndex++) {
      final vRadius = vIndex.isEven ? pRadius : pRadius * 0.45;
      final vAngle = -pi / 2 + vIndex * pi / 5;
      final vPoint = pCentre + Offset(cos(vAngle), sin(vAngle)) * vRadius;
      vIndex == 0 ? vPath.moveTo(vPoint.dx, vPoint.dy) : vPath.lineTo(vPoint.dx, vPoint.dy);
    }
    pCanvas.drawPath(vPath..close(), pPaint);
  }

  @override
  bool shouldRepaint(SpringboardPainter pOld) => pOld.progress != progress || pOld.color != color;
}

/// Courbe du saut qui se dessine une fois à l'apparition.
class SpringboardMark extends StatelessWidget {
  const SpringboardMark({super.key, this.size = 96, this.color = Colors.white});

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final rMark = TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: motionOf(context, const Duration(milliseconds: 1100)),
      curve: Curves.easeOutCubic,
      builder: (_, pProgress, __) => CustomPaint(
        size: Size.square(size),
        painter: SpringboardPainter(progress: pProgress, color: color),
      ),
    );

    return rMark;
  }
}

/// Carte d'en-tête en dégradé de nuit, avec la courbe du saut en filigrane.
class ElanCard extends StatelessWidget {
  const ElanCard({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final rCard = DecoratedBox(
      decoration: BoxDecoration(
        gradient: elanGradient,
        borderRadius: BorderRadius.circular(24),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: Stack(
          children: [
            Positioned(
              right: -24,
              bottom: -28,
              child: Opacity(
                opacity: 0.18,
                child: CustomPaint(
                  size: const Size.square(180),
                  painter: const SpringboardPainter(),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(20),
              child: DefaultTextStyle.merge(
                style: const TextStyle(color: Colors.white),
                child: IconTheme.merge(
                  data: const IconThemeData(color: Colors.white),
                  child: child,
                ),
              ),
            ),
          ],
        ),
      ),
    );

    return rCard;
  }
}

/// Anneau de l'objectif du jour : il se remplit en ambre à chaque réponse.
class GoalRing extends StatelessWidget {
  const GoalRing({
    super.key,
    required this.done,
    required this.goal,
    this.size = 88,
  });

  final int done;
  final int goal;
  final double size;

  @override
  Widget build(BuildContext context) {
    final vTarget = goal == 0 ? 0.0 : (done / goal).clamp(0, 1).toDouble();
    final rRing = TweenAnimationBuilder<double>(
      tween: Tween(end: vTarget),
      duration: motionOf(context, const Duration(milliseconds: 900)),
      curve: Curves.easeOutBack,
      builder: (_, pValue, __) => SizedBox.square(
        dimension: size,
        child: Stack(
          alignment: Alignment.center,
          children: [
            SizedBox.expand(
              child: CircularProgressIndicator(
                value: pValue.clamp(0, 1),
                strokeWidth: size * 0.1,
                strokeCap: StrokeCap.round,
                color: sunriseColor,
                backgroundColor: Colors.white.withValues(alpha: 0.18),
              ),
            ),
            Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '$done',
                  style: TextStyle(
                    fontSize: size * 0.3,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                  ),
                ),
                Text(
                  'sur $goal',
                  style: TextStyle(fontSize: size * 0.13, color: Colors.white70),
                ),
              ],
            ),
          ],
        ),
      ),
    );

    return rRing;
  }
}

/// Barre de progression qui glisse jusqu'à sa valeur au lieu d'y sauter.
class AnimatedBar extends StatelessWidget {
  const AnimatedBar({super.key, required this.value, this.color});

  final double value;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final rBar = TweenAnimationBuilder<double>(
      tween: Tween(end: value.clamp(0, 1).toDouble()),
      duration: motionOf(context, const Duration(milliseconds: 700)),
      curve: Curves.easeOutCubic,
      builder: (_, pValue, __) => LinearProgressIndicator(
        value: pValue,
        minHeight: 6,
        borderRadius: BorderRadius.circular(3),
        color: color,
      ),
    );

    return rBar;
  }
}
