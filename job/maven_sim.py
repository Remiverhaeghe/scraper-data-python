"""Maven simulé : lecture du pom.xml, résolution des dépendances, cycle de vie

Le projet Java n'existe pas vraiment : chaque niveau décrit ses sources (les
paquets qu'elles importent, les nouveautés de Java qu'elles utilisent) et ses
tests. Le simulateur lit le pom.xml saisi, résout les dépendances dans un
dépôt central réduit, puis déroule les phases comme Maven, avec ses messages.
"""

import re
import xml.etree.ElementTree as ET

MAX_POM_LENGTH = 8000
SEPARATOR = "[INFO] " + "-" * 72
SCOPES = ("compile", "provided", "runtime", "test", "system")
PHASES = ("validate", "compile", "test", "package", "verify", "install")
DEFAULT_RELEASE = 8
DEFAULT_SUREFIRE = "3.2.5"
# Version de surefire à partir de laquelle les tests JUnit 5 sont trouvés
SUREFIRE_JUNIT5 = (2, 22)

# Dépôt central réduit : versions publiées, paquets fournis, dépendances
# transitives et versions minimales attendues à l'exécution
CENTRAL = {
    "org.apache.commons:commons-lang3": {
        "versions": ("3.12.0", "3.14.0"),
        "packages": ("org.apache.commons.lang3",),
    },
    "org.junit.jupiter:junit-jupiter": {
        "versions": ("5.10.2",),
        "packages": ("org.junit.jupiter.api",),
    },
    "junit:junit": {"versions": ("4.13.2",), "packages": ("org.junit",)},
    "com.fasterxml.jackson.core:jackson-databind": {
        "versions": ("2.17.0",),
        "packages": ("com.fasterxml.jackson.databind",),
        "dependencies": (
            ("com.fasterxml.jackson.core:jackson-annotations", "2.17.0"),
            ("com.fasterxml.jackson.core:jackson-core", "2.17.0"),
        ),
        "needs": {"com.fasterxml.jackson.core:jackson-core": (2, 15)},
    },
    "com.fasterxml.jackson.core:jackson-core": {
        "versions": ("2.9.10", "2.17.0"),
        "packages": ("com.fasterxml.jackson.core",),
    },
    "com.fasterxml.jackson.core:jackson-annotations": {
        "versions": ("2.17.0",),
        "packages": ("com.fasterxml.jackson.annotation",),
    },
    "org.slf4j:slf4j-api": {"versions": ("2.0.12",), "packages": ("org.slf4j",)},
    "org.projectlombok:lombok": {"versions": ("1.18.32",), "packages": ("lombok",)},
}
PLUGINS = {
    "org.apache.maven.plugins:maven-surefire-plugin": ("2.12.4", "3.2.5"),
    "org.apache.maven.plugins:maven-compiler-plugin": ("3.13.0",),
    "org.apache.maven.plugins:maven-jar-plugin": ("3.4.1",),
}
# Version minimale de Java de chaque nouveauté du langage
FEATURES = {
    "var": (10, "'var' is not allowed here"),
    "switch_expression": (14, "switch expressions are not supported"),
    "text_block": (15, "text blocks are not supported"),
    "record": (16, "records are not supported"),
}


class PomError(Exception):
    """Erreur de lecture ou de validation du pom.xml, avec les lignes Maven."""

    def __init__(self, pLines):
        """Garde les lignes d'erreur à afficher."""
        super().__init__(pLines[0])
        self.lines = pLines


def parse_version(pText):
    """Retourne une version comparable : (2, 17, 0)."""

    rVersion = tuple(int(vPart) for vPart in re.findall(r"\d+", pText or "")[:3])

    return rVersion


def strip_namespaces(pRoot):
    """Retire l'espace de noms Maven des balises, pour les lire par leur nom."""

    for vElement in pRoot.iter():
        if isinstance(vElement.tag, str) and "}" in vElement.tag:
            vElement.tag = vElement.tag.split("}", 1)[1]


