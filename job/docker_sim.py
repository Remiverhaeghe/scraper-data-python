"""Docker simulé : Dockerfile, images, conteneurs, ports, volumes, et curl

Rien n'est transmis au système : un hôte Docker est représenté par un
dictionnaire (images, conteneurs, volumes) que chaque commande fait évoluer.
L'application à conteneuriser est décrite par le niveau : jar Java ou script
Python, port écouté, variables obligatoires, dossier de données. Au lancement,
le simulateur vérifie ce que ferait vraiment l'application, et curl permet
d'aller voir si le service répond.
"""

import fnmatch
import json
import posixpath
import re
import shlex

MAX_DOCKERFILE_LENGTH = 4000
MAX_CONTAINERS = 20
INSTRUCTIONS = (
    "FROM",
    "WORKDIR",
    "COPY",
    "ADD",
    "RUN",
    "ENV",
    "EXPOSE",
    "CMD",
    "ENTRYPOINT",
    "USER",
    "ARG",
    "LABEL",
)
# Images publiques simulées : version de Java, outils présents, service fourni
REGISTRY = {
    "eclipse-temurin:21-jre": {"java": 21, "tools": ("java",)},
    "eclipse-temurin:17-jre": {"java": 17, "tools": ("java",)},
    "eclipse-temurin:21-jdk": {"java": 21, "tools": ("java", "javac")},
    "python:3.12-slim": {"tools": ("python", "pip")},
    "nginx:1.27": {"tools": (), "cmd": ["nginx", "-g", "daemon off;"], "port": 80},
    "alpine:3.20": {"tools": ()},
}
SHELL_TOOLS = ("sh", "mkdir", "echo", "ls", "cp", "chmod", "rm", "cat", "true")
# Version du format de classe Java, affichée par UnsupportedClassVersionError
CLASS_VERSIONS = {17: 61, 21: 65}
PORT_PATTERN = re.compile(r"(\d{1,5}):(\d{1,5})")
URL_PATTERN = re.compile(
    r"(?:https?://)?(?:localhost|127\.0\.0\.1):(\d{1,5})(/[\w/-]*)?"
)


class DockerError(Exception):
    """Erreur d'une commande Docker simulée, avec le message affiché."""


def new_host(pSetup=()):
    """Retourne un hôte vide, avec les conteneurs déjà présents du niveau."""

    rHost = {
        "images": {},
        "containers": [],
        "volumes": {},
        "events": [],
        "sequence": 0,
    }

    for vItem in pSetup:
        vImage = vItem["image"]
        rHost["images"][vImage] = {"base": vImage, **build_base(vImage)}
        start_container(
            rHost,
            create_container(
                rHost, vImage, vItem["name"], vItem.get("ports", []), [], {}
            ),
            None,
        )

    return rHost


def build_base(pImage):
    """Retourne le contenu d'une image publique : dossier, fichiers, commande."""

    rSpec = {
        "workdir": "/",
        "files": {},
        "env": {},
        "expose": [],
        "cmd": list(REGISTRY[pImage].get("cmd", [])),
        "entrypoint": [],
        "requirements": False,
    }

    return rSpec


def join_lines(pText):
    """Retourne les instructions du Dockerfile : (numéro de ligne, mot-clé, arguments)."""

    rInstructions = []
    vBuffer = ""
    vStart = 0

    for vNumber, vLine in enumerate(pText.splitlines(), start=1):
        vStripped = vLine.strip()

        if not vBuffer and (not vStripped or vStripped.startswith("#")):
            continue

        if not vBuffer:
            vStart = vNumber

        if vStripped.endswith("\\"):
            vBuffer += vStripped[:-1] + " "
            continue

        vBuffer += vStripped
        vKeyword, _, vArguments = vBuffer.partition(" ")
        rInstructions.append((vStart, vKeyword.upper(), vArguments.strip()))
        vBuffer = ""

    if vBuffer:
        vKeyword, _, vArguments = vBuffer.partition(" ")
        rInstructions.append((vStart, vKeyword.upper(), vArguments.strip()))

    return rInstructions


