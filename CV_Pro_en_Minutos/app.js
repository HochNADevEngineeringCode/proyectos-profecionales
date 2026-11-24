/**
 * ============================================================================
 * ARCHIVO: app.js
 * DESCRIPCIÓN: Controla el flujo paso a paso ("Siguiente", "Omitir", "Anterior"),
 *              almacena las respuestas del usuario en memoria y llama a
 *              `generarHTMLPlantillaCV(datos)` al finalizar.
 * ============================================================================
 */

// 1. ESTADO CENTRAL DE LOS DATOS DEL USUARIO
const estadoCV = {
    vacante: "",
    nombreApellido: "",
    email: "",
    telefono: "",
    localidad: "",
    linkedin: "",
    github: "",
    perfil: "",
    experiencias: [
        { puesto: "", empresa: "", periodo: "", descripcion: "" }
    ],
    educaciones: [
        { titulo: "", institucion: "", periodo: "" }
    ],
    habilidadesTexto: "",
    idiomasTexto: "",
    fotoDataUrl: ""
};

let pasoActual = 0;

// 2. DEFINICIÓN DE LOS 7 PASOS DEL ASISTENTE
const PASOS = [
    {
        id: "vacante",
        titulo: "¿Cómo se llama la vacante laboral a la que querés aplicar?",
        ayuda: "Escribí el puesto o rubro objetivo (ej: Desarrollador Web Junior, Técnico Electricista, Chofer Profesional, Panadero).",
        permitirOmitir: true,
        renderizar: () => `
            <div class="field-group">
                <label class="field-label" for="input-vacante">Puesto o vacante objetivo</label>
                <input
                    type="text"
                    id="input-vacante"
                    class="field-input"
                    placeholder="Ej: Técnico en Mantenimiento Industrial"
                    value="${escaparAttr(estadoCV.vacante)}"
                >
            </div>
        `,
        guardar: () => {
            estadoCV.vacante = document.getElementById("input-vacante").value.trim();
        },
        limpiar: () => {
            estadoCV.vacante = "";
        }
    },
    {
        id: "contacto",
        titulo: "Completá tus datos básicos de contacto",
        ayuda: "Estos datos van en el encabezado de tu CV. Si dejás algún enlace vacío, no se mostrará.",
        permitirOmitir: false, // Este paso es la identidad base del CV
        renderizar: () => `
            <div class="field-grid">
                <div class="field-group full-width">
                    <label class="field-label" for="input-nombre">Nombre y Apellido *</label>
                    <input type="text" id="input-nombre" class="field-input" placeholder="Ej: Nahuel Hochnadel" value="${escaparAttr(estadoCV.nombreApellido)}" required>
                </div>

                <div class="field-group">
                    <label class="field-label" for="input-email">Correo electrónico</label>
                    <input type="email" id="input-email" class="field-input" placeholder="Ej: correo@ejemplo.com" value="${escaparAttr(estadoCV.email)}">
                </div>

                <div class="field-group">
                    <label class="field-label" for="input-telefono">Teléfono / WhatsApp</label>
                    <input type="text" id="input-telefono" class="field-input" placeholder="Ej: +54 343 534-9146" value="${escaparAttr(estadoCV.telefono)}">
                </div>

                <div class="field-group full-width">
                    <label class="field-label" for="input-localidad">Localidad / Provincia / País</label>
                    <input type="text" id="input-localidad" class="field-input" placeholder="Ej: Entre Ríos, Argentina" value="${escaparAttr(estadoCV.localidad)}">
                </div>

                <div class="field-group">
                    <label class="field-label" for="input-linkedin">Enlace de LinkedIn (opcional)</label>
                    <input type="text" id="input-linkedin" class="field-input" placeholder="https://linkedin.com/in/tu-perfil" value="${escaparAttr(estadoCV.linkedin)}">
                </div>

                <div class="field-group">
                    <label class="field-label" for="input-github">Enlace de GitHub o Web (opcional)</label>
                    <input type="text" id="input-github" class="field-input" placeholder="https://github.com/tu-usuario" value="${escaparAttr(estadoCV.github)}">
                </div>
            </div>
        `,
        guardar: () => {
            estadoCV.nombreApellido = document.getElementById("input-nombre").value.trim();
            estadoCV.email = document.getElementById("input-email").value.trim();
            estadoCV.telefono = document.getElementById("input-telefono").value.trim();
            estadoCV.localidad = document.getElementById("input-localidad").value.trim();
            estadoCV.linkedin = document.getElementById("input-linkedin").value.trim();
            estadoCV.github = document.getElementById("input-github").value.trim();
        },
        limpiar: () => {}
    },
    {
        id: "perfil",
        titulo: "Contanos cómo te ves en tu perfil profesional",
        ayuda: "Escribí 3 o 4 líneas resumiendo tu experiencia, tu forma de trabajar y qué aportás al puesto.",
        permitirOmitir: true,
        renderizar: () => `
            <div class="field-group">
                <label class="field-label" for="input-perfil">Resumen profesional</label>
                <textarea
                    id="input-perfil"
                    class="field-textarea"
                    placeholder="Ej: Profesional responsable con experiencia en diagnóstico técnico, resolución de problemas y trabajo en equipo..."
                >${escaparHTML(estadoCV.perfil)}</textarea>
            </div>
        `,
        guardar: () => {
            estadoCV.perfil = document.getElementById("input-perfil").value.trim();
        },
        limpiar: () => {
            estadoCV.perfil = "";
        }
    },
    {
        id: "experiencia",
        titulo: "¿Cuál es tu experiencia laboral?",
        ayuda: "Agregá tus trabajos anteriores o actuales. Si aún no tenés experiencia laboral, podés omitir este paso.",
        permitirOmitir: true,
        renderizar: () => {
            const itemsHTML = estadoCV.experiencias
                .map(
                    (exp, idx) => `
                    <div class="repeatable-item" data-exp-index="${idx}">
                        <div class="repeatable-header">
                            <span class="repeatable-badge">Experiencia #${idx + 1}</span>
                            ${
                                estadoCV.experiencias.length > 1
                                    ? `<button type="button" class="btn-remove-item" onclick="eliminarExperiencia(${idx})">Eliminar</button>`
                                    : ""
                            }
                        </div>
                        <div class="field-grid">
                            <div class="field-group">
                                <label class="field-label">Puesto / Rol</label>
                                <input type="text" class="field-input exp-puesto" placeholder="Ej: Técnico Electricista" value="${escaparAttr(exp.puesto)}">
                            </div>
                            <div class="field-group">
                                <label class="field-label">Período</label>
                                <input type="text" class="field-input exp-periodo" placeholder="Ej: 2023 – Actualidad" value="${escaparAttr(exp.periodo)}">
                            </div>
                            <div class="field-group full-width">
                                <label class="field-label">Empresa o modalidad</label>
                                <input type="text" class="field-input exp-empresa" placeholder="Ej: Empresa Industrial / Independiente" value="${escaparAttr(exp.empresa)}">
                            </div>
                            <div class="field-group full-width">
                                <label class="field-label">Tareas y logros principales</label>
                                <textarea class="field-textarea exp-desc" style="min-height: 75px;" placeholder="Ej: Mantenimiento preventivo, armado de tableros y resolución de fallas.">${escaparHTML(exp.descripcion)}</textarea>
                            </div>
                        </div>
                    </div>
                `
                )
                .join("");

            return `
                <div id="lista-experiencias">${itemsHTML}</div>
                <button type="button" class="btn-add-item" onclick="agregarExperiencia()">+ Agregar otra experiencia</button>
            `;
        },
        guardar: () => {
            const bloques = document.querySelectorAll("[data-exp-index]");
            estadoCV.experiencias = Array.from(bloques).map((bloque) => ({
                puesto: bloque.querySelector(".exp-puesto").value.trim(),
                periodo: bloque.querySelector(".exp-periodo").value.trim(),
                empresa: bloque.querySelector(".exp-empresa").value.trim(),
                descripcion: bloque.querySelector(".exp-desc").value.trim()
            }));
        },
        limpiar: () => {
            estadoCV.experiencias = [];
        }
    },
    {
        id: "educacion",
        titulo: "¿Qué estudios, cursos o certificaciones tenés?",
        ayuda: "Incluí escuela secundaria, tecnicaturas, carreras universitarias o cursos relevantes.",
        permitirOmitir: true,
        renderizar: () => {
            const itemsHTML = estadoCV.educaciones
                .map(
                    (edu, idx) => `
                    <div class="repeatable-item" data-edu-index="${idx}">
                        <div class="repeatable-header">
                            <span class="repeatable-badge">Formación #${idx + 1}</span>
                            ${
                                estadoCV.educaciones.length > 1
                                    ? `<button type="button" class="btn-remove-item" onclick="eliminarEducacion(${idx})">Eliminar</button>`
                                    : ""
                            }
                        </div>
                        <div class="field-grid">
                            <div class="field-group">
                                <label class="field-label">Título o certificación</label>
                                <input type="text" class="field-input edu-titulo" placeholder="Ej: Técnico Electromecánico" value="${escaparAttr(edu.titulo)}">
                            </div>
                            <div class="field-group">
                                <label class="field-label">Período o estado</label>
                                <input type="text" class="field-input edu-periodo" placeholder="Ej: 2018 – 2024 / En curso" value="${escaparAttr(edu.periodo)}">
                            </div>
                            <div class="field-group full-width">
                                <label class="field-label">Institución educativa</label>
                                <input type="text" class="field-input edu-institucion" placeholder="Ej: Escuela Técnica / ConquerBlocks" value="${escaparAttr(edu.institucion)}">
                            </div>
                        </div>
                    </div>
                `
                )
                .join("");

            return `
                <div id="lista-educaciones">${itemsHTML}</div>
                <button type="button" class="btn-add-item" onclick="agregarEducacion()">+ Agregar otro estudio o curso</button>
            `;
        },
        guardar: () => {
            const bloques = document.querySelectorAll("[data-edu-index]");
            estadoCV.educaciones = Array.from(bloques).map((bloque) => ({
                titulo: bloque.querySelector(".edu-titulo").value.trim(),
                periodo: bloque.querySelector(".edu-periodo").value.trim(),
                institucion: bloque.querySelector(".edu-institucion").value.trim()
            }));
        },
        limpiar: () => {
            estadoCV.educaciones = [];
        }
    },
    {
        id: "habilidades_idiomas",
        titulo: "¿Cuáles son tus habilidades e idiomas?",
        ayuda: "Separá cada habilidad o idioma con una coma (,). La plantilla los ordenará automáticamente con puntos separadores.",
        permitirOmitir: true,
        renderizar: () => `
            <div class="field-group">
                <label class="field-label" for="input-habilidades">Habilidades clave (separadas por coma)</label>
                <input
                    type="text"
                    id="input-habilidades"
                    class="field-input"
                    placeholder="Ej: Electricidad industrial, Python, SQL, Trabajo en equipo, Diagnóstico técnico"
                    value="${escaparAttr(estadoCV.habilidadesTexto)}"
                >
            </div>

            <div class="field-group">
                <label class="field-label" for="input-idiomas">Idiomas y nivel (separados por coma)</label>
                <input
                    type="text"
                    id="input-idiomas"
                    class="field-input"
                    placeholder="Ej: Español — Nativo, Inglés — Intermedio"
                    value="${escaparAttr(estadoCV.idiomasTexto)}"
                >
            </div>
        `,
        guardar: () => {
            estadoCV.habilidadesTexto = document.getElementById("input-habilidades").value.trim();
            estadoCV.idiomasTexto = document.getElementById("input-idiomas").value.trim();
        },
        limpiar: () => {
            estadoCV.habilidadesTexto = "";
            estadoCV.idiomasTexto = "";
        }
    },
    {
        id: "foto",
        titulo: "¿Querés agregar una foto para tu CV? (Opcional)",
        ayuda: "Te recomendamos una foto con fondo claro o neutro. Si preferís un CV sin foto, simplemente presioná Omitir paso.",
        permitirOmitir: true,
        renderizar: () => `
            <div class="photo-upload-box">
                ${
                    estadoCV.fotoDataUrl
                        ? `<img src="${estadoCV.fotoDataUrl}" alt="Vista previa" class="photo-preview-circle" id="preview-foto">`
                        : `<div id="contenedor-preview-foto"></div>`
                }
                <p style="margin: 0 0 12px; color: var(--ink-muted); font-size: 0.92rem;">
                    Seleccioná una imagen JPG o PNG desde tu dispositivo
                </p>
                <input type="file" id="input-foto" accept="image/png, image/jpeg, image/webp" onchange="procesarArchivoFoto(event)">
                ${
                    estadoCV.fotoDataUrl
                        ? `<div style="margin-top: 12px;"><button type="button" class="btn-remove-item" onclick="quitarFoto()">Quitar foto seleccionada</button></div>`
                        : ""
                }
            </div>
        `,
        guardar: () => {},
        limpiar: () => {
            estadoCV.fotoDataUrl = "";
        }
    }
];