def read_text(pElement, pPath, pProperties=None):
    """Retourne le texte d'une balise, propriétés ${...} remplacées, ou une chaîne vide."""

    vChild = pElement.find(pPath)
    vText = (vChild.text or "").strip() if vChild is not None else ""

    rText = re.sub(
        r"\$\{([\w.-]+)\}",
        lambda pMatch: (pProperties or {}).get(pMatch.group(1), pMatch.group(0)),
        vText,
    )

    return rText


def parse_pom(pText):
    """Retourne le modèle du pom.xml ; lève PomError comme Maven le signalerait."""

    if len(pText) > MAX_POM_LENGTH:
        raise PomError(
            [f"[ERROR] pom.xml trop long : {MAX_POM_LENGTH} caractères au plus."]
        )

    try:
        vRoot = ET.fromstring(pText)

    except ET.ParseError as vError:
        raise PomError(
            [
                "[ERROR] Non-parseable POM pom.xml: "
                f"{vError.msg if hasattr(vError, 'msg') else vError} "
                f"@ line {vError.position[0]}, column {vError.position[1]}",
            ]
        ) from vError

    strip_namespaces(vRoot)

    if vRoot.tag != "project":
        raise PomError(
            ["[ERROR] Non-parseable POM pom.xml: la racine doit être <project>"]
        )

    vProperties = {}
    vPropertiesElement = vRoot.find("properties")

    for vChild in list(vPropertiesElement) if vPropertiesElement is not None else []:
        vProperties[vChild.tag] = (vChild.text or "").strip()

    vModel = {
        vKey: read_text(vRoot, vKey, vProperties)
        for vKey in ("modelVersion", "groupId", "artifactId", "version", "packaging")
    }
    vModel["packaging"] = vModel["packaging"] or "jar"
    vErrors = [
        f"[ERROR]     '{vKey}' is missing. @ line 1"
        for vKey in ("modelVersion", "groupId", "artifactId", "version")
        if not vModel[vKey]
    ]
    vModel["properties"] = vProperties
    vModel["dependencies"] = []

    for vDependency in vRoot.findall("dependencies/dependency"):
        vItem = {
            vKey: read_text(vDependency, vKey, vProperties)
            for vKey in ("groupId", "artifactId", "version", "scope")
        }
        vKey = f"{vItem['groupId']}:{vItem['artifactId']}"
        vItem["key"] = vKey
        vItem["scope"] = vItem["scope"] or "compile"

        if not vItem["version"]:
            vErrors.append(
                f"[ERROR]     'dependencies.dependency.version' for {vKey}:jar is missing."
            )

        if vItem["scope"] not in SCOPES:
            vErrors.append(
                f"[ERROR]     'dependencies.dependency.scope' for {vKey}:jar must be "
                f"one of [{', '.join(SCOPES)}] but is '{vItem['scope']}'."
            )

        vModel["dependencies"].append(vItem)

    vModel["plugins"] = {
        f"{read_text(vPlugin, 'groupId') or 'org.apache.maven.plugins'}:"
        f"{read_text(vPlugin, 'artifactId')}": {
            "version": read_text(vPlugin, "version", vProperties),
            "release": read_text(vPlugin, "configuration/release", vProperties),
        }
        for vPlugin in vRoot.findall("build/plugins/plugin")
    }

    if vErrors:
        raise PomError(
            [
                "[ERROR] [ERROR] Some problems were encountered while processing the POMs:"
            ]
            + vErrors
            + ["[ERROR] The build could not read 1 project -> [Help 1]"]
        )

    return vModel


def get_release(pModel):
    """Retourne la version de Java visée par le compilateur."""

    vCompiler = pModel["plugins"].get(
        "org.apache.maven.plugins:maven-compiler-plugin", {}
    )
    vText = (
        vCompiler.get("release")
        or pModel["properties"].get("maven.compiler.release")
        or pModel["properties"].get("maven.compiler.source")
    )
    vVersion = parse_version(vText)

    if not vVersion:
        return DEFAULT_RELEASE

    rRelease = vVersion[1] if vVersion[0] == 1 and len(vVersion) > 1 else vVersion[0]

    return rRelease


