from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
from dotenv import load_dotenv
from model import entrenar_modelo, predecir_pieza
import os

# ======================================
# CONFIGURACIÓN DE ENTORNO (.env)
# ======================================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_KEY = os.getenv("OPENAI_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
client = OpenAI(api_key=OPENAI_KEY)

# ======================================
# APP FASTAPI
# ======================================
app = FastAPI()

# ======================================
# CONFIGURACION CORS PARA VERCEL
# ======================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tusitio.vercel.app",  # 👈 cambia esto por tu dominio real de Vercel
        "http://localhost:3000",       # opcional para pruebas locales
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================
# ENTRENAMIENTO INICIAL DEL MODELO
# ======================================
clf, le = entrenar_modelo()


class Falla(BaseModel):
    descripcion: str
    motocicleta: str


# ======================================
# GENERAR EXPLICACIÓN CON OPENAI
# ======================================
def generar_explicacion(descripcion: str, pieza: str, motocicleta: str) -> str:
    prompt = f"""
    Motocicleta: {motocicleta}
    Falla descrita: "{descripcion}".
    Pieza más probable: {pieza}.

    Instrucciones:
    - No repitas el nombre de la pieza al inicio.
    - Devuelve únicamente estos apartados:
      **Función principal**
      **Posibles fallas y síntomas**
      **Evidencia sonora o mecánica**
    """
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content.strip()


# ======================================
# ENDPOINT: DIAGNÓSTICO IA
# ======================================
@app.post("/api/diagnostico")
def diagnostico(falla: Falla):
    resultados = predecir_pieza(falla.descripcion, falla.motocicleta, clf, le)

    salida = []
    for pieza, prob in resultados[:3]:
        explicacion = generar_explicacion(falla.descripcion, pieza, falla.motocicleta)
        salida.append({
            "pieza": pieza,
            "probabilidad": float(prob),
            "explicacion": explicacion
        })
    return {"predicciones": salida}


# ======================================
# ENDPOINT: REGISTRAR TICKET
# ======================================
@app.post("/api/ticket")
async def registrar_ticket(data: dict):
    try:
        supabase.table("tickets").insert({
            "motocicleta": data.get("motocicleta"),
            "descripcion": data.get("descripcion"),
            "diagnostico_predicho": data.get("diagnostico"),
            "pieza_predicha": data.get("pieza"),
            "probabilidad": data.get("probabilidad"),
            "falla_real": data.get("falla_real"),
            "cambios_realizados": data.get("cambios_realizados")
        }).execute()

        return {"status": "ok", "message": "Ticket registrado correctamente."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ======================================
# PUNTO DE ENTRADA (RAILWAY)
# ======================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
