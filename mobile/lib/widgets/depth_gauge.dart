// Jauge de profondeur d'un thème : le bord du bassin, avec ses repères 1 m, 2 m et 3 m.

import 'package:flutter/material.dart';

import '../l10n/texts.dart';
import '../logic/dive.dart';
import '../theme.dart';

/// L'eau monte de gauche à droite jusqu'à la profondeur atteinte ; les repères peints sur le
/// bord donnent l'échelle. Une profondeur [before] plus faible reste visible en pointillé clair,
/// pour voir de combien on est descendu.
class DepthGauge extends StatelessWidget {
  const DepthGauge({super.key, required this.depth, this.before, this.height = 18});

  final double depth;
  final double? before;
  final double height;

  @override
  Widget build(BuildContext context) {
    final vText = context.texts;

    final rGauge = Semantics(
      label: vText.diveDepthLabel(formatDepth(depth)),
      child: TweenAnimationBuilder<double>(
        tween: Tween(end: depth.clamp(0, poolDepthMetres).toDouble()),
        duration: motionOf(context, const Duration(milliseconds: 800)),
        curve: Curves.easeOutCubic,
        builder: (pContext, pDepth, _) => CustomPaint(
          size: Size(double.infinity, height + 14),
          painter: _DepthPainter(
            depth: pDepth,
            before: before,
            water: waterColor,
            deep: deepColor,
            edge: Theme.of(pContext).colorScheme.outlineVariant,
            ink: Theme.of(pContext).colorScheme.onSurfaceVariant,
            barHeight: height,
          ),
        ),
      ),
    );

    return rGauge;
  }
}

class _DepthPainter extends CustomPainter {
  _DepthPainter({
    required this.depth,
    required this.before,
    required this.water,
    required this.deep,
    required this.edge,
    required this.ink,
    required this.barHeight,
  });

  final double depth;
  final double? before;
  final Color water;
  final Color deep;
  final Color edge;
  final Color ink;
  final double barHeight;

  @override
  void paint(Canvas pCanvas, Size pSize) {
    final vLane = RRect.fromRectAndRadius(
      Rect.fromLTWH(0, 0, pSize.width, barHeight),
      Radius.circular(barHeight / 2),
    );
    pCanvas.drawRRect(vLane, Paint()..color = edge.withValues(alpha: 0.35));

    final vShare = depth / poolDepthMetres;
    if (vShare > 0) {
      pCanvas.save();
      pCanvas.clipRRect(vLane);
      pCanvas.drawRect(
        Rect.fromLTWH(0, 0, pSize.width * vShare, barHeight),
        Paint()
          ..shader = LinearGradient(colors: [water, deep]).createShader(
            Rect.fromLTWH(0, 0, pSize.width, barHeight),
          ),
      );
      pCanvas.restore();
    }

    final vBefore = before;
    if (vBefore != null && vBefore < depth) {
      final vAt = pSize.width * vBefore / poolDepthMetres;
      final vPaint = Paint()
        ..color = Colors.white.withValues(alpha: 0.9)
        ..strokeWidth = 2;
      for (var vY = 2.0; vY < barHeight - 2; vY += 5) {
        pCanvas.drawLine(Offset(vAt, vY), Offset(vAt, vY + 2.5), vPaint);
      }
    }

    // Repères du bord : un trait et la profondeur écrite dessous
    for (final vMarker in depthMarkers) {
      final vX = pSize.width * vMarker / poolDepthMetres;
      final vTick = Paint()
        ..color = ink.withValues(alpha: 0.6)
        ..strokeWidth = 1.5;
      final vTickX = vX.clamp(1.0, pSize.width - 1).toDouble();
      pCanvas.drawLine(Offset(vTickX, barHeight - 5), Offset(vTickX, barHeight + 2), vTick);
      final vLabel = TextPainter(
        text: TextSpan(
          text: '$vMarker m',
          style: TextStyle(fontSize: 10, color: ink, fontWeight: FontWeight.w600),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      final vLeft = (vX - vLabel.width / 2).clamp(0.0, pSize.width - vLabel.width).toDouble();
      vLabel.paint(pCanvas, Offset(vLeft, barHeight + 2));
    }
  }

  @override
  bool shouldRepaint(_DepthPainter pOld) => pOld.depth != depth || pOld.before != before;
}
