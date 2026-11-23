# -*- coding: utf-8 -*-
"""Pruebas de la Actividad 11. No usan internet ni API keys: se simulan las respuestas de las IAs.
Ejecutar:  python pruebas_app.py"""
import sys
import time
import types

import app_marketing_ia as m

time.sleep = lambda s: None  # para que los reintentos no tarden
resultados = []


def prueba(nombre, condicion):
    resultados.append(bool(condicion))
    print(("OK   " if condicion else "FALLA"), nombre)


def texto_de(componentes):
    return str(componentes)


# 1. Prompt
p = m.construir_prompt("Café X", "vende café", "jóvenes", "slogan")
prueba("prompt con negocio, giro, público y tipo", all(x in p for x in ("Café X", "vende café", "jóvenes", "slogan")))
prueba("el prompt cambia según lo que se pide", m.construir_prompt("A", "b", "c", "plan") != m.construir_prompt("A", "b", "c", "slogan"))

# 2. consultar()
ok = m.consultar("Gemini", lambda pr, k: ("hola", "modelo-x"), "llave", "pregunta", "GEMINI_API_KEY")
prueba("consultar: respuesta correcta", ok["texto"] == "hola" and ok["modelo"] == "modelo-x" and "seg" in ok)
prueba("consultar: sin llave avisa", "Falta la API key" in m.consultar("Groq", None, "", "p", "GROQ_API_KEY")["error"])
prueba("consultar: llave con caracteres raros avisa", "caracteres" in m.consultar("Groq", None, "llavé", "p", "GROQ_API_KEY")["error"])


def falla(pr, k):
    raise RuntimeError("401 llave incorrecta")


prueba("consultar: error de la API no rompe", "401" in m.consultar("Gemini", falla, "llave", "p", "G")["error"])

# 3. Groq con requests simulado
respuestas = []


class Resp:
    def __init__(self, codigo, datos=None, texto=""):
        self.status_code, self._d, self.text = codigo, datos, texto

    def json(self):
        return self._d


llamadas = []


def post_falso(url, headers, json, timeout):
    llamadas.append((url, headers, json))
    return respuestas.pop(0)


m.requests.post = post_falso
respuestas[:] = [Resp(200, {"choices": [{"message": {"content": "sugerencias de Groq"}}]})]
texto, modelo = m.llamar_groq("hola", "llave")
prueba("Groq: lee el texto de la respuesta", texto == "sugerencias de Groq" and modelo == m.MODELO_GROQ)
prueba("Groq: manda llave, modelo y mensaje", llamadas[0][1]["Authorization"] == "Bearer llave"
       and llamadas[0][2]["model"] == m.MODELO_GROQ and llamadas[0][2]["messages"][0]["content"] == "hola")
respuestas[:] = [Resp(503, texto="saturado"), Resp(200, {"choices": [{"message": {"content": "ya"}}]})]
prueba("Groq: reintenta si hay 503", m.llamar_groq("hola", "llave")[0] == "ya")
respuestas[:] = [Resp(401, texto="bad key")]
try:
    m.llamar_groq("hola", "llave"); prueba("Groq: error 401", False)
except RuntimeError as e:
    prueba("Groq: error 401 avisa con el código", "401" in str(e))

# 4. Gemini con cliente simulado (503 en el modelo principal, el de respaldo contesta)
errores = types.ModuleType("google.genai.errors")


class APIError(Exception):
    def __init__(self, code):
        super().__init__(f"{code} UNAVAILABLE"); self.code = code


errores.APIError = APIError
usados = []


class ModelosFalso:
    def generate_content(self, model, contents):
        usados.append(model)
        if model == m.MODELOS_GEMINI[0]:
            raise APIError(503)
        return types.SimpleNamespace(text="sugerencias de Gemini")


genai = types.ModuleType("google.genai")
genai.Client = lambda api_key: types.SimpleNamespace(models=ModelosFalso())
genai.errors = errores
google = types.ModuleType("google"); google.genai = genai
sys.modules.update({"google": google, "google.genai": genai, "google.genai.errors": errores})
texto, modelo = m.llamar_gemini("hola", "llave")
prueba("Gemini: con 503 usa el modelo de respaldo", texto == "sugerencias de Gemini" and modelo == m.MODELOS_GEMINI[1])

# 5. Callback completo con las dos IAs simuladas
m.GEMINI_API_KEY, m.GROQ_API_KEY = "llave-g", "llave-q"
m.llamar_gemini = lambda pr, k: ("1. Idea de Gemini", "gemini-prueba")
m.llamar_groq = lambda pr, k: ("1. Idea de Groq", "groq-prueba")
g, x, aviso = m.pedir_sugerencias(1, "Café", "café", "jóvenes", "publicaciones")
prueba("callback: muestra las dos respuestas", "Idea de Gemini" in texto_de(g) and "Idea de Groq" in texto_de(x) and aviso == "")
m.llamar_groq = lambda pr, k: (_ for _ in ()).throw(RuntimeError("sin internet"))
g, x, aviso = m.pedir_sugerencias(1, "Café", "café", "jóvenes", "publicaciones")
prueba("callback: si Groq falla, Gemini sigue", "Idea de Gemini" in texto_de(g) and "sin internet" in texto_de(x))
m.GROQ_API_KEY = ""
g, x, aviso = m.pedir_sugerencias(1, "Café", "café", "jóvenes", "publicaciones")
prueba("callback: sin llave de Groq avisa en su cuadro", "Falta la API key" in texto_de(x) and "Idea de Gemini" in texto_de(g))
prueba("callback: campos vacíos avisan", "Llena" in m.pedir_sugerencias(1, "", "café", "jóvenes", "slogan")[2])
print(f"\n{sum(resultados)} de {len(resultados)} pruebas correctas")
