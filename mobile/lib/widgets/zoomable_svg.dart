// Dessin SVG zoomable au pincement, partagé par les éditeurs de schéma.

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

/// Dessin SVG zoomable, ajusté à la largeur au départ ; pOnTap reçoit les coordonnées du dessin.
class ZoomableSvg extends StatefulWidget {
  const ZoomableSvg({super.key, required this.svg, this.onTap});

  final String svg;
  final void Function(Offset pPosition)? onTap;

  @override
  State<ZoomableSvg> createState() => _ZoomableSvgState();
}

class _ZoomableSvgState extends State<ZoomableSvg> {
  final viewer = TransformationController();
  double? fitted;

  double _size(String pName) =>
      double.parse(RegExp('$pName="([0-9.]+)"').firstMatch(widget.svg)!.group(1)!);

  @override
  void dispose() {
    viewer.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext pContext) {
    final vWidth = _size('width');
    final vHeight = _size('height');

    return LayoutBuilder(builder: (pContext, pConstraints) {
      final vScale = pConstraints.maxWidth / vWidth;

      if (fitted != vScale) {
        fitted = vScale;
        viewer.value = Matrix4.diagonal3Values(vScale, vScale, 1);
      }

      return SizedBox(
        height: vHeight * vScale,
        child: ClipRect(
          child: InteractiveViewer(
            transformationController: viewer,
            constrained: false,
            minScale: vScale,
            maxScale: 3,
            child: GestureDetector(
              onTapUp:
                  widget.onTap == null ? null : (pDetails) => widget.onTap!(pDetails.localPosition),
              child: SvgPicture.string(widget.svg, width: vWidth, height: vHeight),
            ),
          ),
        ),
      );
    });
  }
}