def resolve(pModel):
    """Résout les dépendances : la déclaration la plus proche l'emporte, comme Maven.

    Retourne {clé : (version, scope, parent ou None, versions écartées)} ;
    lève PomError pour un artefact ou une version introuvable.
    """

    rResolved = {}
    vMissing = []

    for vItem in pModel["dependencies"]:
        vEntry = CENTRAL.get(vItem["key"])

        if vEntry is None or vItem["version"] not in vEntry["versions"]:
            vMissing.append(f"{vItem['key']}:jar:{vItem['version']}")
            continue

        rResolved[vItem["key"]] = (vItem["version"], vItem["scope"], None, [])

    if vMissing:
        raise PomError(
            [
                f"[ERROR] Failed to execute goal on project {pModel['artifactId']}: "
                "Could not resolve dependencies",
            ]
            + [
                f"[ERROR]   Could not find artifact {vName} in central "
                "(https://repo.maven.apache.org/maven2)"
                for vName in vMissing
            ]
        )

    for vKey, (_, vScope, _, _) in list(rResolved.items()):
        if vScope == "provided":
            continue

        for vChild, vChildVersion in CENTRAL[vKey].get("dependencies", ()):
            if vChild in rResolved:
                if rResolved[vChild][0] != vChildVersion:
                    rResolved[vChild][3].append((vKey, vChildVersion))
                continue

            rResolved[vChild] = (vChildVersion, vScope, vKey, [])

    return rResolved


def get_packages(pResolved, pScopes):
    """Retourne les paquets fournis par les dépendances des scopes donnés."""

    rPackages = {
        vPackage
        for vKey, (_, vScope, _, _) in pResolved.items()
        if vScope in pScopes
        for vPackage in CENTRAL[vKey]["packages"]
    }

    return rPackages


def check_imports(pFiles, pPackages, pRelease):
    """Retourne les erreurs de compilation de fichiers sources, au format javac."""

    rErrors = []

    for vFile in pFiles:
        for vIndex, vImport in enumerate(vFile.get("imports", []), start=3):
            vPackage = vImport.rsplit(".", 1)[0]

            if vPackage not in pPackages and not vPackage.startswith("java."):
                rErrors.append(
                    f"[ERROR] /{vFile['path']}:[{vIndex},{8 + len(vPackage)}] "
                    f"package {vPackage} does not exist"
                )

        for vFeature in vFile.get("features", []):
            vMinimum, vMessage = FEATURES[vFeature]

            if pRelease < vMinimum:
                rErrors.append(
                    f"[ERROR] /{vFile['path']}:[5,8] {vMessage} in -source {pRelease}"
                )
                rErrors.append(
                    f"[ERROR]   (use -source {vMinimum} or higher to enable it)"
                )

    return rErrors


def find_runtime_errors(pResolved):
    """Retourne l'erreur d'exécution due à une dépendance trop ancienne, ou None."""

    for vKey in pResolved:
        for vNeeded, vMinimum in CENTRAL[vKey].get("needs", {}).items():
            vFound = pResolved.get(vNeeded)

            if vFound and parse_version(vFound[0]) < vMinimum:
                return (
                    "java.lang.NoClassDefFoundError: "
                    "com/fasterxml/jackson/core/exc/StreamConstraintsException",
                    f"{vKey} attend {vNeeded} {'.'.join(map(str, vMinimum))} au moins, "
                    f"mais {vFound[0]} a été retenue.",
                )

    return None


def format_tree(pModel, pResolved):
    """Retourne l'arbre des dépendances, comme mvn dependency:tree."""

    vRoot = [(vKey, vValue) for vKey, vValue in pResolved.items() if vValue[2] is None]
    rLines = [
        f"[INFO] {pModel['groupId']}:{pModel['artifactId']}:jar:{pModel['version']}"
    ]

    for vIndex, (vKey, (vVersion, vScope, _, _)) in enumerate(vRoot):
        vLast = vIndex == len(vRoot) - 1
        vMark = "\\-" if vLast else "+-"
        rLines.append(f"[INFO] {vMark} {vKey}:jar:{vVersion}:{vScope}")
        vChildren = [
            (vChild, vValue)
            for vChild, vValue in pResolved.items()
            if vValue[2] == vKey
        ] + [
            (vChild, None)
            for vChild, vValue in pResolved.items()
            for vParent, _ in vValue[3]
            if vParent == vKey
        ]

        for vChildIndex, (vChild, vValue) in enumerate(vChildren):
            vBranch = "\\-" if vChildIndex == len(vChildren) - 1 else "+-"
            vPrefix = "   " if vLast else "|  "

            if vValue is None:
                vWanted = next(
                    vVersion
                    for vParent, vVersion in pResolved[vChild][3]
                    if vParent == vKey
                )
                rLines.append(
                    f"[INFO] {vPrefix}{vBranch} ({vChild}:jar:{vWanted}:{vScope} - "
                    f"omitted for conflict with {pResolved[vChild][0]})"
                )
            else:
                rLines.append(
                    f"[INFO] {vPrefix}{vBranch} {vChild}:jar:{vValue[0]}:{vValue[1]}"
                )

    return rLines


