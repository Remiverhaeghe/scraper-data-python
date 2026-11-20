// Éléments de l'identité de Tremplin : le livre-tremplin, l'en-tête couleur d'eau
// avec ses vagues, l'anneau de l'objectif du jour, les barres de progression et
// l'éclaboussure d'une bonne réponse.

import 'dart:math';

import 'package:flutter/material.dart';

import '../l10n/texts.dart';
import '../theme.dart';

/// Le livre ouvert qui sert de tremplin, et le nageur qui en saute bras levés.
///
/// [progress], de 0 à 1, fait monter le nageur depuis le livre : la marque le
/// fait sauter à l'ouverture, l'icône le montre en l'air.
class SpringboardPainter extends CustomPainter {
  const SpringboardPainter({this.progress = 1, this.color = Colors.white});

  final double progress;
  final Color color;

  @override
  void paint(Canvas pCanvas, Size pSize) {
    // Dessin sur une grille de 512, comme l'icône
    final vScale = pSize.shortestSide / 512;
    pCanvas.save();
    pCanvas.scale(vScale);

    // Le livre : deux pages blanches bombées, la tranche jaune dessous
    final vPages = Path()
      ..moveTo(60, 380)
      ..quadraticBezierTo(160, 340, 256, 372)
      ..quadraticBezierTo(352, 340, 452, 380)
      ..lineTo(452, 408)
      ..quadraticBezierTo(352, 372, 256, 404)
      ..quadraticBezierTo(160, 372, 60, 408)
      ..close();
    pCanvas.drawPath(vPages, Paint()..color = color);
    final vEdge = Path()
      ..moveTo(60, 408)
      ..quadraticBezierTo(160, 372, 256, 404)
      ..quadraticBezierTo(352, 372, 452, 408)
      ..lineTo(452, 420)
      ..quadraticBezierTo(352, 386, 256, 418)
      ..quadraticBezierTo(160, 386, 60, 420)
      ..close();
    pCanvas.drawPath(vEdge, Paint()..color = boardColor);

    // Le nageur monte au-dessus du livre, en ralentissant comme un vrai saut
    final vLift = Curves.easeOutCubic.transform(progress.clamp(0, 1)) * 60 - 40;
    pCanvas.translate(0, -vLift);
    final vLimb = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    pCanvas.drawLine(const Offset(256, 206), const Offset(256, 282), vLimb..strokeWidth = 40);
    final vLeftLeg = Path()
      ..moveTo(248, 290)
      ..lineTo(222, 326)
      ..lineTo(232, 364);
    final vRightLeg = Path()
      ..moveTo(264, 290)
      ..lineTo(292, 320)
      ..lineTo(318, 338);
    pCanvas.drawPath(vLeftLeg, vLimb..strokeWidth = 26);
    pCanvas.drawPath(vRightLeg, vLimb);
    pCanvas.drawLine(const Offset(240, 216), const Offset(214, 140), vLimb..strokeWidth = 18);
    pCanvas.drawLine(const Offset(272, 216), const Offset(298, 140), vLimb);
    pCanvas.drawCircle(const Offset(256, 178), 24, Paint()..color = color);

    // Traits d'élan jaunes, qui apparaissent quand le saut est lancé
    if (progress > 0.5) {
      final vSpark = Paint()
        ..color = boardColor.withValues(alpha: ((progress - 0.5) * 2).clamp(0, 1))
        ..strokeWidth = 9
        ..strokeCap = StrokeCap.round;
      pCanvas.drawLine(const Offset(150, 340), const Offset(180, 320), vSpark);
      pCanvas.drawLine(const Offset(362, 340), const Offset(332, 320), vSpark);
      pCanvas.drawLine(const Offset(140, 288), const Offset(176, 282), vSpark);
      pCanvas.drawLine(const Offset(372, 288), const Offset(336, 282), vSpark);
    }
    pCanvas.restore();
  }

  @override
  bool shouldRepaint(SpringboardPainter pOld) => pOld.progress != progress || pOld.color != color;
}

/// Le saut depuis le livre, joué une fois à l'apparition.
class SpringboardMark extends StatelessWidget {
  const SpringboardMark({super.key, this.size = 96, this.color = Colors.white});

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final rMark = TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: motionOf(context, const Duration(milliseconds: 1100)),
      curve: Curves.easeOutBack,
      builder: (_, pProgress, __) => CustomPaint(
        size: Size.square(size),
        painter: SpringboardPainter(progress: pProgress, color: color),
      ),
    );

    return rMark;
  }
}

/// Reflets qui ondulent à la surface de l'eau ; [phase] de 0 à 1 fait un tour.
class WavesPainter extends CustomPainter {
  const WavesPainter(this.phase);

  final double phase;