def read_command(pArguments):
    """Retourne une commande CMD ou ENTRYPOINT : forme JSON, sinon forme shell."""

    if pArguments.startswith("["):
        try:
            vCommand = json.loads(pArguments)

        except ValueError as vError:
            raise DockerError(
                f"forme JSON invalide : {pArguments} (guillemets doubles obligatoires)"
            ) from vError

        if not isinstance(vCommand, list) or not all(
            isinstance(vWord, str) for vWord in vCommand
        ):
            raise DockerError(f"forme JSON invalide : {pArguments}")

        return vCommand

    rCommand = ["/bin/sh", "-c", pArguments]

    return rCommand


def resolve_path(pWorkdir, pPath):
    """Retourne un chemin absolu dans l'image, relatif au dossier de travail."""

    rPath = posixpath.normpath(posixpath.join(pWorkdir, pPath))

    return rPath


def copy_files(pSpec, pContext, pArguments, pLine):
    """Copie des fichiers du contexte de construction dans l'image."""

    vWords = pArguments.split()

    if len(vWords) < 2:
        raise DockerError(
            f"dockerfile parse error on line {pLine}: COPY requires at least two arguments"
        )

    vSources, vDestination = vWords[:-1], vWords[-1]
    vMatched = []

    for vSource in vSources:
        vSource = vSource.removeprefix("./") if vSource not in (".", "./") else "."

        if vSource == ".":
            vFiles = [(vPath, vPath) for vPath in pContext]
        else:
            vFiles = [
                (vPath, posixpath.basename(vPath))
                for vPath in pContext
                if fnmatch.fnmatch(vPath, vSource)
            ] + [
                (vPath, vPath[len(vSource) :].lstrip("/"))
                for vPath in pContext
                if vPath.startswith(vSource.rstrip("/") + "/")
            ]

        if not vFiles:
            raise DockerError(
                f'failed to compute cache key: "/{vSource}": not found '
                f"(ligne {pLine} : ce fichier n'est pas dans le contexte de construction)"
            )

        vMatched += vFiles

    vTarget = resolve_path(pSpec["workdir"], vDestination)
    vIsFolder = (
        vDestination.endswith("/")
        or vDestination in (".", "./")
        or len(vMatched) > 1
        or vSources[0] in (".", "./")
    )

    for vContextPath, vName in vMatched:
        vPath = posixpath.join(vTarget, vName) if vIsFolder else vTarget
        pSpec["files"][vPath] = vContextPath


def run_instruction(pSpec, pArguments, pLine, pTools):
    """Exécute un RUN pendant la construction ; lève DockerError en cas d'échec."""

    vWords = pArguments.split()
    vTool = vWords[0] if vWords else ""

    if vTool not in pTools and vTool not in SHELL_TOOLS:
        raise DockerError(
            f'process "/bin/sh -c {pArguments}" did not complete successfully: '
            f"exit code: 127 (/bin/sh: 1: {vTool}: not found, ligne {pLine})"
        )

    if vTool == "pip" and "-r" in vWords:
        vIndex = vWords.index("-r") + 1
        vFile = resolve_path(
            pSpec["workdir"], vWords[vIndex] if vIndex < len(vWords) else ""
        )

        if vFile not in pSpec["files"]:
            raise DockerError(
                f'process "/bin/sh -c {pArguments}" did not complete successfully: '
                "exit code: 1 (ERROR: Could not open requirements file: "
                f"No such file or directory: '{vWords[vIndex] if vIndex < len(vWords) else ''}')"
            )

        pSpec["requirements"] = True


