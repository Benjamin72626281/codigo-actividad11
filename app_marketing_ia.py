# -*- coding: utf-8 -*-
"""
ACTIVIDAD 11. SISTEMAS INTELIGENTES II
Uso de dos APIs de IA generativa (Gemini y Groq) con Dash

Aplicacion: Asesor Basico de Marketing
Con el nombre, giro y publico de una empresa, la app le hace la misma pregunta de marketing a
Gemini (Google) y a Groq y muestra las dos respuestas en texto, una junto a la otra.
Todo corre en tu computadora; solo las respuestas de las IAs vienen de internet.

Instalacion:  pip install dash requests google-genai
Llaves:       GEMINI_API_KEY  (https://aistudio.google.com/apikey)
              GROQ_API_KEY    (https://console.groq.com/keys)
              Se guardan como variables de entorno, o se pegan abajo entre comillas (solo pruebas).
Ejecucion:    python app_marketing_ia.py      y abrir http://127.0.0.1:8050/
"""
import os
import time
from concurrent.futures import ThreadPoolExecutor

import dash
import requests
from dash import Input, Output, State, dcc, html

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
MODELOS_GEMINI = [os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"), "gemini-3.6-flash"]
MODELO_GROQ = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
URL_GROQ = "https://api.groq.com/openai/v1/chat/completions"

TIPOS = {
    "publicaciones": "5 ideas de publicaciones para redes sociales, con el texto sugerido",
    "slogan": "3 opciones de slogan y el mensaje principal de la marca",
    "promociones": "5 ideas de promociones u ofertas para atraer clientes",
    "plan": "un plan basico de marketing para el primer mes, semana por semana",
}

# =============================================================================
# 1. FUNCIONES (prompt y llamadas a las dos APIs)
# =============================================================================
def construir_prompt(negocio, giro, publico, tipo):
    """Arma la pregunta; es la misma para las dos IAs para poder compararlas."""
    return (f"Eres un asesor de marketing para pequenas empresas de Mexico. "
            f"Responde en espanol, con lenguaje sencillo, en maximo 200 palabras y con lista numerada.\n"
            f"Negocio: {negocio}\nA que se dedica: {giro}\nPublico objetivo: {publico}\n"
            f"Dame {TIPOS[tipo]}.")


def llamar_gemini(prompt, api_key):
    """Pregunta a Gemini con la libreria google-genai. Si esta saturado (503) reintenta
    y despues prueba con el modelo de respaldo. Regresa (texto, modelo)."""
    from google import genai
    from google.genai.errors import APIError

    cliente = genai.Client(api_key=api_key)
    for modelo in MODELOS_GEMINI:
        for intento in range(2):
            try:
                respuesta = cliente.models.generate_content(model=modelo, contents=prompt)
                return respuesta.text, modelo
            except APIError as error:
                if error.code not in (429, 503):
                    raise
                time.sleep(2 * (intento + 1))
    raise RuntimeError("Gemini esta saturado. Intenta de nuevo en un minuto.")


def llamar_groq(prompt, api_key):
    """Pregunta a Groq con una peticion HTTP compatible con la API de OpenAI.
    Regresa (texto, modelo)."""
    cabeceras = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                 "User-Agent": "actividad11-marketing/1.0"}
    cuerpo = {"model": MODELO_GROQ, "messages": [{"role": "user", "content": prompt}],
              "temperature": 0.7, "max_tokens": 500}
    for intento in range(3):
        r = requests.post(URL_GROQ, headers=cabeceras, json=cuerpo, timeout=30)
        if r.status_code in (429, 502, 503) and intento < 2:
            time.sleep(2 * (intento + 1))
            continue
        if r.status_code != 200:
            raise RuntimeError(f"Groq respondio {r.status_code}: {r.text[:200]}")
        return r.json()["choices"][0]["message"]["content"], MODELO_GROQ


def consultar(nombre, funcion, llave, prompt, variable):
    """Llama a una API y regresa un diccionario con el texto o con el error (sin romper la app)."""
    llave = (llave or "").strip()
    if not llave:
        return {"error": f"Falta la API key de {nombre} (variable {variable})."}
    if not llave.isascii():
        return {"error": f"La API key de {nombre} tiene caracteres raros. Copiala de nuevo."}
    inicio = time.time()
    try:
        texto, modelo = funcion(prompt, llave)
        return {"texto": texto, "modelo": modelo, "seg": round(time.time() - inicio, 1)}
    except Exception as e:  # llave incorrecta, sin internet, cuota agotada, etc.
        return {"error": f"No se pudo obtener la respuesta de {nombre}: {e}"}


