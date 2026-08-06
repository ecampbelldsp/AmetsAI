# pipeline.py
import json
import os
import yaml
from langchain_huggingface import HuggingFaceEmbeddings

# Importaciones locales del core
from core.rag.data_processor import load_historial_documents, load_clinical_documents
from core.rag.vector_db import DualCorpusManager


def setup_environment():
    """Carga credenciales y variables de entorno."""
    with open("../.cred/credentials.yaml", "r") as file:
        cred = yaml.safe_load(file)
    os.environ["HF_TOKEN"] = cred["HF_TOKEN"]


def main():
    # 1. Configuración inicial
    setup_environment()
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    # Rutas
    ruta_historial = "../data/historiales/historial_visitas_poc.json"
    ruta_fichas = "../data/historiales/fichas_tecnicas_corpus.json"
    db_persist_path = "../data/chroma/local_chroma_db"

    # 2. Inicializar Gestor de Base de Datos
    db_manager = DualCorpusManager(embeddings_model=embeddings, persist_directory=db_persist_path)

    # 3. Flujo de Ingesta (Se ejecutaría solo la primera vez o en actualizaciones)
    print("--- Iniciando proceso de ingesta de documentos ---")
    docs_comercial = load_historial_documents(ruta_historial)
    docs_clinico = load_clinical_documents(ruta_fichas)
    db_manager.build_and_persist(docs_comercial, docs_clinico)

    # Nota: En ejecuciones futuras, podrías comentar el bloque 3 y usar:
    # db_manager.load_existing_db()

    # 4. Flujo de Recuperación (Retrieval Pipeline)
    transcripcion_audio = (
        "Visita de seguimiento con la doctora Elena Torres. Le he llevado la ficha técnica "
        "de Glucofast que me pidió la semana pasada. Hemos estado revisando juntos el apartado "
        "de posología. Le he subrayado que, según la ficha, para el segmento de pacientes con "
        "insuficiencia renal moderada, es decir, con un filtrado entre 30 y 60, la indicación de "
        "la marca es ajustar a 25 miligramos al día."
    )

    print(f"\n--- Ejecutando Dual Retrieval ---")
    retrieved_context = db_manager.retrieve(transcripcion_audio, k_comercial=1, k_clinico=1)

    # 5. Salida para inspección
    print(json.dumps(retrieved_context, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()