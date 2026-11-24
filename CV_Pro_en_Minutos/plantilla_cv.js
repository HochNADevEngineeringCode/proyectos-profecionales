/**
 * ============================================================================
 * ARCHIVO: plantilla_cv.js
 * DESCRIPCIÓN: Módulo reemplazable de la plantilla del CV.
 *              Incluye:
 *                - Renderizado condicional (oculta lo omitido/vacío).
 *                - Enlaces de contacto (LinkedIn / GitHub) clicables.
 *                - Código QR dinámico si el usuario ingresó un enlace válido.
 * ============================================================================
 */

function escaparHTML(texto) {
    if (!texto) return "";
    return String(texto)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Asegura que los enlaces tengan protocolo http/https para funcionar bien
function normalizarURL(url) {
    const limpia = (url || "").trim();
    if (!limpia) return "";
    if (/^https?:\/\//i.test(limpia)) return limpia;
    return `https://${limpia}`;
}

function generarHTMLPlantillaCV(datos) {
    const linkedinURL = normalizarURL(datos.linkedin);
    const githubURL = normalizarURL(datos.github);
    // El QR prioriza LinkedIn; si no hay LinkedIn, usa GitHub
    const urlParaQR = linkedinURL || githubURL || "";

    const experienciasValidas = (datos.experiencias || []).filter(
        (exp) => exp.puesto.trim() || exp.empresa.trim() || exp.descripcion.trim()
    );

    const educacionesValidas = (datos.educaciones || []).filter(
        (edu) => edu.titulo.trim() || edu.institucion.trim()
    );

    const habilidadesValidas = (datos.habilidades || []).filter((h) => h.trim());
    const idiomasValidos = (datos.idiomas || []).filter((i) => i.trim());

    const htmlExperiencias = experienciasValidas
        .map(
            (exp) => `
            <article class="cv-entry">
                <div class="cv-entry-header">
                    ${exp.puesto.trim() ? `<h3 class="cv-entry-title">${escaparHTML(exp.puesto)}</h3>` : ""}
                    ${exp.periodo.trim() ? `<span class="cv-entry-date">${escaparHTML(exp.periodo)}</span>` : ""}
                </div>
                ${exp.empresa.trim() ? `<p class="cv-entry-subtitle">${escaparHTML(exp.empresa)}</p>` : ""}
                ${exp.descripcion.trim() ? `<p class="cv-entry-description">${escaparHTML(exp.descripcion)}</p>` : ""}
            </article>
        `
        )
        .join("");

    const htmlEducacion = educacionesValidas
        .map(
            (edu) => `
            <article class="cv-entry">
                <div class="cv-entry-header">
                    ${edu.titulo.trim() ? `<h3 class="cv-entry-title">${escaparHTML(edu.titulo)}</h3>` : ""}
                    ${edu.periodo.trim() ? `<span class="cv-entry-date">${escaparHTML(edu.periodo)}</span>` : ""}
                </div>
                ${edu.institucion.trim() ? `<p class="cv-entry-subtitle">${escaparHTML(edu.institucion)}</p>` : ""}
            </article>
        `
        )
        .join("");

    const tieneAside = Boolean(datos.fotoDataUrl) || Boolean(urlParaQR);

    return `
        <style>
            .cv-sheet {
                --cv-accent: #344D69;
                --cv-text: #202936;
                --cv-muted: #667386;
                --cv-line: #DCE2E9;
                --cv-bg: #FFFFFF;

                width: 100%;
                max-width: 794px;
                min-height: 1123px;
                margin: 0 auto;
                padding: 48px 54px;
                background: var(--cv-bg);
                color: var(--cv-text);
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10pt;
                line-height: 1.5;
                box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12);
                text-align: left;
            }

            .cv-sheet *,
            .cv-sheet *::before,
            .cv-sheet *::after {
                box-sizing: border-box;
            }

            .cv-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 24px;
                padding-bottom: 22px;
                border-bottom: 2px solid var(--cv-accent);
            }

            .cv-header-info {
                flex: 1;
                min-width: 0;
            }

            .cv-name {
                margin: 0;
                font-size: 27pt;
                font-weight: 700;
                letter-spacing: -0.8px;
                line-height: 1.15;
            }

            .cv-position {
                margin: 5px 0 13px;
                color: var(--cv-accent);
                font-size: 12pt;
                font-weight: 600;
            }

            .cv-contact {
                display: flex;
                flex-wrap: wrap;
                gap: 5px 15px;
                color: var(--cv-muted);
                font-size: 9pt;
            }

            .cv-contact a {
                color: var(--cv-accent);
                font-weight: 600;
                text-decoration: underline;
                text-underline-offset: 2px;
            }

            .cv-header-aside {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 10px;
                flex-shrink: 0;
            }

            .cv-photo {
                width: 95px;
                height: 115px;
                object-fit: cover;
                object-position: center;
                border-radius: 4px;
            }

            .cv-qr-box {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 4px;
            }

            .cv-qr-canvas {
                width: 84px;
                height: 84px;
                padding: 3px;
                background: #FFFFFF;
                border: 1px solid var(--cv-line);
            }

            .cv-qr-canvas img,
            .cv-qr-canvas canvas {
                display: block;
                width: 76px !important;
                height: 76px !important;
            }

            .cv-qr-label {
                color: var(--cv-accent);
                font-size: 7.5pt;
                font-weight: 600;
                text-align: center;
            }

            .cv-section {
                margin-top: 23px;
                break-inside: avoid;
            }

            .cv-section-title {
                margin: 0 0 11px;
                padding-bottom: 6px;
                border-bottom: 1px solid var(--cv-line);
                color: var(--cv-accent);
                font-size: 10pt;
                font-weight: 700;
                letter-spacing: 1px;
                text-transform: uppercase;
            }

            .cv-profile {
                margin: 0;
                color: var(--cv-text);
                line-height: 1.65;
            }

            .cv-entry {
                margin-bottom: 14px;
                break-inside: avoid;
            }

            .cv-entry:last-child {
                margin-bottom: 0;
            }

            .cv-entry-header {
                display: flex;
                justify-content: space-between;
                align-items: baseline;
                flex-wrap: wrap;
                gap: 4px 12px;
            }

            .cv-entry-title {
                margin: 0;
                font-size: 10pt;
                font-weight: 700;
            }

            .cv-entry-date {
                color: var(--cv-muted);
                font-size: 9pt;
            }

            .cv-entry-subtitle {
                margin: 2px 0 5px;
                color: var(--cv-accent);
                font-size: 9pt;
                font-weight: 600;
            }

            .cv-entry-description {
                margin: 0;
                line-height: 1.55;
                white-space: pre-line;
            }

            .cv-inline-list {
                display: flex;
                flex-wrap: wrap;
                gap: 7px 17px;
                margin: 0;
                padding: 0;
                list-style: none;
            }

            .cv-inline-list li {
                font-size: 9.5pt;
            }

            .cv-inline-list li:not(:last-child)::after {
                content: "·";
                margin-left: 17px;
                color: var(--cv-accent);
                font-weight: 700;
            }

            @page {
                size: A4;
                margin: 0;
            }

            @media print {
                .cv-sheet {
                    width: 210mm;
                    min-height: 297mm;
                    padding: 15mm 17mm;
                    margin: 0;
                    box-shadow: none;
                    -webkit-print-color-adjust: exact;
                    print-color-adjust: exact;
                }

                .cv-contact a {
                    color: var(--cv-text);
                    text-decoration: none;
                }
            }
        </style>

        <article class="cv-sheet">
            <header class="cv-header">
                <div class="cv-header-info">
                    ${datos.nombreApellido.trim() ? `<h1 class="cv-name">${escaparHTML(datos.nombreApellido)}</h1>` : ""}
                    ${datos.vacante.trim() ? `<p class="cv-position">${escaparHTML(datos.vacante)}</p>` : ""}

                    <div class="cv-contact">
                        ${datos.localidad.trim() ? `<span>${escaparHTML(datos.localidad)}</span>` : ""}
                        ${datos.telefono.trim() ? `<span>${escaparHTML(datos.telefono)}</span>` : ""}
                        ${datos.email.trim() ? `<a href="mailto:${escaparHTML(datos.email)}">${escaparHTML(datos.email)}</a>` : ""}
                        ${linkedinURL ? `<a href="${escaparHTML(linkedinURL)}" target="_blank" rel="noopener noreferrer">LinkedIn</a>` : ""}
                        ${githubURL ? `<a href="${escaparHTML(githubURL)}" target="_blank" rel="noopener noreferrer">GitHub</a>` : ""}
                    </div>
                </div>

                ${
                    tieneAside
                        ? `
                        <div class="cv-header-aside">
                            ${datos.fotoDataUrl ? `<img class="cv-photo" src="${datos.fotoDataUrl}" alt="Fotografía profesional">` : ""}
                            ${
                                urlParaQR
                                    ? `
                                    <div class="cv-qr-box">
                                        <div id="cv-qr-target" class="cv-qr-canvas" data-qr-url="${escaparHTML(urlParaQR)}"></div>
                                        <span class="cv-qr-label">${linkedinURL ? "Ver LinkedIn" : "Ver GitHub"}</span>
                                    </div>
                                `
                                    : ""
                            }
                        </div>
                    `
                        : ""
                }
            </header>

            ${
                datos.perfil.trim()
                    ? `
                    <section class="cv-section">
                        <h2 class="cv-section-title">Perfil profesional</h2>
                        <p class="cv-profile">${escaparHTML(datos.perfil)}</p>
                    </section>
                `
                    : ""
            }

            ${
                experienciasValidas.length > 0
                    ? `
                    <section class="cv-section">
                        <h2 class="cv-section-title">Experiencia laboral</h2>
                        ${htmlExperiencias}
                    </section>
                `
                    : ""
            }

            ${
                educacionesValidas.length > 0
                    ? `
                    <section class="cv-section">
                        <h2 class="cv-section-title">Educación y formación</h2>
                        ${htmlEducacion}
                    </section>
                `
                    : ""
            }

            ${
                habilidadesValidas.length > 0
                    ? `
                    <section class="cv-section">
                        <h2 class="cv-section-title">Habilidades</h2>
                        <ul class="cv-inline-list">
                            ${habilidadesValidas.map((hab) => `<li>${escaparHTML(hab)}</li>`).join("")}
                        </ul>
                    </section>
                `
                    : ""
            }

            ${
                idiomasValidos.length > 0
                    ? `
                    <section class="cv-section">
                        <h2 class="cv-section-title">Idiomas</h2>
                        <ul class="cv-inline-list">
                            ${idiomasValidos.map((idi) => `<li>${escaparHTML(idi)}</li>`).join("")}
                        </ul>
                    </section>
                `
                    : ""
            }
        </article>
    `;
}

// Dibuja el QR después de inyectar el HTML del CV en el DOM
function renderizarQRSiAplica() {
    const qrTarget = document.getElementById("cv-qr-target");
    if (!qrTarget) return;

    const url = qrTarget.getAttribute("data-qr-url");
    if (!url || !window.QRCode) return;

    qrTarget.innerHTML = "";
    new QRCode(qrTarget, {
        text: url,
        width: 152,
        height: 152,
        colorDark: "#202936",
        colorLight: "#FFFFFF",
        correctLevel: QRCode.CorrectLevel.M
    });
}