def build_image(pDockerfile, pContext):
    """Construit une image depuis le Dockerfile ; retourne (lignes, spécification)."""

    if len(pDockerfile) > MAX_DOCKERFILE_LENGTH:
        raise DockerError(
            f"Dockerfile trop long : {MAX_DOCKERFILE_LENGTH} caractères au plus."
        )

    vInstructions = join_lines(pDockerfile)

    if not vInstructions or vInstructions[0][1] not in ("FROM", "ARG"):
        raise DockerError(
            "dockerfile parse error : no build stage in current context (FROM manquant)"
        )

    vSpec = None
    vTools = ()
    rLines = []

    for vIndex, (vLine, vKeyword, vArguments) in enumerate(vInstructions, start=1):
        if vKeyword not in INSTRUCTIONS:
            raise DockerError(
                f"dockerfile parse error on line {vLine}: unknown instruction: {vKeyword}"
            )

        rLines.append(f" => [{vIndex}/{len(vInstructions)}] {vKeyword} {vArguments}")

        if vKeyword == "FROM":
            vImage = vArguments.split()[0] if vArguments else ""
            vImage = vImage if ":" in vImage else f"{vImage}:latest"

            if vImage not in REGISTRY:
                raise DockerError(
                    f"failed to resolve source metadata for docker.io/library/{vImage}: "
                    "not found (images simulées : " + ", ".join(REGISTRY) + ")"
                )

            vSpec = {"base": vImage, **build_base(vImage)}
            vTools = REGISTRY[vImage]["tools"]
        elif vSpec is None:
            continue
        elif vKeyword == "WORKDIR":
            vSpec["workdir"] = resolve_path(vSpec["workdir"], vArguments)
        elif vKeyword in ("COPY", "ADD"):
            copy_files(vSpec, pContext, vArguments, vLine)
        elif vKeyword == "RUN":
            run_instruction(vSpec, vArguments, vLine, vTools)
        elif vKeyword == "ENV":
            vName, vSeparator, vValue = vArguments.partition("=")

            if not vSeparator:
                vName, _, vValue = vArguments.partition(" ")

            vSpec["env"][vName.strip()] = vValue.strip().strip('"')
        elif vKeyword == "EXPOSE":
            vSpec["expose"] = [
                int(vPort.split("/")[0])
                for vPort in vArguments.split()
                if vPort.split("/")[0].isdigit()
            ]
        elif vKeyword == "CMD":
            vSpec["cmd"] = read_command(vArguments)
        elif vKeyword == "ENTRYPOINT":
            vSpec["entrypoint"] = read_command(vArguments)

    if vSpec is None:
        raise DockerError(
            "dockerfile parse error : no build stage in current context (FROM manquant)"
        )

    rBuild = (rLines, vSpec)

    return rBuild


def find_container(pHost, pName):
    """Retourne un conteneur par nom ou par début d'identifiant ; lève DockerError."""

    for vContainer in pHost["containers"]:
        if pName and (
            vContainer["name"] == pName or vContainer["id"].startswith(pName)
        ):
            return vContainer

    raise DockerError(f"Error response from daemon: No such container: {pName}")


def create_container(pHost, pImage, pName, pPorts, pVolumes, pEnv):
    """Crée un conteneur arrêté ; lève DockerError si le nom est déjà pris."""

    if len(pHost["containers"]) >= MAX_CONTAINERS:
        raise DockerError(
            f"{MAX_CONTAINERS} conteneurs au plus : supprimez-en avec docker rm."
        )

    pHost["sequence"] += 1
    vName = pName or f"conteneur_{pHost['sequence']}"

    if any(vContainer["name"] == vName for vContainer in pHost["containers"]):
        raise DockerError(
            f'Error response from daemon: Conflict. The container name "/{vName}" is '
            "already in use. You have to remove (or rename) that container to be able "
            "to reuse that name."
        )

    rContainer = {
        "id": f"{pHost['sequence'] * 7919:012x}",
        "name": vName,
        "image": pImage,
        "ports": [list(vPort) for vPort in pPorts],
        "volumes": [list(vVolume) for vVolume in pVolumes],
        "env": dict(pEnv),
        "status": "created",
        "logs": [],
        "records": 0,
        "listen": None,
    }
    pHost["containers"].append(rContainer)

    for vSource, _ in pVolumes:
        pHost["volumes"].setdefault(vSource, {"records": 0, "writer": None})

    return rContainer


