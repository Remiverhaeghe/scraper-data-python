"""Lecteur XML réduit, pour le pom.xml du simulateur Maven

Il comprend ce qu'écrit un pom.xml : déclaration, commentaires, éléments,
attributs, texte, entités prédéfinies et numériques, sections CDATA. Le
DOCTYPE et les entités déclarées sont refusés. L'application mobile en a une
copie en Dart, même algorithme et mêmes messages : une erreur de saisie y est
signalée exactement comme sur le PC.
"""

import re

NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_.:-]*")
ENTITIES = {"lt": "<", "gt": ">", "amp": "&", "quot": '"', "apos": "'"}
SPACES = " \t\r\n"
MAX_CODE_POINT = 0x10FFFF


class XmlError(Exception):
    """Erreur de lecture, avec la ligne et la colonne où elle se produit."""


class Element:
    """Élément lu : nom sans préfixe d'espace de noms, enfants, texte direct."""

    def __init__(self, pTag):
        """Crée un élément vide."""
        self.tag = pTag
        self.children = []
        self.text = ""

    def find(self, pPath):
        """Retourne le premier élément au bout du chemin a/b, ou None."""

        rElement = self

        for vName in pPath.split("/"):
            rElement = next(
                (vChild for vChild in rElement.children if vChild.tag == vName), None
            )

            if rElement is None:
                return None

        return rElement

    def findall(self, pPath):
        """Retourne tous les éléments au bout du chemin a/b."""

        vParent, _, vName = pPath.rpartition("/")
        vElement = self.find(vParent) if vParent else self

        rElements = (
            [vChild for vChild in vElement.children if vChild.tag == vName]
            if vElement is not None
            else []
        )

        return rElements


class Reader:
    """Lecture d'un document, caractère par caractère."""

    def __init__(self, pText):
        """Prépare la lecture depuis le début du texte."""
        self.text = pText
        self.position = 0

    def fail(self, pReason, pPosition=None):
        """Lève une erreur placée à la position donnée, la position courante sinon."""

        vPosition = self.position if pPosition is None else pPosition
        vLine = self.text.count("\n", 0, vPosition) + 1
        vColumn = vPosition - (self.text.rfind("\n", 0, vPosition) + 1) + 1

        raise XmlError(f"{pReason} (ligne {vLine}, colonne {vColumn})")

    def starts(self, pPrefix):
        """Indique si le texte continue par pPrefix."""

        return self.text.startswith(pPrefix, self.position)

    def skip_spaces(self):
        """Avance après les blancs."""

        while self.position < len(self.text) and self.text[self.position] in SPACES:
            self.position += 1

    def skip_until(self, pEnd, pReason):
        """Avance après la prochaine occurrence de pEnd ; erreur si elle manque."""

        vEnd = self.text.find(pEnd, self.position)

        if vEnd < 0:
            self.fail(pReason)

        self.position = vEnd + len(pEnd)

    def skip_misc(self):
        """Avance après les blancs, commentaires et instructions ; refuse le DOCTYPE."""

        while True:
            self.skip_spaces()

            if self.starts("<!--"):
                self.skip_until("-->", "commentaire non fermé")
            elif self.starts("<?"):
                self.skip_until("?>", "instruction non fermée")
            elif self.starts("<!DOCTYPE"):
                self.fail("DOCTYPE non pris en charge")
            else:
                return

    def read_name(self):
        """Lit un nom de balise ou d'attribut."""

        vMatch = NAME_PATTERN.match(self.text, self.position)

        if vMatch is None:
            self.fail("nom de balise attendu")

        self.position = vMatch.end()

        return vMatch.group()

    def decode(self, pText, pStart):
        """Remplace les entités d'un texte ; pStart sert à placer une erreur."""

        vParts = []
        vIndex = 0

        while True:
            vAmpersand = pText.find("&", vIndex)

            if vAmpersand < 0:
                vParts.append(pText[vIndex:])
                return "".join(vParts)

            vParts.append(pText[vIndex:vAmpersand])
            vEnd = pText.find(";", vAmpersand)
            vName = pText[vAmpersand + 1 : vEnd] if vEnd > 0 else ""

            vCode = None

            if re.fullmatch(r"#[0-9]{1,7}", vName):
                vCode = int(vName[1:])
            elif re.fullmatch(r"#x[0-9A-Fa-f]{1,6}", vName):
                vCode = int(vName[2:], 16)

            if vName in ENTITIES:
                vParts.append(ENTITIES[vName])
            elif vCode is not None and vCode <= MAX_CODE_POINT:
                vParts.append(chr(vCode))
            else:
                self.fail("entité inconnue", pStart + vAmpersand)

            vIndex = vEnd + 1

    def read_attributes(self):
        """Avance après les attributs ; retourne True si la balise se ferme seule."""

        while True:
            self.skip_spaces()

            if self.starts("/>"):
                self.position += 2
                return True

            if self.starts(">"):
                self.position += 1
                return False

            if self.position >= len(self.text):
                self.fail("balise non terminée")

            self.read_name()
            self.skip_spaces()

            if not self.starts("="):
                self.fail("« = » attendu après le nom de l'attribut")

            self.position += 1
            self.skip_spaces()
            vQuote = self.text[self.position : self.position + 1]

            if vQuote not in ('"', "'"):
                self.fail("valeur d'attribut entre guillemets attendue")

            self.position += 1
            self.skip_until(vQuote, "valeur d'attribut non fermée")

    def read_element(self):
        """Lit un élément complet à partir de son « < »."""

        vStart = self.position
        self.position += 1
        vName = self.read_name()
        rElement = Element(vName.rpartition(":")[2])

        if self.read_attributes():
            return rElement

        while True:
            if self.position >= len(self.text):
                self.fail(f"balise <{vName}> non fermée", vStart)

            if self.starts("</"):
                vClosing = self.position
                self.position += 2
                vEndName = self.read_name()
                self.skip_spaces()

                if not self.starts(">"):
                    self.fail("« > » attendu")

                self.position += 1

                if vEndName != vName:
                    self.fail(f"balise </{vEndName}> au lieu de </{vName}>", vClosing)

                return rElement

            if self.starts("<!--"):
                self.skip_until("-->", "commentaire non fermé")
            elif self.starts("<![CDATA["):
                vEnd = self.text.find("]]>", self.position)

                if vEnd < 0:
                    self.fail("section CDATA non fermée")

                rElement.text += self.text[self.position + 9 : vEnd]
                self.position = vEnd + 3
            elif self.starts("<?"):
                self.skip_until("?>", "instruction non fermée")
            elif self.starts("<"):
                rElement.children.append(self.read_element())
            else:
                vEnd = self.text.find("<", self.position)
                vEnd = len(self.text) if vEnd < 0 else vEnd
                rElement.text += self.decode(
                    self.text[self.position : vEnd], self.position
                )
                self.position = vEnd


def parse(pText):
    """Retourne l'élément racine d'un document ; lève XmlError s'il est mal formé."""

    vReader = Reader(pText.lstrip("﻿"))
    vReader.skip_misc()

    if vReader.position >= len(vReader.text):
        vReader.fail("document vide")

    if not vReader.starts("<"):
        vReader.fail("« < » attendu au début de l'élément racine")

    rRoot = vReader.read_element()
    vReader.skip_misc()

    if vReader.position < len(vReader.text):
        vReader.fail("contenu après l'élément racine")

    return rRoot
