import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import math
import time
import config

# =============================================================================
# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTILOS
# =============================================================================
st.set_page_config(page_title="Flujo Multifásico", layout="wide")
st.title("Flujo Multifásico")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap');
    html, body, [class*="css"] { font-family: 'Crimson Text', serif; font-size: 19px; }
    h1, h2, h3, h4 { color: #1a6bbf; font-weight: 600; }
    .stMetric label { font-size: 16px !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. FUNCIONES DE LÓGICA
# =============================================================================
def calcular_fisica_fluido(vel, rad, rho_s, nombre_fluido):
    g = config.GRAVEDAD
    D = config.DIAMETRO_TUBERIA
    
    propiedades = config.BASE_FLUIDOS[nombre_fluido]
    rho_f = propiedades["rho_f"]
    mu = propiedades["mu"]
    nu = propiedades["nu"]
    
    r = rad * 1e-3
    drho = rho_s - rho_f
    abs_drho = abs(drho)

    Wp_stokes = (2/9) * g * (r**2) * abs_drho / mu
    Re_p0 = 2 * r * Wp_stokes / nu
    Wp_mag = Wp_stokes / (1 + 0.15 * (Re_p0**0.687)) if Re_p0 > 0.5 else Wp_stokes
    
    Wp = np.sign(drho) * Wp_mag
    Re_p_real = 2 * r * Wp_mag / nu

    Re_D = max(1, vel * D / nu)
    if Re_D > 4000: f = 0.316 / (Re_D**0.25)
    elif Re_D > 2300: f = 0.025
    else: f = 64 / Re_D

    u_star = vel * math.sqrt(f / 8)
    Wt = 2.5 * u_star
    ratio = Wp_mag / Wt if Wt > 0 else 999

    if ratio < 0.35:
        regimen = {"name": "Homogéneo", "color": config.COLOR_HOMOGENEO, "desc": "Suspensión total. Partículas en líneas rectas por todo el tubo."}
    elif ratio < 1.2:
        regimen = {"name": "Heterogéneo", "color": config.COLOR_HETEROGENEO, "desc": "Líneas rectas concentradas hacia una zona del tubo."}
    elif ratio < 2.5:
        regimen = {"name": "Saltación", "color": config.COLOR_SALTACION, "desc": "Partículas avanzan rebotando en el tubo."}
    else:
        regimen = {"name": "Lecho Estático", "color": config.COLOR_LECHO, "desc": "Depósito estacionario en el fondo o techo."}

    return Wp, Wt, ratio, Re_p_real, Re_D, f, drho, regimen

# =============================================================================
# 3. INTERFAZ DE USUARIO
# =============================================================================
st.title("Simulador de Flujo Multifásico Sólido-Líquido")

st.sidebar.header("Condiciones de Operación")

lista_fluidos = list(config.BASE_FLUIDOS.keys())
fluido_seleccionado = st.sidebar.selectbox("Fluido Portador", lista_fluidos)

st.sidebar.markdown("---")
vel = st.sidebar.slider("Velocidad de Flujo ($v$) [m/s]", 0.1, 4.0, 1.2, 0.1)
conc = st.sidebar.slider("Concentración de Sólidos (%)", 5, 55, 20, 1)
rad = st.sidebar.slider("Radio de Partícula ($r_p$) [mm]", 0.1, 2.5, 0.5, 0.1)

st.sidebar.markdown("---")
st.sidebar.subheader("Propiedades de la Partícula")
rho_s = st.sidebar.number_input("Densidad del Sólido ($\\rho_s$) [kg/m³]", min_value=100.0, max_value=8000.0, value=2650.0, step=50.0)

# =============================================================================
# 4. EJECUCIÓN Y VISUALIZACIÓN
# =============================================================================
Wp, Wt, ratio, Re_p_real, Re_D, f, drho_calculado, regimen = calcular_fisica_fluido(vel, rad, rho_s, fluido_seleccionado)

tab_diseno, tab_calculos = st.tabs(["🎨 Simulación e Hidráulica", "🧮 Memoria de Cálculo"])

with tab_diseno:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Sedimentación ($W_p$)", f"{Wp:.4f} m/s")
    col2.metric("Turbulencia ($W_t$)", f"{Wt:.4f} m/s")
    col3.metric("Relación ($W_p / W_t$)", f"{ratio:.3f}")
    col4.metric("Régimen Previsto", regimen["name"])

    st.markdown(f"#### <span style='color:{regimen['color']}'>{regimen['name']}</span>", unsafe_allow_html=True)
    st.info(regimen["desc"])
    
    # -------------------------------------------------------------------------
    # MOTOR DE FÍSICA LAMINAR RÍGIDO CON BOTÓN DE PAUSA
    # -------------------------------------------------------------------------
    html_canvas = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{ box-sizing: border-box; }}
            body {{ margin: 0; padding: 4px; overflow: hidden; font-family: sans-serif; }}

            .wrapper {{
                display: flex;
                flex-direction: column;
                gap: 8px;
                width: calc(100% - 8px);
            }}

            .container {{ position: relative; width: 100%; height: 240px; }}
            canvas {{
                background-color: #e6e9f2;
                border: 3px solid #4a5575;
                border-radius: 8px;
                width: 100%; height: 100%;
                display: block;
            }}
            #ctrlBtn {{
                position: absolute; top: 12px; right: 12px; z-index: 10;
                padding: 10px 20px; font-weight: bold; font-size: 15px;
                cursor: pointer; color: white;
                border: none; border-radius: 6px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                transition: background-color 0.4s ease, transform 0.1s ease;
            }}
            #ctrlBtn:active {{ transform: scale(0.95); }}
            #ctrlBtn.running {{ background-color: #e74c3c; }}
            #ctrlBtn.paused  {{ background-color: #2ecc71; }}
        </style>
    </head>
    <body>
        <div class="wrapper">

            <div class="container">
                <button id="ctrlBtn" class="running" onclick="toggleSim()">⏸ DETENER</button>
                <canvas id="simCanvas"></canvas>
            </div>
        </div>

        <script>
            const canvas = document.getElementById('simCanvas');
            const ctx = canvas.getContext('2d');
            canvas.width  = canvas.clientWidth;
            canvas.height = canvas.clientHeight;

            let vel_base = {vel * 4};
            let n_target = {min(500, int(conc * 12))};
            let radius   = Math.max(2, {rad * 4});

            const color        = "{regimen['color']}";
            const drho         = {drho_calculado};
            const regimen_name = "{regimen['name']}";
            const gravity_dir  = drho > 0 ? 1 : -1;

            // ── Transición suave de velocidad ──────────────────────────────
            // flowFactor va de 0 (detenido) a 1 (corriendo) de forma gradual
            let flowFactor  = 1.0;
            let targetFlow  = 1.0;
            const ACCEL     = 0.018;   // suavidad de arranque/parada

            let isPaused = false;
            function toggleSim() {{
                isPaused  = !isPaused;
                targetFlow = isPaused ? 0.0 : 1.0;
                const btn = document.getElementById('ctrlBtn');
                if (isPaused) {{
                    btn.innerText  = "▶ CORRER";
                    btn.className  = "paused";
                }} else {{
                    btn.innerText  = "⏸ DETENER";
                    btn.className  = "running";
                }}
            }}

            // ── Perfil de velocidad parabólico (flujo de Poiseuille) ────────
            // Devuelve un factor 0-1 según la posición vertical normalizada
            function poiseuilleProfile(y) {{
                const H  = canvas.height;
                const yn = (y / H) * 2 - 1;   // -1 (techo) … +1 (piso)
                return Math.max(0, 1 - yn * yn);
            }}

            // ── Turbulencia suave tipo Perlin simplificado ──────────────────
            // Usamos una suma de senos desfasados para cada partícula
            function turbulenceY(p, t) {{
                return  Math.sin(p.phase + t * 0.8)  * 0.6
                      + Math.sin(p.phase * 1.7 + t * 1.4) * 0.3;
            }}

            // ── Crear partículas ────────────────────────────────────────────
            function makeParticle() {{
                let initY;
                if (regimen_name === "Homogéneo") {{
                    initY = radius + Math.random() * (canvas.height - 2 * radius);
                }} else if (regimen_name === "Heterogéneo") {{
                    const bias = Math.random();
                    initY = gravity_dir > 0
                        ? canvas.height - radius - bias * bias * (canvas.height * 0.55)
                        : radius + bias * bias * (canvas.height * 0.55);
                }} else if (regimen_name === "Saltación") {{
                    // En saltación: muchas partículas forman un lecho y pocas saltan
                    const bedThickness = canvas.height * 0.18;
                    initY = gravity_dir > 0
                        ? canvas.height - radius - Math.random() * bedThickness
                        : radius + Math.random() * bedThickness;
                }} else {{
                    initY = gravity_dir > 0
                        ? canvas.height - radius - Math.random() * (canvas.height * 0.25)
                        : radius + Math.random() * (canvas.height * 0.25);
                }}
                // Arcos muy achatados: máximo 12% de la altura del canal
                const arcFraction = (regimen_name === "Saltación") ? 0.03 + Math.random() * 0.09 : 0;
                const gravAcc = 0.18;   // gravedad alta → caída rápida → parábola achatada
                const arcHeight = arcFraction * (canvas.height - 2 * radius);
                const initVy = (regimen_name === "Saltación")
                    ? -gravity_dir * Math.sqrt(2 * gravAcc * arcHeight) * (0.8 + Math.random() * 0.2)
                    : 0;
                return {{
                    x: Math.random() * canvas.width,
                    y: initY,
                    laneY: initY,
                    vx: 0,
                    vy: initVy,
                    phase: Math.random() * Math.PI * 2,
                    arcFrac: arcFraction,
                    onGround: false,
                    // Solo una parte de las partículas salta; el resto forma el lecho.
                    // Cambia 0.18 a 0.25 si quieres más partículas saltando.
                    isJumper: regimen_name === "Saltación" ? Math.random() < 0.18 : true
                }};
            }}

            let particles = [];
            for (let i = 0; i < n_target; i++) {{
                particles.push(makeParticle());
            }}

            // dummy empty loop (legacy, no ejecuta)
            for (let i = 0; i < 0; i++) {{
                particles.push(makeParticle());
            }}

            // ── Loop principal ──────────────────────────────────────────────
            let t = 0;
            function animate() {{
                // Interpolación exponencial suave de flowFactor
                flowFactor += (targetFlow - flowFactor) * ACCEL;
                t += 0.016 * flowFactor;   // el tiempo interno se congela al parar

                ctx.clearRect(0, 0, canvas.width, canvas.height);

                // Etiqueta de estado con fade-in suave
                const stateLabel = (flowFactor < 0.05)
                    ? "DETENIDO (Gravedad)"
                    : (flowFactor < 0.95 ? "..." : regimen_name.toUpperCase());
                ctx.globalAlpha = 1;
                ctx.fillStyle   = "rgba(74, 85, 117, 0.8)";
                ctx.font        = "bold 22px Arial";
                ctx.fillText("ESTADO: " + stateLabel, 15, 35);

                // Ajuste dinámico de cantidad de partículas
                while (particles.length < n_target) particles.push(makeParticle());
                while (particles.length > n_target) particles.pop();

                for (let i = 0; i < particles.length; i++) {{
                    const p  = particles[i];
                    const ff = flowFactor;           // alias corto

                    // ── Velocidad horizontal ────────────────────────────────
                    let vxTarget = 0;
                    if (regimen_name !== "Lecho Estático") {{
                        const profile = poiseuilleProfile(p.y);
                        vxTarget = vel_base * profile * ff;
                        // Saltación: las partículas van algo más lentas
                        if (regimen_name === "Saltación") vxTarget *= 0.7;
                    }}
                    // Suavizar aceleración horizontal (inercia propia)
                    if (typeof p.vx === "undefined") p.vx = 0;
                    p.vx += (vxTarget - p.vx) * 0.07;

                    // ── Velocidad vertical según régimen ────────────────────
                    // ff=1 → flujo completo; ff=0 → detenido (gravedad domina)
                    // Al detener: caen (gravity_dir=1) o flotan (gravity_dir=-1)
                    // Al reanudar: vuelven a su laneY con el flujo

                    if (regimen_name === "Homogéneo") {{
                        // Corriendo: turbulencia suave centrada en laneY
                        // Detenido: caen/flotan por gravedad pura
                        const turb     = turbulenceY(p, t) * ff;
                        const restoreK = 0.06 * ff;          // restaurar carril solo al correr
                        const gravity  = gravity_dir * 0.55 * (1 - ff);
                        p.vy += gravity;
                        p.vy += (p.laneY - p.y) * restoreK + turb * 1.2;
                        p.vy *= 0.85;  // amortiguación

                    }} else if (regimen_name === "Heterogéneo") {{
                        const turb     = turbulenceY(p, t) * ff * 0.6;
                        const restoreK = 0.05 * ff;
                        const gravity  = gravity_dir * 0.6 * (1 - ff);
                        p.vy += gravity;
                        p.vy += (p.laneY - p.y) * restoreK + turb;
                        p.vy *= 0.85;

                    }} else if (regimen_name === "Saltación") {{
                        const gravAcc = 0.18;

                        if (p.isJumper) {{
                            // Pocas partículas saltan sobre el lecho.
                            const grav = gravity_dir * gravAcc * ff + gravity_dir * 0.25 * (1 - ff);
                            p.vy += grav;
                            p.vy *= 0.994;
                        }} else {{
                            // La mayoría queda como lecho: pegada al fondo y con movimiento lento.
                            const bedY = gravity_dir > 0 ? canvas.height - radius : radius;
                            p.y += (bedY - p.y) * 0.08;
                            p.vy *= 0.4;
                        }}

                    }} else {{
                        // Lecho Estático: siempre caen, vibración leve al correr
                        const vibration = Math.sin(p.phase + t * 3) * ff * 0.3;
                        p.vy += gravity_dir * 0.6 + vibration;
                        p.vy *= 0.92;
                    }}

                    // ── Mover ───────────────────────────────────────────────
                    p.x += p.vx;
                    p.y += p.vy;

                    // ── Colisión piso / techo ───────────────────────────────
                    const floor   = canvas.height - radius;
                    const ceiling = radius;
                    if (p.y >= floor) {{
                        p.y = floor;
                        if (regimen_name === "Saltación") {{
                            if (p.isJumper && ff > 0.05) {{
                                const gravAcc = 0.18;
                                const arcH    = p.arcFrac * (canvas.height - 2 * radius);
                                const launchV = Math.sqrt(2 * gravAcc * arcH) * Math.sqrt(ff);
                                p.vy = -Math.abs(launchV) * gravity_dir;
                            }} else {{
                                p.vy = 0;
                            }}
                        }} else {{
                            p.vy *= -0.15;
                        }}
                    }} else if (p.y <= ceiling) {{
                        p.y = ceiling;
                        if (regimen_name === "Saltación") {{
                            if (p.isJumper && ff > 0.05) {{
                                const gravAcc = 0.18;
                                const arcH    = p.arcFrac * (canvas.height - 2 * radius);
                                const launchV = Math.sqrt(2 * gravAcc * arcH) * Math.sqrt(ff);
                                p.vy = Math.abs(launchV) * gravity_dir * -1;
                            }} else {{
                                p.vy = 0;
                            }}
                        }} else {{
                            p.vy *= -0.15;
                        }}
                    }}

                    // ── Reaparecer por la izquierda ─────────────────────────
                    if (p.x > canvas.width + radius) {{
                        p.x = -radius;
                        // Al reentrar, resetear posición vertical al carril
                        if (regimen_name === "Homogéneo" || regimen_name === "Heterogéneo") {{
                            p.y  = p.laneY;
                            p.vy = 0;
                        }}
                    }}

                    // ── Dibujar ─────────────────────────────────────────────
                    ctx.globalAlpha = 0.82 + 0.08 * ff;
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
                    ctx.fillStyle = color;
                    ctx.fill();
                }}

                ctx.globalAlpha = 1;
                requestAnimationFrame(animate);
            }}

            animate();
        </script>
    </body>
    </html>
    """
    
    components.html(html_canvas, height=430)

with tab_calculos:
    props = config.BASE_FLUIDOS[fluido_seleccionado]
    
    st.subheader(f"Auditoría del Fluido: {fluido_seleccionado}")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"**Densidad ($\\rho_f$):** `{props['rho_f']} kg/m³`")
    c2.markdown(f"**Viscosidad ($\\mu$):** `{props['mu']} Pa·s`")
    c3.markdown(f"**Diferencial ($\\Delta\\rho$):** `{drho_calculado} kg/m³`")
    c4.markdown(f"**Reynolds de Tubería ($Re_D$):** `{Re_D:.0f}`")
    
    st.markdown("---")
    st.markdown("#### Corrección de Arrastre de Schiller-Naumann")
    st.latex(r'W_{p, \text{stokes}} = \frac{2}{9} \frac{g \cdot r_p^2 \cdot |\rho_s - \rho_f|}{\mu}')
    st.latex(r'W_t = 2.5 \cdot v \cdot \sqrt{\frac{f}{8}}')
    st.markdown("---")
    st.markdown("#### Criterio de Estabilidad Numérica")
    st.latex(r'Re_p = \frac{2 \cdot r_p \cdot W_p}{\nu}')
    