# =============================================================================
# 2. INTERFAZ
# =============================================================================
CAJA = {"background": "white", "borderRadius": "10px", "padding": "14px", "minHeight": "200px"}


def control(etiqueta, componente, ancho):
    return html.Div([html.Label(etiqueta, style={"fontSize": "13px", "color": "#333"}), componente],
                    style={"width": ancho})


app = dash.Dash(__name__, title="Asesor Basico de Marketing")
server = app.server

app.layout = html.Div(style={"fontFamily": "Arial, sans-serif", "background": "#f1f4f9",
                             "padding": "20px", "minHeight": "100vh"}, children=[
    html.H1("Asesor Básico de Marketing", style={"textAlign": "center", "color": "#1d3557",
                                                 "marginBottom": "0"}),
    html.P("Actividad 11. Sistemas Inteligentes II. Gemini y Groq",
           style={"textAlign": "center", "color": "#457b9d", "marginTop": "4px"}),

    html.Div(style={"background": "white", "padding": "16px", "borderRadius": "10px",
                    "marginBottom": "16px"}, children=[
        html.Div(style={"display": "flex", "gap": "18px", "flexWrap": "wrap", "alignItems": "flex-end"},
                 children=[
            control("Nombre del negocio", dcc.Input(id="negocio", value="Café La Parroquia Verde",
                                                    style={"width": "100%"}), "240px"),
            control("A qué se dedica", dcc.Input(id="giro", style={"width": "100%"},
                    value="Café de especialidad, pan artesanal y postres"), "340px"),
            control("Público objetivo", dcc.Input(id="publico", style={"width": "100%"},
                    value="Universitarios de 18 a 30 años"), "280px"),
            control("¿Qué necesitas?", dcc.Dropdown(id="tipo", value="publicaciones", clearable=False,
                    options=[{"label": "Ideas de publicaciones", "value": "publicaciones"},
                             {"label": "Slogan y mensaje", "value": "slogan"},
                             {"label": "Promociones", "value": "promociones"},
                             {"label": "Plan básico del mes", "value": "plan"}]), "240px"),
            html.Button("Pedir sugerencias", id="btn", n_clicks=0, style={
                "background": "#1d3557", "color": "white", "border": "none", "padding": "10px 26px",
                "borderRadius": "6px", "cursor": "pointer", "fontSize": "15px"}),
        ]),
        html.Div(id="aviso", style={"fontSize": "13px", "color": "#b5651d", "marginTop": "8px"}),
    ]),

    dcc.Loading(children=html.Div(style={"display": "grid", "gap": "14px",
                                         "gridTemplateColumns": "repeat(auto-fit, minmax(420px, 1fr))"},
                                  children=[html.Div(id="res-gemini", style=CAJA),
                                            html.Div(id="res-groq", style=CAJA)])),
])


# =============================================================================
# 3. CALLBACK
# =============================================================================
def caja(nombre, r):
    """Dibuja el resultado de una IA: titulo con modelo y tiempo, y el texto (o el error)."""
    if "error" in r:
        return [html.H3(nombre), html.P(r["error"], style={"color": "#b5651d"})]
    return [html.H3(nombre), html.Div(f"{r['modelo']} · {r['seg']} s", style={"color": "#666", "fontSize": "13px"}),
            dcc.Markdown(r["texto"])]


@app.callback(Output("res-gemini", "children"), Output("res-groq", "children"), Output("aviso", "children"),
              Input("btn", "n_clicks"),
              State("negocio", "value"), State("giro", "value"), State("publico", "value"),
              State("tipo", "value"), prevent_initial_call=True)
def pedir_sugerencias(n_clicks, negocio, giro, publico, tipo):
    if not (negocio and giro and publico):
        return [], [], "Llena el nombre, a qué se dedica y el público objetivo."
    prompt = construir_prompt(negocio, giro, publico, tipo)
    with ThreadPoolExecutor(max_workers=2) as pool:  # las dos IAs responden al mismo tiempo
        f_gemini = pool.submit(consultar, "Gemini", llamar_gemini, GEMINI_API_KEY, prompt, "GEMINI_API_KEY")
        f_groq = pool.submit(consultar, "Groq", llamar_groq, GROQ_API_KEY, prompt, "GROQ_API_KEY")
        r_gemini, r_groq = f_gemini.result(), f_groq.result()
    return caja("Gemini (Google)", r_gemini), caja("Groq", r_groq), ""


# =============================================================================
# 4. EJECUCION
# =============================================================================
if __name__ == "__main__":
    app.run(debug=False, port=8050)