def get_used_ports(pHost, pExcept=None):
    """Retourne les ports de l'hôte publiés par les conteneurs en marche."""

    rPorts = {
        vHostPort: vContainer["name"]
        for vContainer in pHost["containers"]
        if vContainer["status"] == "running" and vContainer is not pExcept
        for vHostPort, _ in vContainer["ports"]
    }

    return rPorts


def start_process(pImage, pContainer, pApp):
    """Retourne (en marche, journaux, port écouté) du processus du conteneur."""

    vCommand = pImage["entrypoint"] + (pContainer.get("command") or pImage["cmd"])
    vEnv = {**pImage["env"], **pContainer["env"]}
    vBase = REGISTRY[pImage["base"]]

    if not vCommand:
        return (
            False,
            ["docker: Error response from daemon: no command specified."],
            None,
        )

    if vCommand[:2] == ["/bin/sh", "-c"]:
        vCommand = vCommand[2].split()

    if vCommand[0] == "nginx":
        return (True, ["nginx: start worker processes"], 80)

    if vCommand[0] == "java":
        if "java" not in vBase["tools"]:
            return (False, ["/bin/sh: 1: java: not found"], None)

        vJar = vCommand[vCommand.index("-jar") + 1] if "-jar" in vCommand[:-1] else ""
        vPath = resolve_path(pImage["workdir"], vJar)

        if not vJar or vPath not in pImage["files"]:
            return (
                False,
                [f"Error: Unable to access jarfile {vJar or '(aucun)'}"],
                None,
            )

        if pApp.get("java_min", 0) > vBase["java"]:
            return (
                False,
                [
                    "Error: LinkageError occurred while loading main class "
                    "fr.atelier.Application",
                    "java.lang.UnsupportedClassVersionError: compiled by a more recent "
                    f"version of the Java Runtime (class file version "
                    f"{CLASS_VERSIONS[pApp['java_min']]}.0), this version of the Java "
                    "Runtime only recognizes class file versions up to "
                    f"{CLASS_VERSIONS[vBase['java']]}.0",
                ],
                None,
            )
    elif vCommand[0] in ("python", "python3"):
        if "python" not in vBase["tools"]:
            return (False, [f"/bin/sh: 1: {vCommand[0]}: not found"], None)

        vScript = resolve_path(
            pImage["workdir"], vCommand[1] if len(vCommand) > 1 else ""
        )

        if vScript not in pImage["files"]:
            return (
                False,
                [
                    f"python: can't open file '{vScript}': [Errno 2] No such file or directory"
                ],
                None,
            )

        if pApp.get("requirements") and not pImage["requirements"]:
            return (
                False,
                [
                    "Traceback (most recent call last):",
                    f'  File "{vScript}", line 1, in <module>',
                    "ModuleNotFoundError: No module named 'flask'",
                ],
                None,
            )
    else:
        return (False, [], None)

    vMissing = [vName for vName in pApp.get("env_required", []) if not vEnv.get(vName)]

    if vMissing:
        return (
            False,
            [
                "APPLICATION FAILED TO START",
                f"Description: la variable d'environnement {vMissing[0]} est absente : "
                "impossible de joindre la base de données.",
            ],
            None,
        )

    vPort = (
        int(vEnv.get("SERVER_PORT", pApp["port"]))
        if str(vEnv.get("SERVER_PORT", pApp["port"])).isdigit()
        else pApp["port"]
    )
    vLogs = (
        [f"Tomcat started on port {vPort} (http)", "Started Application in 2.1 seconds"]
        if vCommand[0] == "java"
        else [f" * Running on http://0.0.0.0:{vPort}"]
    )

    rProcess = (True, vLogs, vPort)

    return rProcess


