"""Schémas électriques sur le web : montages guidés, mode libre, simulation"""

import json
import re
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from job.circuit import OPERABLE_DEFAULTS, PROTECTIONS, Circuit
from job.circuit_drawing import render_circuit
from job.circuit_levels import (
    FREE_LIMITS,
    build_circuit_overview,
    build_values,
    delete_schema,
    find_schema,
    get_controls,
    get_editable,
    get_solution,
    load_levels,
    read_schema,
    read_state,
    run_level,
    save_attempt,
    save_schema,
)
from job.progress import XP_RULES
from web.dependencies import get_database_file, require_csrf
from web.rendering import templates

router = APIRouter()

MAX_FIELD_LENGTH = 20_000
FILE_NAME_PATTERN = re.compile(r"[^\w-]+")


def check_level(pLevelId):
    """Retourne un niveau ; refuse un identifiant inconnu."""

    rLevel = load_levels().get(pLevelId)

    if rLevel is None:
        raise HTTPException(status_code=404, detail="Montage inconnu.")

    return rLevel


def read_json(pText):
    """Retourne un champ JSON du formulaire, ou None s'il est absent ou illisible."""

    if not pText or len(pText) > MAX_FIELD_LENGTH:
        return None

    try:
        rValue = json.loads(pText)

    except ValueError:
        return None

    return rValue


def render_page(pRequest, pDatabaseFile, pValues):
    """Affiche la page : montages, mode libre et montage ouvert."""

    rResponse = templates.TemplateResponse(
        pRequest,
        "circuit.html",
        {
            "active_page": "circuit",
            "overview": build_circuit_overview(pDatabaseFile),
            "level_xp": XP_RULES["circuit_level"][1],
            **pValues,
        },
    )

    return rResponse


def describe_work(pLevel, pSchema, pValues, pFree=False, pName=""):
    """Retourne les valeurs d'affichage de l'éditeur : palette, schéma, valeurs."""

    vLimits = pLevel["palette"] if pLevel else FREE_LIMITS
    vComponents = (pSchema or {}).get("components") or []

    if pLevel:
        vComponents = [
            {"id": vId, "type": vId.split("-")[0], "x": 0, "y": 0}
            for vId in pLevel.get("editable", [])
        ]

    rValues = {
        "level": pLevel,
        "free": pFree,
        "schema_name": pName,
        "palette": vLimits,
        "initial": pSchema or {"components": [], "wires": []},
        "values": pValues,
        "editable": get_editable(
            [vItem for vItem in vComponents if isinstance(vItem, dict)], pLevel
        ),
    }

    return rValues


@router.get("/circuit", response_class=HTMLResponse)
def show_circuit(
    request: Request,
    pLevelId: str = Query("", alias="level"),
    pFree: bool = Query(False, alias="free"),
    pName: str = Query("", alias="schema", max_length=60),
    pDatabaseFile: str = Depends(get_database_file),
):
    """Affiche les montages, et le montage ou le schéma libre demandé."""

    vValues = {}

    if pLevelId:
        vLevel = check_level(pLevelId)
        vRow = next(
            vRow
            for vRow in build_circuit_overview(pDatabaseFile)["rows"]
            if vRow["id"] == pLevelId
        )
        vValues = describe_work(vLevel, vRow["schema"], vRow["values"])
    elif pFree:
        vSaved = find_schema(pDatabaseFile, pName) if pName else None
        vValues = describe_work(
            None,
            (vSaved or {}).get("schema"),
            (vSaved or {}).get("values") or {},
            True,
            pName if vSaved else "",
        )

    rResponse = render_page(request, pDatabaseFile, vValues)

    return rResponse


def read_form_values(pForm, pComponents, pLevel):
    """Retourne les valeurs réglées dans le formulaire, bornées."""

    vRaw = {
        vKey[len("value_") :]: vValue
        for vKey, vValue in pForm.items()
        if vKey.startswith("value_") and isinstance(vValue, str)
    }

    if pLevel:
        return build_values(
            pComponents, vRaw, pLevel.get("values"), pLevel.get("editable", [])
        )

    rValues = build_values(pComponents, vRaw)

    return rValues


def build_simulation(pComponents, pWires, pResult, pInputs, pMemory):
    """Retourne le dessin simulé, les commandes avec leur état et l'état à renvoyer."""

    rSimulation = {
        "svg": render_circuit(pComponents, pWires, pResult),
        "faults": pResult["faults"],
        "controls": [
            {
                "id": vId,
                "label": vLabel,
                "status": pResult["parts"][vId]["status"],
                "on": bool(pInputs.get(vId, OPERABLE_DEFAULTS[vType])),
            }
            for vId, vType, vLabel in get_controls(pComponents)
        ],
        "inputs": json.dumps(pInputs),
        "memory": json.dumps(pMemory),
    }

    return rSimulation