def parse_command(pCommand):
    """Retourne (phases et buts, sauter les tests) d'une commande mvn ; lève ValueError."""

    vWords = pCommand.split()

    if not vWords or vWords[0] != "mvn":
        raise ValueError("Commande inconnue : seules les commandes mvn sont simulées.")

    vGoals = []
    vSkipTests = False

    for vWord in vWords[1:]:
        if vWord in ("-DskipTests", "-Dmaven.test.skip=true"):
            vSkipTests = True
        elif vWord in ("-q", "-B", "--batch-mode", "-U"):
            continue
        elif vWord in PHASES or vWord in ("clean", "dependency:tree"):
            vGoals.append(vWord)
        else:
            raise ValueError(
                f'Unknown lifecycle phase "{vWord}". Phases simulées : clean, '
                f"{', '.join(PHASES)}, et dependency:tree."
            )

    if not vGoals:
        raise ValueError(
            "No goals have been specified for this build : par exemple mvn package."
        )

    rCommand = (vGoals, vSkipTests)

    return rCommand


def header(pModel):
    """Retourne l'en-tête affiché par Maven avant la construction."""

    vName = f"{pModel['groupId']}:{pModel['artifactId']}"

    rLines = [
        "[INFO] Scanning for projects...",
        f"[INFO] {f'< {vName} >'.center(72, '-')}",
        f"[INFO] Building {pModel['artifactId']} {pModel['version']}",
        f"[INFO] {f'[ {pModel['packaging']} ]'.center(72, '-')}",
    ]

    return rLines


def footer(pSuccess, pErrors=()):
    """Retourne le bilan de fin de construction."""

    rLines = [
        SEPARATOR,
        "[INFO] BUILD SUCCESS" if pSuccess else "[INFO] BUILD FAILURE",
        SEPARATOR,
        *pErrors,
    ]

    return rLines