  @override
  void paint(Canvas pCanvas, Size pSize) {
    final vPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeWidth = 2.5;
    for (var vRow = 0; vRow < 4; vRow++) {
      final vY = pSize.height * (0.2 + vRow * 0.22);
      final vShift = (phase + vRow * 0.27) * 2 * pi;
      final vPath = Path();
      for (var vX = 0.0; vX <= pSize.width; vX += 6) {
        final vWave = vY + sin(vX / 28 + vShift) * 4;
        vX == 0 ? vPath.moveTo(vX, vWave) : vPath.lineTo(vX, vWave);
      }
      pCanvas.drawPath(vPath, vPaint..color = Colors.white.withValues(alpha: 0.08 + vRow * 0.02));
    }
  }

  @override
  bool shouldRepaint(WavesPainter pOld) => pOld.phase != phase;
}

/// Carte d'en-tête couleur d'eau, avec des reflets qui ondulent à l'ouverture et le
/// livre-tremplin en filigrane.
class PoolCard extends StatefulWidget {
  const PoolCard({super.key, required this.child});

  final Widget child;

  @override
  State<PoolCard> createState() => _PoolCardState();
}

class _PoolCardState extends State<PoolCard> with SingleTickerProviderStateMixin {
  late final AnimationController waves =
      AnimationController(vsync: this, duration: const Duration(seconds: 6));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Trois passages de vagues à l'ouverture, puis l'eau se calme : pas d'animation
    // sans fin qui use la batterie. Figées si le téléphone réduit les animations.
    if (MediaQuery.maybeDisableAnimationsOf(context) ?? false) {
      waves.stop();
    } else if (!waves.isAnimating && waves.value == 0) {
      waves.repeat(count: 3);
    }
  }

  @override
  void dispose() {
    waves.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final rCard = DecoratedBox(
      decoration: BoxDecoration(
        gradient: poolGradient,
        borderRadius: BorderRadius.circular(24),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: Stack(
          children: [
            Positioned.fill(
              child: RepaintBoundary(
                child: AnimatedBuilder(
                  animation: waves,
                  builder: (_, __) => CustomPaint(painter: WavesPainter(waves.value)),
                ),
              ),
            ),
            const Positioned(
              right: -30,
              bottom: -36,
              child: Opacity(
                opacity: 0.16,
                child: CustomPaint(
                  size: Size.square(190),
                  painter: SpringboardPainter(),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(20),
              child: DefaultTextStyle.merge(
                style: const TextStyle(color: Colors.white),
                child: IconTheme.merge(
                  data: const IconThemeData(color: Colors.white),
                  child: widget.child,
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

/// Éclaboussure d'une bonne réponse : des ronds qui s'élargissent dans l'eau
/// autour de [child], et quelques gouttes qui sautent.
class SplashRings extends StatelessWidget {
  const SplashRings({super.key, required this.child, this.color = waterColor, this.size = 56});

  final Widget child;
  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    final rSplash = TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: motionOf(context, const Duration(milliseconds: 900)),
      curve: Curves.easeOutCubic,
      builder: (_, pValue, pChild) => SizedBox.square(
        dimension: size,
        child: CustomPaint(
          painter: _SplashPainter(pValue, color),
          child: Center(child: pChild),
        ),
      ),
      child: child,
    );

    return rSplash;
  }
}

class _SplashPainter extends CustomPainter {
  const _SplashPainter(this.progress, this.color);

  final double progress;
  final Color color;

  @override
  void paint(Canvas pCanvas, Size pSize) {
    if (progress >= 1) {
      return;
    }
    final vCentre = pSize.center(Offset.zero);
    final vMax = pSize.shortestSide / 2;
    for (final vDelay in [0.0, 0.25]) {
      final vT = ((progress - vDelay) / (1 - vDelay)).clamp(0.0, 1.0);
      if (vT > 0) {
        pCanvas.drawCircle(
          vCentre,
          vMax * (0.35 + 0.65 * vT),
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = 3 * (1 - vT) + 0.5
            ..color = color.withValues(alpha: 1 - vT),
        );
      }
    }
    // Gouttes : elles montent puis retombent, en parabole
    final vDrop = Paint()..color = color.withValues(alpha: 1 - progress);
    for (var vIndex = 0; vIndex < 5; vIndex++) {
      final vAngle = -pi / 2 + (vIndex - 2) * 0.45;
      final vDistance = vMax * 1.1 * progress;
      final vFall = vMax * 0.9 * progress * progress;
      pCanvas.drawCircle(
        vCentre + Offset(cos(vAngle) * vDistance, sin(vAngle) * vDistance + vFall),
        2.5,
        vDrop,
      );
    }
  }

  @override
  bool shouldRepaint(_SplashPainter pOld) => pOld.progress != progress;
}

/// Anneau de l'objectif du jour : il se remplit en jaune plongeoir à chaque réponse.
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
                color: boardColor,
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
                  context.texts.brandSur('${goal}'),
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