@router.post(
    "/circuit/run", response_class=HTMLResponse, dependencies=[Depends(require_csrf)]
)
async def run_circuit(
    request: Request,
    pDatabaseFile: str = Depends(get_database_file),
):
    """Vérifie, simule, manœuvre, enregistre ou exporte le schéma envoyé."""

    vForm = await request.form()
    vLevelId = str(vForm.get("level", ""))
    vLevel = check_level(vLevelId) if vLevelId else None
    vAction = str(vForm.get("action", "simulate"))
    vName = " ".join(str(vForm.get("name", "")).split())[:60]
    vRawSchema = read_json(str(vForm.get("answer", ""))) or {"components": []}
    vValues = {}

    try:
        vComponents, vWires = read_schema(
            vRawSchema, vLevel["palette"] if vLevel else FREE_LIMITS
        )

    except (ValueError, TypeError, KeyError, AttributeError) as vError:
        vMessage = (
            str(vError) if isinstance(vError, ValueError) else "Schéma illisible."
        )

        return render_page(
            request,
            pDatabaseFile,
            {
                **describe_work(vLevel, None, {}, vLevel is None, vName),
                "error": vMessage,
            },
        )

    vSchema = {"components": vComponents, "wires": vWires}
    vValues = read_form_values(vForm, vComponents, vLevel)
    vWork = describe_work(vLevel, vSchema, vValues, vLevel is None, vName)

    if vAction == "solution" and vLevel:
        vComponents, vWires, vValues = get_solution(vLevel)
        vWork = describe_work(
            vLevel, {"components": vComponents, "wires": vWires}, vValues
        )
        return render_page(request, pDatabaseFile, vWork)

    if vAction == "export":
        vFileName = FILE_NAME_PATTERN.sub("-", vName or "schema").strip("-") or "schema"

        return Response(
            render_circuit(vComponents, vWires, pTitle=vName or "Schéma"),
            media_type="image/svg+xml",
            headers={"Content-Disposition": f'attachment; filename="{vFileName}.svg"'},
        )

    if vAction == "save" and vLevel is None:
        try:
            save_schema(pDatabaseFile, vName, vSchema, vValues)

        except ValueError as vError:
            return render_page(request, pDatabaseFile, {**vWork, "error": str(vError)})

        vUrl = (
            router.url_path_for("show_circuit")
            + "?"
            + urlencode({"free": 1, "schema": vName})
        )

        return RedirectResponse(vUrl, status_code=303)

    vCircuit = Circuit(vComponents, vWires, vValues)
    vExtra = {}

    if vAction == "check" and vLevel:
        vRun = run_level(vLevel, vComponents, vWires, vValues)
        vExtra["run"] = vRun
        vExtra["first"] = save_attempt(
            pDatabaseFile, vLevelId, vSchema, vValues, vRun["passed"]
        )
        vInputs = vRun["inputs"]
        vResult = vRun["result"]
    else:
        vInputs, vMemory = read_state(
            read_json(str(vForm.get("inputs", ""))),
            read_json(str(vForm.get("memory", ""))),
            vComponents,
        )

        if vAction.startswith("operate:"):
            vId = vAction.split(":", 1)[1]
            vType = vCircuit.types.get(vId)

            if vType in OPERABLE_DEFAULTS:
                vInputs[vId] = not vInputs.get(vId, OPERABLE_DEFAULTS[vType])

                if vType in PROTECTIONS and vInputs[vId]:
                    vMemory["tripped"] = [
                        vOther for vOther in vMemory["tripped"] if vOther != vId
                    ]
        else:
            vInputs, vMemory = {}, None

        vResult = vCircuit.simulate(vInputs, vMemory)

    vExtra["simulation"] = build_simulation(
        vCircuit.components, vWires, vResult, vInputs, vResult["memory"]
    )

    rResponse = render_page(request, pDatabaseFile, {**vWork, **vExtra})

    return rResponse


@router.post("/circuit/delete", dependencies=[Depends(require_csrf)])
async def delete_circuit_schema(
    request: Request, pDatabaseFile: str = Depends(get_database_file)
):
    """Supprime un schéma libre enregistré et revient au mode libre."""

    vForm = await request.form()
    delete_schema(pDatabaseFile, str(vForm.get("name", "")))

    rResponse = RedirectResponse(
        router.url_path_for("show_circuit") + "?free=1", status_code=303
    )

    return rResponse
