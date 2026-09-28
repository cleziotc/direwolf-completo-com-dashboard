(() => {
    "use strict";

    let lastOverviewData = null;

    function addSparklineToCard(valueId, canvasId) {
        const value = document.getElementById(valueId);
        if (!value) return;

        const card = value.closest(".card");
        if (!card || card.querySelector("#" + canvasId)) return;

        const wrap = document.createElement("div");
        wrap.className = "sparkline-wrap";
        wrap.innerHTML = '<canvas id="' + canvasId + '"></canvas>';
        card.appendChild(wrap);
    }


    function installUi() {
        addSparklineToCard("rf_rx", "spark_rf_rx");
        addSparklineToCard("rf_to_is", "spark_rf_to_is");
        addSparklineToCard("is_rx", "spark_is_rx");
        addSparklineToCard("duplicate_drop", "spark_duplicate");

        const cards = document.querySelector(".cards");

        if (cards && !document.getElementById("ops_grid")) {
            cards.insertAdjacentHTML(
                "afterend",
                `
                <div class="ops-grid" id="ops_grid">
                    <div class="ops-card">
                        <div class="ops-label">Pacotes/min</div>
                        <div class="ops-value" id="packets_per_minute">--</div>
                        <div class="ops-sub">RF RX + APRS-IS nos últimos 60 s</div>
                    </div>

                    <div class="ops-card">
                        <div class="ops-label">Uptime Direwolf</div>
                        <div class="ops-value" id="direwolf_uptime">--</div>
                        <div class="ops-sub">Tempo desde a última inicialização do serviço</div>
                    </div>

                    <div class="ops-card">
                        <div class="ops-label">Uptime Dashboard</div>
                        <div class="ops-value" id="dashboard_uptime">--</div>
                        <div class="ops-sub">Processo FastAPI atual</div>
                    </div>

                    <div class="ops-card">
                        <div class="ops-label">APRS-IS verificado</div>
                        <div class="ops-value" id="last_verified_short">--</div>
                        <div class="ops-sub" id="last_verified_sub">Aguardando estado</div>
                    </div>
                </div>
                `
            );
        }

        const workspace = document.querySelector(".workspace");

        if (workspace && !document.getElementById("insights_grid")) {
            workspace.insertAdjacentHTML(
                "afterend",
                `
                <div class="insights-grid" id="insights_grid">
                    <div class="panel">
                        <div class="panel-header">
                            <div>
                                <div class="panel-title">Top estações</div>
                                <div class="panel-sub">Maior atividade nas últimas 24 horas</div>
                            </div>
                        </div>
                        <div class="station-list" id="top_stations">
                            <div class="station-list-empty">Aguardando dados...</div>
                        </div>
                    </div>

                    <div class="panel">
                        <div class="panel-header">
                            <div>
                                <div class="panel-title">Últimas estações</div>
                                <div class="panel-sub">Último pacote único por indicativo</div>
                            </div>
                        </div>
                        <div class="station-list" id="recent_stations">
                            <div class="station-list-empty">Aguardando dados...</div>
                        </div>
                    </div>

                    <div class="panel">
                        <div class="panel-header">
                            <div>
                                <div class="panel-title">Telemetria / WX</div>
                                <div class="panel-sub">Últimas estações meteorológicas recebidas</div>
                            </div>
                        </div>
                        <div class="weather-list" id="weather_stations">
                            <div class="station-list-empty">Aguardando dados...</div>
                        </div>
                    </div>
                </div>
                `
            );
        }

        if (!document.getElementById("station_modal")) {
            document.body.insertAdjacentHTML(
                "beforeend",
                `
                <div
                    class="station-modal hidden"
                    id="station_modal"
                >
                    <div class="station-modal-card">
                        <div class="station-modal-head">
                            <div class="station-modal-title" id="station_modal_title">--</div>
                            <button
                                type="button"
                                class="station-modal-close"
                                id="station_modal_close"
                                aria-label="Fechar"
                            >×</button>
                        </div>
                        <div class="station-modal-body" id="station_modal_body">
                            Carregando...
                        </div>
                    </div>
                </div>
                `
            );

            document.getElementById("station_modal_close").addEventListener(
                "click",
                closeStationDetails
            );

            document.getElementById("station_modal").addEventListener(
                "click",
                event => {
                    if (event.target.id === "station_modal") {
                        closeStationDetails();
                    }
                }
            );
        }
    }


    function formatDuration(seconds) {
        const total = Number(seconds);

        if (!Number.isFinite(total) || total < 0) {
            return "--";
        }

        const days = Math.floor(total / 86400);
        const hours = Math.floor((total % 86400) / 3600);
        const minutes = Math.floor((total % 3600) / 60);

        if (days > 0) {
            return `${days}d ${hours}h`;
        }

        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        }

        return `${minutes}m`;
    }


    function formatDateTime(isoTime) {
        if (!isoTime) return "--";

        const date = new Date(isoTime);

        if (Number.isNaN(date.getTime())) {
            return "--";
        }

        return date.toLocaleString(
            "pt-BR",
            {
                timeZone: "UTC",
                day: "2-digit",
                month: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit"
            }
        );
    }


    function nullableNumber(value) {
        if (value === null || value === undefined || value === "") {
            return null;
        }

        const number = Number(value);

        return Number.isFinite(number)
            ? number
            : null;
    }


    function renderSparkline(canvasId, values, color) {
        const canvas = document.getElementById(canvasId);

        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();

        if (rect.width <= 0 || rect.height <= 0) return;

        const dpr = window.devicePixelRatio || 1;

        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;

        const ctx = canvas.getContext("2d");

        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        const width = rect.width;
        const height = rect.height;

        ctx.clearRect(0, 0, width, height);

        const clean = (values || []).map(
            value => Number(value) || 0
        );

        if (clean.length < 2) return;

        const maxValue = Math.max(1, ...clean);

        ctx.strokeStyle = color;
        ctx.lineWidth = 1.8;
        ctx.lineJoin = "round";
        ctx.lineCap = "round";
        ctx.beginPath();

        clean.forEach(
            (value, index) => {
                const x = (
                    index / (clean.length - 1)
                ) * width;

                const y = height - 3 - (
                    value / maxValue
                ) * (height - 7);

                if (index === 0) {
                    ctx.moveTo(x, y);
                }
                else {
                    ctx.lineTo(x, y);
                }
            }
        );

        ctx.stroke();
    }


    function sourceChip(source) {
        if (source === "RF") {
            return '<span class="source-chip source-chip-rf">RF</span>';
        }

        return '<span class="source-chip source-chip-is">IS</span>';
    }


    function closeStationDetails() {
        const modal = document.getElementById("station_modal");

        if (modal) {
            modal.classList.add("hidden");
        }
    }


    async function openStationDetails(callsign) {
        const modal = document.getElementById("station_modal");
        const title = document.getElementById("station_modal_title");
        const body = document.getElementById("station_modal_body");

        if (!modal || !title || !body) return;

        title.textContent = callsign;
        body.innerHTML = "Carregando...";
        modal.classList.remove("hidden");

        try {
            const response = await fetch(
                "/api/station/" +
                encodeURIComponent(callsign) +
                "?hours=24"
            );

            if (!response.ok) {
                throw new Error("HTTP " + response.status);
            }

            const data = await response.json();
            const latest = data.latest || {};
            const position = data.position || {};

            let html = `
                <div class="station-detail-grid">
                    <div class="station-detail-card">
                        <div class="station-detail-label">Pacotes 24h</div>
                        <div class="station-detail-value">${data.packets ?? 0}</div>
                    </div>

                    <div class="station-detail-card">
                        <div class="station-detail-label">RF direto</div>
                        <div class="station-detail-value rf">${data.rf_packets ?? 0}</div>
                    </div>

                    <div class="station-detail-card">
                        <div class="station-detail-label">APRS-IS</div>
                        <div class="station-detail-value is">${data.is_packets ?? 0}</div>
                    </div>
                </div>

                <div class="station-detail-section">
                    <div class="station-detail-section-title">Atividade</div>

                    <div class="wx-row">
                        <div class="wx-row-label">Primeiro pacote</div>
                        <div class="wx-row-value">${escapeHtml(formatDateTime(data.first_seen))}</div>
                    </div>

                    <div class="wx-row">
                        <div class="wx-row-label">Último pacote</div>
                        <div class="wx-row-value">${escapeHtml(formatDateTime(data.last_seen))}</div>
                    </div>

                    <div class="wx-row">
                        <div class="wx-row-label">Última origem</div>
                        <div class="wx-row-value">
                            ${latest.source === "RF" ? "RF direto" : "APRS-IS"}
                        </div>
                    </div>
                </div>
            `;

            if (
                position.latitude !== null &&
                position.latitude !== undefined &&
                position.longitude !== null &&
                position.longitude !== undefined
            ) {
                html += `
                    <div class="station-detail-section">
                        <div class="station-detail-section-title">Última posição conhecida</div>

                        <div class="wx-position-coords">
                            <div class="wx-position-coordinate">
                                <span class="wx-position-prefix">LAT</span>
                                <span class="wx-position-value">${Number(position.latitude).toFixed(5)}</span>
                            </div>

                            <div class="wx-position-coordinate">
                                <span class="wx-position-prefix">LON</span>
                                <span class="wx-position-value">${Number(position.longitude).toFixed(5)}</span>
                            </div>
                        </div>

                        <div class="station-list-meta" style="margin-top:8px">
                            ${escapeHtml(formatDateTime(position.time))}
                            •
                            ${position.source === "RF" ? "RF direto" : "APRS-IS"}
                        </div>
                    </div>
                `;
            }

            if (
                latest.aprs_format ||
                latest.speed !== null && latest.speed !== undefined ||
                latest.course !== null && latest.course !== undefined ||
                latest.altitude !== null && latest.altitude !== undefined ||
                latest.mic_e_status
            ) {
                html += '<div class="station-detail-section">';
                html += '<div class="station-detail-section-title">Dados APRS</div>';

                if (latest.aprs_format) {
                    html += `
                        <div class="wx-row">
                            <div class="wx-row-label">Formato</div>
                            <div class="wx-row-value">${escapeHtml(latest.aprs_format)}</div>
                        </div>
                    `;
                }

                if (latest.speed !== null && latest.speed !== undefined) {
                    html += `
                        <div class="wx-row">
                            <div class="wx-row-label">Velocidade</div>
                            <div class="wx-row-value">${formatNumber(latest.speed, 1)} km/h</div>
                        </div>
                    `;
                }

                if (latest.course !== null && latest.course !== undefined) {
                    html += `
                        <div class="wx-row">
                            <div class="wx-row-label">Curso</div>
                            <div class="wx-row-value">${formatNumber(latest.course, 0)}°</div>
                        </div>
                    `;
                }

                if (latest.altitude !== null && latest.altitude !== undefined) {
                    html += `
                        <div class="wx-row">
                            <div class="wx-row-label">Altitude</div>
                            <div class="wx-row-value">${formatNumber(latest.altitude, 0)} m</div>
                        </div>
                    `;
                }

                if (latest.mic_e_status) {
                    html += `
                        <div class="wx-row">
                            <div class="wx-row-label">Mic-E</div>
                            <div class="wx-row-value">${escapeHtml(latest.mic_e_status)}</div>
                        </div>
                    `;
                }

                html += "</div>";
            }

            if (latest.comment) {
                html += `
                    <div class="station-detail-section">
                        <div class="station-detail-section-title">Comentário</div>
                        <div>${escapeHtml(latest.comment)}</div>
                    </div>
                `;
            }

            if (latest.packet) {
                html += `
                    <div class="station-detail-section">
                        <div class="station-detail-section-title">Último pacote bruto</div>
                        <div class="station-detail-packet">${escapeHtml(latest.packet)}</div>
                    </div>
                `;
            }

            body.innerHTML = html;
        }
        catch (error) {
            body.innerHTML =
                '<div class="station-list-empty">Não foi possível carregar os detalhes da estação.</div>';

            console.error(
                "Erro nos detalhes da estação:",
                error
            );
        }
    }


    async function updateOverview() {
        try {
            const [overviewResponse, statusResponse] = await Promise.all(
                [
                    fetch("/api/overview"),
                    fetch("/api/status")
                ]
            );

            if (!overviewResponse.ok) {
                throw new Error(
                    "Overview HTTP " +
                    overviewResponse.status
                );
            }

            const data = await overviewResponse.json();
            const status = statusResponse.ok
                ? await statusResponse.json()
                : {};

            lastOverviewData = data;

            const packetRate = data.packet_rate || {};
            const uptime = data.uptime || {};
            const activity = data.minute_activity || {};
            const series = activity.series || [];

            document.getElementById(
                "packets_per_minute"
            ).textContent =
                packetRate.packets_per_minute ?? "--";

            document.getElementById(
                "direwolf_uptime"
            ).textContent =
                formatDuration(
                    uptime.direwolf_seconds
                );

            document.getElementById(
                "dashboard_uptime"
            ).textContent =
                formatDuration(
                    uptime.dashboard_seconds
                );

            document.getElementById(
                "last_verified_short"
            ).textContent =
                status.last_verified
                    ? formatTime(status.last_verified)
                    : "--";

            document.getElementById(
                "last_verified_sub"
            ).textContent =
                status.aprs_is_server
                    ? "Servidor: " + status.aprs_is_server
                    : "Servidor não identificado";

            renderSparkline(
                "spark_rf_rx",
                series.map(item => item.rf_rx),
                "#22d3ee"
            );

            renderSparkline(
                "spark_rf_to_is",
                series.map(item => item.rf_to_is),
                "#4ade80"
            );

            renderSparkline(
                "spark_is_rx",
                series.map(item => item.is_rx),
                "#60a5fa"
            );

            renderSparkline(
                "spark_duplicate",
                series.map(item => item.duplicate_drop),
                "#f59e0b"
            );

            const top = document.getElementById("top_stations");
            const topStations = (
                data.top_stations &&
                data.top_stations.stations
            ) || [];

            if (topStations.length === 0) {
                top.innerHTML =
                    '<div class="station-list-empty">Sem estações no período.</div>';
            }
            else {
                top.innerHTML = topStations.map(
                    (station, index) => `
                        <div
                            class="station-list-row"
                            data-station-call="${escapeHtml(station.callsign)}"
                        >
                            <div>
                                <div class="station-list-call">
                                    ${index + 1}. ${escapeHtml(station.callsign)}
                                </div>
                                <div class="station-list-meta">
                                    RF ${station.rf_packets ?? 0}
                                    • IS ${station.is_packets ?? 0}
                                    • ${escapeHtml(formatTime(station.last_seen))}
                                </div>
                            </div>
                            <div class="station-list-value">
                                ${station.packets ?? 0}
                            </div>
                        </div>
                    `
                ).join("");
            }

            const recent = document.getElementById("recent_stations");
            const recentStations = (
                data.recent_stations &&
                data.recent_stations.stations
            ) || [];

            if (recentStations.length === 0) {
                recent.innerHTML =
                    '<div class="station-list-empty">Sem estações recentes.</div>';
            }
            else {
                recent.innerHTML = recentStations.map(
                    station => `
                        <div
                            class="station-list-row"
                            data-station-call="${escapeHtml(station.callsign)}"
                        >
                            <div>
                                <div class="station-list-call">
                                    ${escapeHtml(station.callsign)}
                                    ${sourceChip(station.source)}
                                </div>
                                <div class="station-list-meta">
                                    ${station.is_weather ? "WX • " : ""}
                                    ${escapeHtml(station.aprs_format || "APRS")}
                                </div>
                            </div>
                            <div class="station-list-value">
                                ${escapeHtml(formatTime(station.time))}
                            </div>
                        </div>
                    `
                ).join("");
            }

            const weatherContainer =
                document.getElementById(
                    "weather_stations"
                );

            const weatherStations = (
                data.weather_stations &&
                data.weather_stations.stations
            ) || [];

            if (weatherStations.length === 0) {
                weatherContainer.innerHTML =
                    '<div class="station-list-empty">Nenhuma estação WX recebida.</div>';
            }
            else {
                weatherContainer.innerHTML = weatherStations.map(
                    station => {
                        const wx = station.weather || {};
                        const wind = nullableNumber(wx.wind_speed);
                        const gust = nullableNumber(wx.wind_gust);

                        const windText =
                            wind === null
                                ? "--"
                                : formatNumber(
                                    wind * 3.6,
                                    1
                                ) + " km/h";

                        const gustText =
                            gust === null
                                ? ""
                                : " • raj. " +
                                  formatNumber(
                                      gust * 3.6,
                                      1
                                  );

                        return `
                            <div
                                class="weather-card"
                                data-station-call="${escapeHtml(station.callsign)}"
                            >
                                <div class="weather-card-call">
                                    ${escapeHtml(station.callsign)}
                                    ${sourceChip(station.source)}
                                </div>

                                <div class="weather-card-main">
                                    <div class="weather-card-temp">
                                        ${formatNumber(wx.temperature, 1)}°C
                                    </div>
                                    <div class="weather-card-hum">
                                        ${formatNumber(wx.humidity, 0)}%
                                    </div>
                                </div>

                                <div class="weather-card-wind">
                                    ${windText}${gustText}
                                </div>

                                <div class="station-list-meta">
                                    ${escapeHtml(formatTime(station.time))}
                                </div>
                            </div>
                        `;
                    }
                ).join("");
            }

            document
                .querySelectorAll("[data-station-call]")
                .forEach(
                    element => {
                        element.addEventListener(
                            "click",
                            () => openStationDetails(
                                element.dataset.stationCall
                            )
                        );
                    }
                );
        }
        catch (error) {
            console.error(
                "Erro no painel operacional:",
                error
            );
        }
    }


    function redrawSparklines() {
        if (!lastOverviewData) return;

        const activity =
            lastOverviewData.minute_activity || {};

        const series =
            activity.series || [];

        renderSparkline(
            "spark_rf_rx",
            series.map(item => item.rf_rx),
            "#22d3ee"
        );

        renderSparkline(
            "spark_rf_to_is",
            series.map(item => item.rf_to_is),
            "#4ade80"
        );

        renderSparkline(
            "spark_is_rx",
            series.map(item => item.is_rx),
            "#60a5fa"
        );

        renderSparkline(
            "spark_duplicate",
            series.map(item => item.duplicate_drop),
            "#f59e0b"
        );
    }


    function buildNormalPopupV2(station) {
        const sourceLabel =
            station.source === "RF"
                ? "RF direto"
                : "APRS-IS";

        const badgeClass =
            station.source === "RF"
                ? "source-chip-rf"
                : "source-chip-is";

        let html = `
            <div class="normal-popup">
                <div class="normal-head">
                    <div class="popup-call" style="margin-bottom:0">
                        ${escapeHtml(station.callsign)}
                    </div>

                    <div class="normal-badge ${badgeClass}">
                        ${sourceLabel}
                    </div>
                </div>

                <div class="normal-meta">
                    Último pacote
                    ${escapeHtml(formatTime(station.time))}
                </div>

                <div class="wx-position">
                    <div class="wx-position-label">
                        Posição
                    </div>

                    <div class="wx-position-coords">
                        <div class="wx-position-coordinate">
                            <span class="wx-position-prefix">LAT</span>
                            <span class="wx-position-value">
                                ${Number(station.latitude).toFixed(5)}
                            </span>
                        </div>

                        <div class="wx-position-coordinate">
                            <span class="wx-position-prefix">LON</span>
                            <span class="wx-position-value">
                                ${Number(station.longitude).toFixed(5)}
                            </span>
                        </div>
                    </div>
                </div>
        `;

        if (station.aprs_format) {
            html += `
                <div class="wx-row">
                    <div class="wx-row-label">Formato</div>
                    <div class="wx-row-value">
                        ${escapeHtml(station.aprs_format)}
                    </div>
                </div>
            `;
        }

        if (
            station.speed !== null &&
            station.speed !== undefined
        ) {
            html += `
                <div class="wx-row">
                    <div class="wx-row-label">Velocidade</div>
                    <div class="wx-row-value">
                        ${formatNumber(station.speed, 1)} km/h
                    </div>
                </div>
            `;
        }

        if (
            station.course !== null &&
            station.course !== undefined
        ) {
            html += `
                <div class="wx-row">
                    <div class="wx-row-label">Curso</div>
                    <div class="wx-row-value">
                        ${formatNumber(station.course, 0)}°
                    </div>
                </div>
            `;
        }

        if (
            station.altitude !== null &&
            station.altitude !== undefined
        ) {
            html += `
                <div class="wx-row">
                    <div class="wx-row-label">Altitude</div>
                    <div class="wx-row-value">
                        ${formatNumber(station.altitude, 0)} m
                    </div>
                </div>
            `;
        }

        if (station.mic_e_status) {
            html += `
                <div class="wx-row">
                    <div class="wx-row-label">Mic-E</div>
                    <div class="wx-row-value">
                        ${escapeHtml(station.mic_e_status)}
                    </div>
                </div>
            `;
        }

        if (station.comment) {
            html += `
                <div class="popup-comment">
                    ${escapeHtml(station.comment)}
                </div>
            `;
        }

        html += `
                <button
                    type="button"
                    class="popup-detail-button"
                    data-popup-station="${escapeHtml(station.callsign)}"
                >
                    Detalhes da estação
                </button>
            </div>
        `;

        return html;
    }


    installUi();

    window.openStationDetails =
        openStationDetails;

    window.closeStationDetails =
        closeStationDetails;

    window.buildNormalPopup =
        buildNormalPopupV2;

    try {
        buildNormalPopup =
            buildNormalPopupV2;
    }
    catch (error) {
        console.debug(
            "Binding do popup normal:",
            error
        );
    }

    document.addEventListener(
        "click",
        event => {
            const button =
                event.target.closest(
                    "[data-popup-station]"
                );

            if (button) {
                openStationDetails(
                    button.dataset.popupStation
                );
            }
        }
    );

    updateOverview();

    setInterval(
        updateOverview,
        15000
    );

    window.addEventListener(
        "resize",
        redrawSparklines
    );

    if (typeof updateMap === "function") {
        updateMap();
    }
})();
