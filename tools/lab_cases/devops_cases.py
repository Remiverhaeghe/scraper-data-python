"""Cas Maven et Docker : commandes et fichiers piégeux sur chaque niveau."""

from job.devops_levels import load_levels as load_devops_levels
from job.devops_levels import play_step
from job.docker_sim import new_host

# Commandes Maven et Docker jouées à la suite sur chaque niveau
MAVEN_COMMANDS = (
    "mvn compile",
    "mvn test",
    "mvn package -DskipTests",
    "mvn dependency:tree",
    "mvn clean install",
    "mvn -q verify",
    "mvn deploy",
    "mvn",
    "ls -la",
    "mvn   validate",
)
DOCKER_COMMANDS = (
    "docker images",
    "docker ps",
    "docker build .",
    "docker build -t essai .",
    "docker run essai",
    "docker run -d --name a -p 8080:8080 -v donnees:/app/data -e DB_URL=x "
    "-e SERVER_PORT=9090 essai",
    "curl http://localhost:8080/",
    "curl localhost:9090/",
    "docker ps -a",
    "docker logs a",
    "docker logs inconnu",
    "docker stop a",
    "docker start a",
    "docker restart a",
    "docker rm a",
    "docker rm -f a",
    "docker volume ls",
    "docker volume create v1",
    "docker volume rm v1",
    "docker pull nginx:1.27",
    "docker pull inconnu",
    "docker run -d -p 80 nginx",
    "docker run -d -p 8081:80 nginx:1.27",
    "curl -X POST http://localhost:8081/mesures",
    "docker run --frob x",
    "docker run -p",
    "docker run -v data:relatif x",
    "docker exec a ls",
    "kubectl get pods",
    "curl ftp://x",
    'docker run "non fermé',
    "docker run -d --name b alpine:3.20",
    "docker logs b",
)
# Fichiers piégeux, joués avec mvn package sur le premier niveau Maven
POM_VARIANTS = (
    "<project>",
    "<project><a></b></project>",
    "<project>&foo;</project>",
    "<project>&#1114112;</project>",
    "<!DOCTYPE x><project/>",
    "<project/> en trop",
    "",
    "﻿<?xml version='1.0'?><!-- note --><p:project xmlns:p='x'>"
    "<p:modelVersion>4.0.0</p:modelVersion></p:project>",
    "<project><modelVersion>4.0.0</modelVersion><groupId>fr.a</groupId>"
    "<artifactId>&#233;t&#xE9;</artifactId><version><![CDATA[1.0]]></version>"
    "<properties><v>2</v></properties><dependencies><dependency>"
    "<groupId>org.apache.commons</groupId><artifactId>commons-lang3</artifactId>"
    "<version>${v}</version><scope>runtimme</scope></dependency><dependency>"
    "<groupId>x</groupId><artifactId>y</artifactId></dependency></dependencies>"
    "</project>",
    "<project><modelVersion>4.0.0</modelVersion><groupId>fr.a</groupId>"
    "<artifactId>a</artifactId><version>1</version><build><plugins><plugin>"
    "<artifactId>maven-compiler-plugin</artifactId><configuration>"
    "<release>1.8</release></configuration></plugin></plugins></build>"
    "<dependencies><dependency><groupId>x</groupId><artifactId>y</artifactId>"
    "<version>1</version></dependency></dependencies></project>",
    "<project " + "a='b' " * 2000 + "/>",
    "<project><groupId attr=sans-guillemets>x</groupId></project>",
)
# Dockerfiles piégeux, joués sur le premier niveau Docker
DOCKERFILE_VARIANTS = (
    "",
    "COPPY a b",
    "FROM inconnu",
    "FROM alpine:3.20\nRUN apt-get install x",
    "FROM python:3.12-slim\nWORKDIR /app\nCOPY . .\n"
    "RUN pip install -r requirements.txt\nCMD python app.py",
    "FROM eclipse-temurin:21-jre\nCMD",
    "# image\nFROM eclipse-temurin:21-jre \\\n  AS base\nWORKDIR app\nWORKDIR ../srv\n"
    'ENV DB_URL "jdbc:x"\nENV SERVER_PORT=8080\nEXPOSE 80/tcp abc 8080\n'
    "COPY ./target/*.jar ./pom.xml /srv/\nENTRYPOINT java -jar\n"
    'CMD ["suivi-machines-1.0.0.jar"]',
    'FROM eclipse-temurin:21-jre\nCMD ["java", "-jar",',
    "FROM eclipse-temurin:21-jre\nCOPY target/ /app/\nCOPY src /code\n"
    "WORKDIR /app\nCMD java -jar suivi-machines-1.0.0.jar",
    "ARG V\nFROM eclipse-temurin:17-jre\nCOPY absent.jar app.jar",
    'FROM alpine:3.20\nCMD ["/bin/sh", "-c"]',
)
DOCKERFILE_COMMANDS = (
    "docker build -t v .",
    "docker run -d --name v -p 8080:8080 v",
    "docker logs v",
    "curl localhost:8080",
)


def build_devops_case(pLevel, pName, pSteps):
    """Joue des étapes (fichier, commande) : console, objectif, message, hôte final."""

    vHost = new_host(pLevel.get("setup", []))
    vSteps = []

    for vFile, vCommand in pSteps:
        vLines, vReached, vMessage = play_step(pLevel, vFile, vCommand, vHost)
        vSteps.append(
            {
                "file": vFile,
                "command": vCommand,
                "lines": vLines,
                "reached": vReached,
                "message": vMessage,
            }
        )

    rCase = {
        "name": f"{pLevel['id']} : {pName}",
        "level": pLevel["id"],
        "steps": vSteps,
        "host": vHost,
    }

    return rCase


def build_devops_cases():
    """Retourne les cas Maven et Docker : solution, départ, commandes, fichiers piégeux."""

    rCases = []
    vVariantsPlayed = set()

    for vLevel in load_devops_levels().values():
        vCommands = MAVEN_COMMANDS if vLevel["tool"] == "maven" else DOCKER_COMMANDS
        vSeries = [
            (
                "solution",
                [(vLevel["solution"], vCommand) for vCommand in vLevel["commands"]],
            ),
            ("départ", [(vLevel["file"], vCommand) for vCommand in vLevel["commands"]]),
            (
                "commandes variées",
                [(vLevel["solution"], vCommand) for vCommand in vCommands],
            ),
        ]

        if vLevel["tool"] not in vVariantsPlayed:
            vVariantsPlayed.add(vLevel["tool"])
            vSeries += [
                (
                    f"fichier piégeux {vIndex}",
                    [(vFile, vCommand) for vCommand in vPlayed],
                )
                for vIndex, (vFile, vPlayed) in enumerate(
                    (
                        [(vPom, ("mvn package",)) for vPom in POM_VARIANTS]
                        if vLevel["tool"] == "maven"
                        else [
                            (vText, DOCKERFILE_COMMANDS)
                            for vText in DOCKERFILE_VARIANTS
                        ]
                    ),
                    1,
                )
            ]

        rCases += [
            build_devops_case(vLevel, vName, vSteps) for vName, vSteps in vSeries
        ]

    return rCases