def run_maven(pProject, pPomText, pCommand):
    """Exécute une commande mvn sur le projet ; retourne (lignes, compte rendu).

    Le compte rendu indique la réussite, la phase atteinte, le nombre de tests
    exécutés, le jar produit et les scopes retenus.
    """

    vReport = {
        "success": False,
        "phase": None,
        "tests_run": 0,
        "skipped_tests": False,
        "jar": None,
        "scopes": {},
    }

    try:
        vGoals, vSkipTests = parse_command(pCommand)

    except ValueError as vError:
        return ([f"[ERROR] {vError}"], vReport)

    try:
        vModel = parse_pom(pPomText)
        vLines = header(vModel)
        vResolved = resolve(vModel)

    except PomError as vError:
        return (["[INFO] Scanning for projects..."] + vError.lines, vReport)

    vReport["scopes"] = {vKey: vValue[1] for vKey, vValue in vResolved.items()}

    if "dependency:tree" in vGoals:
        vLines += ["[INFO] --- dependency:3.6.1:tree (default-cli) ---"]
        vLines += format_tree(vModel, vResolved) + footer(True)
        vReport["success"] = True

        return (vLines, vReport)

    if "clean" in vGoals:
        vLines.append(
            f"[INFO] --- clean:3.2.0:clean (default-clean) @ {vModel['artifactId']} ---"
        )
        vLines.append("[INFO] Deleting target")

    vTarget = max(
        (PHASES.index(vGoal) for vGoal in vGoals if vGoal in PHASES), default=-1
    )
    vArtifact = vModel["artifactId"]
    vRelease = get_release(vModel)

    if vTarget >= PHASES.index("compile"):
        vLines.append(
            f"[INFO] --- compiler:3.13.0:compile (default-compile) @ {vArtifact} ---"
        )
        vErrors = check_imports(
            pProject["sources"],
            get_packages(vResolved, ("compile", "provided", "system")),
            vRelease,
        )

        if vErrors:
            vLines += ["[ERROR] COMPILATION ERROR : "] + vErrors
            vLines += footer(
                False, ["[ERROR] Failed to execute goal compiler:3.13.0:compile"]
            )
            return (vLines, vReport)

        vLines.append(
            f"[INFO] Compiling {len(pProject['sources'])} source files with javac "
            f"[debug release {vRelease}] to target/classes"
        )
        vReport["phase"] = "compile"

    if vTarget >= PHASES.index("test"):
        vLines.append(
            f"[INFO] --- compiler:3.13.0:testCompile (default-testCompile) @ {vArtifact} ---"
        )
        vErrors = check_imports(
            pProject["tests"], get_packages(vResolved, SCOPES), vRelease
        )

        if vErrors:
            vLines += ["[ERROR] COMPILATION ERROR : "] + vErrors
            vLines += footer(
                False, ["[ERROR] Failed to execute goal compiler:3.13.0:testCompile"]
            )
            return (vLines, vReport)

        vSurefire = (
            vModel["plugins"]
            .get("org.apache.maven.plugins:maven-surefire-plugin", {})
            .get("version")
            or DEFAULT_SUREFIRE
        )
        vLines.append(
            f"[INFO] --- surefire:{vSurefire}:test (default-test) @ {vArtifact} ---"
        )
        vCount = sum(vFile.get("count", 0) for vFile in pProject["tests"])

        if vSkipTests:
            vLines.append("[INFO] Tests are skipped.")
            vReport["skipped_tests"] = True
        elif parse_version(vSurefire)[:2] < SUREFIRE_JUNIT5 and any(
            "org.junit.jupiter.api.Test" in vFile.get("imports", [])
            for vFile in pProject["tests"]
        ):
            vLines += [
                "[INFO] -------------------------------------------------------",
                "[INFO]  T E S T S",
                "[INFO] -------------------------------------------------------",
                "[INFO] Tests run: 0, Failures: 0, Errors: 0, Skipped: 0",
            ]
        else:
            vFailure = find_runtime_errors(vResolved)
            vLines += [
                "[INFO] -------------------------------------------------------",
                "[INFO]  T E S T S",
                "[INFO] -------------------------------------------------------",
            ]

            if vFailure:
                vLines += [
                    f"[ERROR] Tests run: {vCount}, Failures: 0, Errors: {vCount}, Skipped: 0",
                    f"[ERROR]   {vFailure[0]}",
                ]
                vLines += footer(
                    False,
                    [
                        "[ERROR] Failed to execute goal surefire: There are test failures.",
                        f"[ERROR] Piste : {vFailure[1]} Voir mvn dependency:tree.",
                    ],
                )
                return (vLines, vReport)

            vLines.append(
                f"[INFO] Tests run: {vCount}, Failures: 0, Errors: 0, Skipped: 0"
            )
            vReport["tests_run"] = vCount

        vReport["phase"] = "test"

    if vTarget >= PHASES.index("package"):
        vJar = f"{vArtifact}-{vModel['version']}.{vModel['packaging']}"
        vLines.append(f"[INFO] --- jar:3.4.1:jar (default-jar) @ {vArtifact} ---")
        vLines.append(f"[INFO] Building jar: target/{vJar}")
        vReport["jar"] = vJar
        vReport["phase"] = "package"

    if vTarget >= PHASES.index("install"):
        vLines.append(
            f"[INFO] Installing target/{vReport['jar']} to ~/.m2/repository/"
            f"{vModel['groupId'].replace('.', '/')}/{vArtifact}/{vModel['version']}"
        )
        vReport["phase"] = "install"

    vLines += footer(True)
    vReport["success"] = True

    return (vLines, vReport)