def start_container(pHost, pContainer, pApp):
    """Démarre un conteneur : ports libres, puis processus ; retourne les lignes."""

    vUsed = get_used_ports(pHost, pContainer)

    for vHostPort, _ in pContainer["ports"]:
        if vHostPort in vUsed:
            raise DockerError(
                "Error response from daemon: driver failed programming external "
                f"connectivity on endpoint {pContainer['name']}: Bind for "
                f"0.0.0.0:{vHostPort} failed: port is already allocated "
                f"(utilisé par {vUsed[vHostPort]})"
            )

    vImage = pHost["images"][pContainer["image"]]
    vRunning, vLogs, vPort = start_process(vImage, pContainer, pApp or {})
    pContainer["logs"] += vLogs
    pContainer["status"] = "running" if vRunning else "exited (1)"
    pContainer["listen"] = vPort

    rLines = [pContainer["id"]]

    return rLines


def parse_run(pWords):
    """Retourne les options de docker run : nom, ports, volumes, env, image, commande."""

    rOptions = {
        "name": None,
        "ports": [],
        "volumes": [],
        "env": {},
        "image": None,
        "command": [],
    }
    vIndex = 0

    while vIndex < len(pWords):
        vWord = pWords[vIndex]

        if rOptions["image"] is not None:
            rOptions["command"].append(vWord)
        elif vWord in ("-d", "--detach", "--rm", "-it", "-i", "-t"):
            pass
        elif vWord in ("--name", "-p", "--publish", "-v", "--volume", "-e", "--env"):
            vIndex += 1

            if vIndex >= len(pWords):
                raise DockerError(f"flag needs an argument: {vWord}")

            vValue = pWords[vIndex]

            if vWord == "--name":
                rOptions["name"] = vValue
            elif vWord in ("-p", "--publish"):
                vMatch = PORT_PATTERN.fullmatch(vValue)

                if not vMatch:
                    raise DockerError(
                        f'invalid argument "{vValue}" for "-p" : '
                        "écrivez -p PORT_HÔTE:PORT_CONTENEUR"
                    )

                rOptions["ports"].append((int(vMatch.group(1)), int(vMatch.group(2))))
            elif vWord in ("-v", "--volume"):
                vSource, vSeparator, vTarget = vValue.partition(":")

                if not vSeparator or not vTarget.startswith("/"):
                    raise DockerError(
                        f"invalid volume specification: '{vValue}' : écrivez -v VOLUME:/chemin"
                    )

                rOptions["volumes"].append((vSource, vTarget.rstrip("/") or "/"))
            else:
                vName, _, vSetting = vValue.partition("=")
                rOptions["env"][vName] = vSetting
        elif vWord.startswith("-"):
            raise DockerError(f"unknown flag: {vWord}")
        else:
            rOptions["image"] = vWord

        vIndex += 1

    if rOptions["image"] is None:
        raise DockerError(
            '"docker run" requires at least 1 argument : l\'image à lancer.'
        )

    return rOptions


def get_image_name(pName):
    """Retourne le nom complet d'une image, avec latest par défaut."""

    rName = pName if ":" in pName else f"{pName}:latest"

    return rName


def format_ports(pContainer):
    """Retourne les ports publiés d'un conteneur, comme docker ps."""

    if pContainer["status"] != "running":
        return ""

    rText = ", ".join(
        f"0.0.0.0:{vHostPort}->{vContainerPort}/tcp"
        for vHostPort, vContainerPort in pContainer["ports"]
    )

    return rText


def list_containers(pHost, pAll):
    """Retourne le tableau de docker ps."""

    rLines = [f"{'CONTAINER ID':<14}{'IMAGE':<26}{'STATUS':<14}{'PORTS':<28}NAMES"]

    for vContainer in pHost["containers"]:
        if pAll or vContainer["status"] == "running":
            rLines.append(
                f"{vContainer['id']:<14}{vContainer['image']:<26}"
                f"{vContainer['status']:<14}{format_ports(vContainer):<28}"
                f"{vContainer['name']}"
            )

    return rLines


def get_data_target(pHost, pContainer, pApp):
    """Retourne où l'application écrit ses données : un volume, ou le conteneur."""

    for vSource, vTarget in pContainer["volumes"]:
        if vTarget == pApp.get("data_dir"):
            return pHost["volumes"][vSource]

    rTarget = pContainer

    return rTarget


