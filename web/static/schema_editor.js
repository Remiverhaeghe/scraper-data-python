// Éditeur de schéma des questions de révision : palette, grille, déplacement et câblage.
// La géométrie et les symboles viennent du serveur (job/schema_drawing.py) : le
// schéma construit ici ressemble au schéma attendu affiché à la correction.
(function () {
    var SVG_NS = "http://www.w3.org/2000/svg";
    var PORT_RADIUS = 6;

    function createElement(pName, pAttributes) {
        var rElement = document.createElementNS(SVG_NS, pName);

        Object.keys(pAttributes || {}).forEach(function (pKey) {
            rElement.setAttribute(pKey, pAttributes[pKey]);
        });

        return rElement;
    }

    function createEditor(pRoot) {
        var vConfig = JSON.parse(pRoot.querySelector("[data-schema-config]").textContent);
        var vGrid = vConfig.grid;
        var vCanvas = pRoot.querySelector("[data-schema-canvas]");
        var vAnswer = pRoot.querySelector("[data-schema-answer]");
        var vWiresLayer = createElement("g");
        var vComponentsLayer = createElement("g");
        // Par type : case occupée et groupe SVG ; chaque type n'est posé qu'une fois.
        var vComponents = {};
        var vWires = [];
        var vPending = null;
        var vSelected = null;
        var vDrag = null;
        var vWidth = 2 * vGrid.margin + vGrid.columns * vGrid.cellWidth;
        var vHeight = 2 * vGrid.margin + vGrid.rows * vGrid.cellHeight;

        vCanvas.setAttribute("viewBox", "0 0 " + vWidth + " " + vHeight);
        vCanvas.appendChild(createElement("rect", { width: vWidth, height: vHeight, fill: "#ffffff" }));
        vCanvas.appendChild(vWiresLayer);
        vCanvas.appendChild(vComponentsLayer);

        function getOrigin(pCell) {
            return [
                vGrid.margin + pCell[0] * vGrid.cellWidth + vGrid.symbolOffset,
                vGrid.margin + pCell[1] * vGrid.cellHeight
            ];
        }

        function getPort(pType, pPort) {
            return vConfig.components[pType].ports.filter(function (pItem) {
                return pItem[0] === pPort;
            })[0];
        }

        function getPortPosition(pType, pPort) {
            var vOrigin = getOrigin(vComponents[pType].cell);
            var vPort = getPort(pType, pPort);

            return [vOrigin[0] + vPort[1], vOrigin[1] + vPort[2]];
        }

        function getExit(pType, pPort) {
            return getPort(pType, pPort)[2] < vGrid.height / 2 ? -1 : 1;
        }

        // Même tracé que route_wire côté serveur : sortie de borne, couloirs, arrivée.
        function routeWire(pStart, pStartExit, pEnd, pEndExit, pCorridor, pLane) {
            var vFacing = pStartExit !== pEndExit && (pEnd[1] - pStart[1]) * pStartExit > 0;

            if (vFacing && pStart[0] === pEnd[0]) {
                return "M" + pStart[0] + "," + pStart[1] + " V" + pEnd[1];
            }

            // Bornes proches et face à face : un coude à mi-hauteur, sans passer au couloir.
            if (vFacing && Math.abs(pEnd[1] - pStart[1]) <= vGrid.facingLimit) {
                var vMiddle = (pStart[1] + pEnd[1]) / 2 + pStartExit * pLane * vGrid.laneStep / 2;

                return "M" + pStart[0] + "," + pStart[1] + " V" + vMiddle + " H" + pEnd[0] + " V" + pEnd[1];
            }

            var vShift = vGrid.wireExit + pLane * vGrid.laneStep;
            var vCorridor = pCorridor + pLane * vGrid.laneStep;

            return "M" + pStart[0] + "," + pStart[1]
                + " V" + (pStart[1] + pStartExit * vShift)
                + " H" + vCorridor
                + " V" + (pEnd[1] + pEndExit * vShift)
                + " H" + pEnd[0] + " V" + pEnd[1];
        }

        function save() {
            var vTypes = Object.keys(vComponents);

            vAnswer.value = vTypes.length ? JSON.stringify({
                components: vTypes.map(function (pType) {
                    return { type: pType, x: vComponents[pType].cell[0], y: vComponents[pType].cell[1] };
                }),
                wires: vWires.map(function (pWire) {
                    return pWire.start.concat(pWire.end);
                })
            }) : "";
        }

        function isFree(pCell, pType) {
            return !Object.keys(vComponents).some(function (pOther) {
                var vCell = vComponents[pOther].cell;

                return pOther !== pType && vCell[0] === pCell[0] && vCell[1] === pCell[1];
            });
        }

        // Colonne par colonne : une chaîne se construit de haut en bas.
        function getFirstFreeCell() {
            for (var vColumn = 0; vColumn < vGrid.columns; vColumn += 1) {
                for (var vRow = 0; vRow < vGrid.rows; vRow += 1) {
                    if (isFree([vColumn, vRow])) {
                        return [vColumn, vRow];
                    }
                }
            }

            return null;
        }

        function getNearestCell(pX, pY) {
            var vColumn = Math.round((pX - vGrid.margin - vGrid.symbolOffset) / vGrid.cellWidth);
            var vRow = Math.round((pY - vGrid.margin) / vGrid.cellHeight);

            return [
                Math.min(Math.max(vColumn, 0), vGrid.columns - 1),
                Math.min(Math.max(vRow, 0), vGrid.rows - 1)
            ];
        }

        function moveGroup(pType, pX, pY) {
            vComponents[pType].group.setAttribute("transform", "translate(" + pX + "," + pY + ")");
        }

        function redrawWires() {
            vWires.forEach(function (pWire, pIndex) {
                var vStart = getPortPosition(pWire.start[0], pWire.start[1]);
                var vEnd = getPortPosition(pWire.end[0], pWire.end[1]);
                var vCorridor = Math.max(
                    getOrigin(vComponents[pWire.start[0]].cell)[0],
                    getOrigin(vComponents[pWire.end[0]].cell)[0]
                ) - vGrid.symbolOffset + vGrid.corridorOffset;
                var vPath = routeWire(
                    vStart, getExit(pWire.start[0], pWire.start[1]),
                    vEnd, getExit(pWire.end[0], pWire.end[1]),
                    vCorridor, pIndex % vGrid.laneCount
                );

                pWire.hit.setAttribute("d", vPath);
                pWire.line.setAttribute("d", vPath);
            });
        }

        function select(pItem) {
            pRoot.querySelectorAll(".is-selected").forEach(function (pElement) {
                pElement.classList.remove("is-selected");
            });
            vSelected = pItem;

            if (pItem) {
                pItem.element.classList.add("is-selected");
            }
        }

        function setPending(pPort) {
            if (vPending) {
                vPending.element.classList.remove("is-pending");
            }

            vPending = pPort;

            if (pPort) {
                pPort.element.classList.add("is-pending");
            }
        }

        function addWire(pStart, pEnd) {
            var vKey = [pStart.join("."), pEnd.join(".")].sort().join("|");

            if (vWires.some(function (pWire) { return pWire.key === vKey; })) {
                return;
            }

            var vGroup = createElement("g", { class: "schema-wire" });
            var vWire = {
                key: vKey,
                start: pStart,
                end: pEnd,
                element: vGroup,
                hit: createElement("path", { class: "schema-wire-hit" }),
                line: createElement("path", { class: "schema-wire-line", stroke: vGrid.wireColor })
            };

            vGroup.appendChild(vWire.hit);
            vGroup.appendChild(vWire.line);
            vGroup.wire = vWire;
            vWiresLayer.appendChild(vGroup);
            vWires.push(vWire);
            redrawWires();
            save();
        }

        function selectPort(pType, pPort, pElement) {
            if (!vPending) {
                setPending({ type: pType, port: pPort, element: pElement });
                return;
            }

            var vFirst = vPending;

            setPending(null);

            if (vFirst.type !== pType) {
                addWire([vFirst.type, vFirst.port], [pType, pPort]);
            }
        }

        function addComponent(pType) {
            var vCell = getFirstFreeCell();
            var vComponent = vConfig.components[pType];

            if (vComponents[pType] || !vCell) {
                return;
            }

            var vGroup = createElement("g", { class: "schema-component", "data-component": pType });
            var vTop = vGrid.height / 2 - (vComponent.lines.length - 1) * vGrid.labelLineHeight / 2;

            vGroup.appendChild(createElement("rect", {
                class: "schema-frame", x: -4, y: -4, width: vGrid.width + 8, height: vGrid.height + 8
            }));

            var vSymbol = createElement("g");

            // Dessin du symbole fourni par le serveur, constant du code et non saisi.
            vSymbol.innerHTML = vComponent.drawing;
            vGroup.appendChild(vSymbol);

            vComponent.lines.forEach(function (pLine, pIndex) {
                var vText = createElement("text", {
                    x: vGrid.width + vGrid.labelGap,
                    y: vTop + pIndex * vGrid.labelLineHeight + 4,
                    "font-size": 12,
                    fill: "#334155"
                });

                vText.textContent = pLine;
                vGroup.appendChild(vText);
            });

            vComponent.ports.forEach(function (pPort) {
                var vCircle = createElement("circle", {
                    class: "schema-port", cx: pPort[1], cy: pPort[2], r: PORT_RADIUS, "data-port": pPort[0]
                });
                var vTitle = createElement("title");

                vTitle.textContent = vComponent.label + " : borne " + pPort[0];
                vCircle.appendChild(vTitle);
                vGroup.appendChild(vCircle);
            });

            vComponents[pType] = { cell: vCell, group: vGroup, element: vGroup, type: pType };
            vComponentsLayer.appendChild(vGroup);
            moveGroup(pType, getOrigin(vCell)[0], getOrigin(vCell)[1]);
            pRoot.querySelector('[data-type="' + pType + '"]').disabled = true;
            save();
        }

        function removeWire(pWire) {
            vWires.splice(vWires.indexOf(pWire), 1);
            pWire.element.remove();
        }

        function removeComponent(pType) {
            vWires.filter(function (pWire) {
                return pWire.start[0] === pType || pWire.end[0] === pType;
            }).forEach(removeWire);

            if (vPending && vPending.type === pType) {
                setPending(null);
            }

            vComponents[pType].group.remove();
            delete vComponents[pType];
            pRoot.querySelector('[data-type="' + pType + '"]').disabled = false;
        }

        function deleteSelection() {
            if (vSelected && vSelected.wire) {
                removeWire(vSelected.wire);
            } else if (vSelected && vSelected.type) {
                removeComponent(vSelected.type);
            }

            select(null);
            redrawWires();
            save();
        }

        function getPoint(pEvent) {
            var vPoint = vCanvas.createSVGPoint();

            vPoint.x = pEvent.clientX;
            vPoint.y = pEvent.clientY;

            return vPoint.matrixTransform(vCanvas.getScreenCTM().inverse());
        }

        vCanvas.addEventListener("pointerdown", function (pEvent) {
            var vPort = pEvent.target.closest("[data-port]");
            var vGroup = pEvent.target.closest("[data-component]");
            var vWire = pEvent.target.closest(".schema-wire");

            vCanvas.focus();

            if (vPort) {
                selectPort(vGroup.dataset.component, vPort.dataset.port, vPort);
                pEvent.preventDefault();
                return;
            }

            if (vGroup) {
                var vType = vGroup.dataset.component;
                var vPoint = getPoint(pEvent);
                var vOrigin = getOrigin(vComponents[vType].cell);

                select(vComponents[vType]);
                vDrag = { type: vType, dx: vPoint.x - vOrigin[0], dy: vPoint.y - vOrigin[1] };
                vCanvas.setPointerCapture(pEvent.pointerId);
                pEvent.preventDefault();
                return;
            }

            select(vWire ? { element: vWire, wire: vWire.wire } : null);
        });

        vCanvas.addEventListener("pointermove", function (pEvent) {
            if (vDrag) {
                var vPoint = getPoint(pEvent);

                moveGroup(vDrag.type, vPoint.x - vDrag.dx, vPoint.y - vDrag.dy);
            }
        });

        vCanvas.addEventListener("pointerup", function (pEvent) {
            if (!vDrag) {
                return;
            }

            var vPoint = getPoint(pEvent);
            var vCell = getNearestCell(vPoint.x - vDrag.dx, vPoint.y - vDrag.dy);
            var vComponent = vComponents[vDrag.type];

            // Case occupée : le composant revient à sa place.
            if (isFree(vCell, vDrag.type)) {
                vComponent.cell = vCell;
            }

            moveGroup(vDrag.type, getOrigin(vComponent.cell)[0], getOrigin(vComponent.cell)[1]);
            vDrag = null;
            redrawWires();
            save();
        });

        vCanvas.addEventListener("keydown", function (pEvent) {
            if (pEvent.key === "Delete" || pEvent.key === "Backspace") {
                deleteSelection();
                pEvent.preventDefault();
            }
        });

        pRoot.querySelectorAll("[data-type]").forEach(function (pButton) {
            pButton.addEventListener("click", function () {
                addComponent(pButton.dataset.type);
            });
        });

        pRoot.querySelector('[data-schema-action="delete"]').addEventListener("click", deleteSelection);
        pRoot.querySelector('[data-schema-action="clear"]').addEventListener("click", function () {
            Object.keys(vComponents).forEach(removeComponent);
            select(null);
            save();
        });

        pRoot.hidden = false;
    }

    document.querySelectorAll("[data-schema-editor]").forEach(createEditor);
})();