// 3. FUNCIONES AUXILIARES PARA FORMULARIOS DINÁMICOS
function escaparAttr(texto) {
    if (!texto) return "";
    return String(texto)
        .replace(/&/g, "&amp;")
        .replace(/"/g, "&quot;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function agregarExperiencia() {
    PASOS[3].guardar();
    estadoCV.experiencias.push({ puesto: "", empresa: "", periodo: "", descripcion: "" });
    renderizarPasoActual();
}

function eliminarExperiencia(indice) {
    PASOS[3].guardar();
    estadoCV.experiencias.splice(indice, 1);
    renderizarPasoActual();
}

function agregarEducacion() {
    PASOS[4].guardar();
    estadoCV.educaciones.push({ titulo: "", institucion: "", periodo: "" });
    renderizarPasoActual();
}

function eliminarEducacion(indice) {
    PASOS[4].guardar();
    estadoCV.educaciones.splice(indice, 1);
    renderizarPasoActual();
}

function procesarArchivoFoto(evento) {
    const archivo = evento.target.files[0];
    if (!archivo) return;

    const lector = new FileReader();
    lector.onload = (e) => {
        estadoCV.fotoDataUrl = e.target.result;
        renderizarPasoActual();
    };
    lector.readAsDataURL(archivo);
}

function quitarFoto() {
    estadoCV.fotoDataUrl = "";
    renderizarPasoActual();
}

// 4. CONTROL DE NAVEGACIÓN ENTRE VISTAS Y PASOS
function mostrarVista(nombreVista) {
    document.getElementById("vista-inicio").classList.toggle("hidden", nombreVista !== "inicio");
    document.getElementById("vista-asistente").classList.toggle("hidden", nombreVista !== "asistente");
    document.getElementById("vista-resultado").classList.toggle("hidden", nombreVista !== "resultado");

    document.getElementById("nav-inicio").classList.toggle("active", nombreVista === "inicio");
}

function iniciarAsistente() {
    pasoActual = 0;
    // Aseguramos al menos una fila vacía en experiencia y educación si fueron limpiadas
    if (estadoCV.experiencias.length === 0) {
        estadoCV.experiencias = [{ puesto: "", empresa: "", periodo: "", descripcion: "" }];
    }
    if (estadoCV.educaciones.length === 0) {
        estadoCV.educaciones = [{ titulo: "", institucion: "", periodo: "" }];
    }
    mostrarVista("asistente");
    renderizarPasoActual();
}

function renderizarPasoActual() {
    const paso = PASOS[pasoActual];
    const totalPasos = PASOS.length;
    const porcentaje = Math.round(((pasoActual + 1) / totalPasos) * 100);

    document.getElementById("texto-paso").textContent = `Paso ${pasoActual + 1} de ${totalPasos}`;
    document.getElementById("porcentaje-paso").textContent = `${porcentaje}%`;
    document.getElementById("barra-progreso").style.width = `${porcentaje}%`;

    const contenedor = document.getElementById("contenedor-pregunta");
    contenedor.innerHTML = `
        <h2 class="step-question">${paso.titulo}</h2>
        <p class="step-hint">${paso.ayuda}</p>
        ${paso.renderizar()}
    `;

    // Control de visibilidad de botones Anterior, Omitir y Siguiente
    document.getElementById("btn-anterior").disabled = pasoActual === 0;
    document.getElementById("btn-omitir").classList.toggle("hidden", !paso.permitirOmitir);

    const btnSiguiente = document.getElementById("btn-siguiente");
    btnSiguiente.textContent = pasoActual === totalPasos - 1 ? "Finalizar y ver CV ✓" : "Siguiente →";
}

function avanzarPaso() {
    if (pasoActual < PASOS.length - 1) {
        pasoActual++;
        renderizarPasoActual();
    } else {
        construirYMostrarCVFinal();
    }
}

// Completa automáticamente períodos incompletos como "2024" o "2024-" -> "2024 – Presente"
function normalizarPeriodo(textoPeriodo) {
    const limpio = (textoPeriodo || "").trim();
    if (!limpio) return "";

    // Caso 1: Solo un año (ej: "2024")
    if (/^\d{4}$/.test(limpio)) {
        return `${limpio} – Presente`;
    }

    // Caso 2: Año seguido de guion sin fecha final (ej: "2024-", "2024 -", "2024–")
    const matchInicioSolo = limpio.match(/^(\d{4})\s*[-–—]\s*$/);
    if (matchInicioSolo) {
        return `${matchInicioSolo[1]} – Presente`;
    }

    // Caso 3: Rango con guion (ej: "2024-2026" o "2024 - 2027") -> lo prolija con " – "
    const matchRango = limpio.match(/^(.+?)\s*[-–—]\s*(.+)$/);
    if (matchRango) {
        return `${matchRango[1].trim()} – ${matchRango[2].trim()}`;
    }

    return limpio;
}

function construirYMostrarCVFinal() {
    // Convertimos los textos separados por coma en arrays limpios
    const habilidadesArray = estadoCV.habilidadesTexto
        ? estadoCV.habilidadesTexto.split(",").map((item) => item.trim()).filter(Boolean)
        : [];

    const idiomasArray = estadoCV.idiomasTexto
        ? estadoCV.idiomasTexto.split(",").map((item) => item.trim()).filter(Boolean)
        : [];

    // Aplicamos normalización de períodos (ej: "2024" -> "2024 – Presente")
    const experienciasNormalizadas = (estadoCV.experiencias || []).map((exp) => ({
        ...exp,
        periodo: normalizarPeriodo(exp.periodo)
    }));

    const educacionesNormalizadas = (estadoCV.educaciones || []).map((edu) => ({
        ...edu,
        periodo: normalizarPeriodo(edu.periodo)
    }));

    const datosPreparados = {
        ...estadoCV,
        experiencias: experienciasNormalizadas,
        educaciones: educacionesNormalizadas,
        habilidades: habilidadesArray,
        idiomas: idiomasArray
    };

    // Llamamos al módulo reemplazable `plantilla_cv.js`
    const contenedorCV = document.getElementById("contenedor-cv-final");
    contenedorCV.innerHTML = generarHTMLPlantillaCV(datosPreparados);
    if (typeof renderizarQRSiAplica === "function") {
        renderizarQRSiAplica();
    }
    mostrarVista("resultado");
}

// Imprime o exporta a PDF asegurando que la hoja A4 nunca salga en blanco
function imprimirOGuardarCV() {
    const hojaCV = document.querySelector("#contenedor-cv-final .cv-sheet");
    if (!hojaCV) {
        window.print();
        return;
    }

    // Creamos un contenedor limpio exclusivo para impresión
    const zonaImpresion = document.createElement("div");
    zonaImpresion.id = "zona-impresion-temporal";
    zonaImpresion.innerHTML = document.getElementById("contenedor-cv-final").innerHTML;

    // Ocultamos temporalmente la interfaz web y dejamos visible solo la hoja del CV
    const elementosWeb = Array.from(document.body.children);
    elementosWeb.forEach((el) => {
        el.dataset.prevDisplay = el.style.display;
        el.style.display = "none";
    });

    document.body.appendChild(zonaImpresion);

    window.print();

    // Restauramos toda la interfaz web al cerrar la ventana de impresión
    zonaImpresion.remove();
    elementosWeb.forEach((el) => {
        el.style.display = el.dataset.prevDisplay || "";
        delete el.dataset.prevDisplay;
    });
}

// 5. EVENTOS PRINCIPALES AL CARGAR LA PÁGINA
document.addEventListener("DOMContentLoaded", () => {
    // Botones que llevan a la pantalla de inicio
    document.getElementById("btn-logo-inicio").addEventListener("click", (e) => {
        e.preventDefault();
        mostrarVista("inicio");
    });
    document.getElementById("nav-inicio").addEventListener("click", () => mostrarVista("inicio"));

    // Botones que inician el asistente
    document.getElementById("nav-comenzar").addEventListener("click", iniciarAsistente);
    document.getElementById("btn-hero-comenzar").addEventListener("click", iniciarAsistente);

    // Botón Anterior
    document.getElementById("btn-anterior").addEventListener("click", () => {
        if (pasoActual > 0) {
            PASOS[pasoActual].guardar();
            pasoActual--;
            renderizarPasoActual();
        }
    });

    // Botón Omitir paso (limpia los datos de ese paso para que no salgan en el CV)
    document.getElementById("btn-omitir").addEventListener("click", () => {
        PASOS[pasoActual].limpiar();
        avanzarPaso();
    });

    // Envío del formulario (Botón Siguiente / Finalizar)
    document.getElementById("formulario-paso").addEventListener("submit", (e) => {
        e.preventDefault();
        const form = e.target;
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        PASOS[pasoActual].guardar();
        avanzarPaso();
    });

    // Botones de la vista final del CV
    document.getElementById("btn-volver-editar").addEventListener("click", () => {
        mostrarVista("asistente");
        renderizarPasoActual();
    });

    document.getElementById("btn-descargar-pdf").addEventListener("click", () => {
        alert("En la ventana que se abrirá, elegí 'Guardar como PDF' (o 'Microsoft Print to PDF') y apretá Guardar.");
        imprimirOGuardarCV();
    });

    document.getElementById("btn-imprimir-cv").addEventListener("click", () => {
        imprimirOGuardarCV();
    });
});