def run_curl(pHost, pWords, pApp):
    """Interroge un port de l'hôte comme curl ; note la réponse pour les objectifs."""

    vMethod = "GET"
    vUrl = None
    vIndex = 0

    while vIndex < len(pWords):
        if pWords[vIndex] == "-X" and vIndex + 1 < len(pWords):
            vMethod = pWords[vIndex + 1].upper()
            vIndex += 1
        elif not pWords[vIndex].startswith("-"):
            vUrl = pWords[vIndex]

        vIndex += 1

    vMatch = URL_PATTERN.fullmatch(vUrl or "")

    if not vMatch:
        raise DockerError("curl : écrivez par exemple curl http://localhost:8080/")

    vPort = int(vMatch.group(1))
    vPath = vMatch.group(2) or "/"
    vContainer = next(
        (
            vItem
            for vItem in pHost["containers"]
            if vItem["status"] == "running"
            and any(vHostPort == vPort for vHostPort, _ in vItem["ports"])
        ),
        None,
    )

    if vContainer is None:
        return [
            f"curl: (7) Failed to connect to localhost port {vPort}: Connection refused"
        ]

    vInside = next(
        vTarget for vHostPort, vTarget in vContainer["ports"] if vHostPort == vPort
    )

    if vInside != vContainer["listen"]:
        return ["curl: (56) Recv failure: Connection reset by peer"]

    vRunning = [
        vItem["name"] for vItem in pHost["containers"] if vItem["status"] == "running"
    ]

    if vContainer["listen"] == 80 and vContainer["image"].startswith("nginx"):
        return ["<h1>Ancien site de l'atelier</h1>"]

    if vPath == "/mesures" and pApp.get("data_dir"):
        vTarget = get_data_target(pHost, vContainer, pApp)

        if vMethod == "POST":
            vTarget["records"] += 1
            vTarget["writer"] = vContainer["id"]

            return [json.dumps({"enregistrees": vTarget["records"]})]

        pHost["events"].append(
            {
                "kind": "read",
                "records": vTarget["records"],
                "other": vTarget.get("writer") not in (None, vContainer["id"]),
                "running": vRunning,
            }
        )

        return [json.dumps({"mesures": vTarget["records"]})]

    pHost["events"].append(
        {
            "kind": "reach",
            "port": vPort,
            "image": vContainer["image"],
            "running": vRunning,
        }
    )

    rLines = [json.dumps({"application": pApp.get("name", "atelier"), "statut": "ok"})]

    return rLines


