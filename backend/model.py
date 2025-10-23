from openai import OpenAI
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from supabase import create_client
from dotenv import load_dotenv
import os

# ======================================
# CONFIGURACIÓN DE ENTORNO
# ======================================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_KEY = os.getenv("OPENAI_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
client = OpenAI(api_key=OPENAI_KEY)


# ======================================
# FUNCIONES
# ======================================
def get_embedding(text: str) -> list:
    """Genera embedding con OpenAI"""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def entrenar_modelo():
    """Obtiene datos de Supabase y entrena el modelo IA"""
    datos = supabase.table("fallas").select(
        "descripcion, motocicletas(modelo), diagnosticos(probabilidad, piezas(nombre))"
    ).execute()
    df = pd.DataFrame(datos.data)

    textos, etiquetas = [], []
    for _, row in df.iterrows():
        if row["diagnosticos"]:
            for d in row["diagnosticos"]:
                moto = row.get("motocicletas", {}).get("modelo", "N/A") if row.get("motocicletas") else "N/A"
                texto_final = f"{moto}: {row['descripcion']}"
                textos.append(texto_final)
                etiquetas.append(d["piezas"]["nombre"])

    if not textos:
        raise ValueError("No hay datos suficientes en Supabase para entrenar el modelo.")

    embeddings = [get_embedding(text) for text in textos]

    le = LabelEncoder()
    y = le.fit_transform(etiquetas)

    clf = LogisticRegression(max_iter=1000, multi_class="multinomial")
    clf.fit(embeddings, y)
    return clf, le


def predecir_pieza(descripcion: str, motocicleta: str, clf, le):
    """Predice la pieza más probable"""
    texto = f"{motocicleta}: {descripcion}"
    emb = np.array(get_embedding(texto)).reshape(1, -1)
    probs = clf.predict_proba(emb)[0]
    etiquetas = le.classes_
    ranking = sorted(zip(etiquetas, probs), key=lambda x: x[1], reverse=True)
    return ranking
