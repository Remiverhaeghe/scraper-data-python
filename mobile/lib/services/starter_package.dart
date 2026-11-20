// Paquet de révision livré avec l'application (assets/revision/depart.json.gz),
// écrit par tools/mobile_package.py : de quoi réviser sans jamais avoir vu le PC.

import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';

const starterPackageAsset = 'assets/revision/depart.json.gz';

/// Retourne le contenu du paquet livré, décompressé, prêt pour RevisionState.
Future<String> loadStarterPackage([AssetBundle? pBundle]) async {
  final vData = await (pBundle ?? rootBundle).load(starterPackageAsset);
  final rContent = utf8.decode(gzip.decode(vData.buffer.asUint8List()));

  return rContent;
}