def run_docker(pHost, pLevel, pDockerfile, pCommand):
    """Exécute une commande sur l'hôte simulé ; retourne les lignes affichées.

    L'hôte est modifié sur place. Lève DockerError pour une commande refusée,
    avec le message qu'afficherait Docker.
    """

    try:
        vWords = shlex.split(pCommand)

    except ValueError as vError:
        raise DockerError(f"commande illisible : {vError}") from vError

    vApp = pLevel.get("app", {})

    if vWords[:1] == ["curl"]:
        return run_curl(pHost, vWords[1:], vApp)

    if vWords[:1] != ["docker"] or len(vWords) < 2:
        raise DockerError(
            "Commandes simulées : docker … et curl http://localhost:PORT/"
        )

    vVerb, vRest = vWords[1], vWords[2:]

    if vVerb == "build":
        vTag = None

        for vIndex, vWord in enumerate(vRest):
            if vWord in ("-t", "--tag") and vIndex + 1 < len(vRest):
                vTag = get_image_name(vRest[vIndex + 1])

        if not vRest or vRest[-1] not in (".", "./"):
            raise DockerError(
                '"docker build" requires exactly 1 argument : le contexte, souvent « . »'
            )

        vLines, vSpec = build_image(pDockerfile, pLevel.get("context", []))
        vName = vTag or "<none>:<none>"
        pHost["images"][vName] = vSpec
        pHost["events"].append({"kind": "build", "image": vName})

        return (
            vLines
            + [f" => naming to docker.io/library/{vName}", " => DONE"]
            + (
                []
                if vTag
                else ["Astuce : sans -t, l'image n'a pas de nom pour docker run."]
            )
        )

    if vVerb == "images":
        return [f"{'REPOSITORY':<24}{'TAG':<12}IMAGE ID"] + [
            f"{vName.split(':')[0]:<24}{vName.split(':')[1]:<12}{vIndex * 48271:012x}"
            for vIndex, vName in enumerate(pHost["images"], start=1)
        ]

    if vVerb == "pull":
        vName = get_image_name(vRest[0]) if vRest else ""

        if vName not in REGISTRY:
            raise DockerError(
                f"pull access denied for {vName or '(rien)'}, repository does not exist"
            )

        pHost["images"][vName] = {"base": vName, **build_base(vName)}

        return [f"Status: Downloaded newer image for {vName}"]

    if vVerb == "run":
        vOptions = parse_run(vRest)
        vImage = get_image_name(vOptions["image"])

        if vImage not in pHost["images"]:
            if vImage not in REGISTRY:
                raise DockerError(
                    f"Unable to find image '{vImage}' locally : construisez-la avec "
                    "docker build -t NOM . ou vérifiez son nom"
                )

            pHost["images"][vImage] = {"base": vImage, **build_base(vImage)}

        vContainer = create_container(
            pHost,
            vImage,
            vOptions["name"],
            vOptions["ports"],
            vOptions["volumes"],
            vOptions["env"],
        )
        vContainer["command"] = vOptions["command"]

        return start_container(pHost, vContainer, vApp)

    if vVerb == "ps":
        return list_containers(pHost, "-a" in vRest or "--all" in vRest)

    if vVerb == "logs":
        return find_container(pHost, vRest[-1] if vRest else "")["logs"] or [
            "(aucun journal)"
        ]

    if vVerb in ("stop", "start", "restart", "rm"):
        vForce = "-f" in vRest or "--force" in vRest
        vNames = [vWord for vWord in vRest if not vWord.startswith("-")]

        if not vNames:
            raise DockerError(f'"docker {vVerb}" requires at least 1 argument')

        rLines = []

        for vName in vNames:
            vContainer = find_container(pHost, vName)

            if vVerb == "rm":
                if vContainer["status"] == "running" and not vForce:
                    raise DockerError(
                        "Error response from daemon: You cannot remove a running "
                        f"container {vContainer['id']}. Stop the container before "
                        "attempting removal or force remove (docker rm -f)"
                    )

                pHost["containers"].remove(vContainer)
            elif vVerb == "stop":
                vContainer["status"] = "exited (143)"
            else:
                vContainer["status"] = "exited (0)"
                start_container(pHost, vContainer, vApp)

            rLines.append(vName)

        return rLines

    if vVerb == "volume":
        if vRest[:1] == ["ls"]:
            return ["DRIVER    VOLUME NAME"] + [
                f"local     {vName}" for vName in pHost["volumes"]
            ]

        if vRest[:1] == ["create"] and len(vRest) == 2:
            pHost["volumes"].setdefault(vRest[1], {"records": 0, "writer": None})
            return [vRest[1]]

        raise DockerError(
            "Commandes de volume simulées : docker volume ls, docker volume create NOM"
        )

    raise DockerError(
        f"docker: '{vVerb}' n'est pas simulée. Commandes : build, images, pull, run, ps, "
        "logs, stop, start, restart, rm, volume ; et curl."
    )


def is_goal_reached(pHost, pGoal):
    """Indique si l'objectif du niveau est atteint d'après les événements notés."""

    for vEvent in pHost["events"]:
        if pGoal["type"] == "persist" and vEvent["kind"] == "read":
            if vEvent["records"] > 0 and vEvent["other"]:
                return True
        elif pGoal["type"] == "reach" and vEvent["kind"] == "reach":
            if (
                vEvent["port"] == pGoal.get("port", vEvent["port"])
                and vEvent["image"] == pGoal.get("image", vEvent["image"])
                and all(vName in vEvent["running"] for vName in pGoal.get("keep", []))
                and not vEvent["image"].startswith("nginx")
            ):
                return True

    return False
