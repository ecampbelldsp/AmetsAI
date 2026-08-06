import logging
import numpy as np
import librosa
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_huggingface import HuggingFaceEmbeddings
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ajusta las importaciones para que sean relativas a la nueva ubicación
from core.stt.stt_pipeline import STTEngine
from core.rag.vector_db import DualCorpusManager
from core.agentic.core import AgentOrchestrator

# ==========================================
# 0. Configuración de Logging
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("FastAPIApp")

# ==========================================
# Inicialización de la Aplicación FastAPI
# ==========================================
app = FastAPI()

# Configuración de CORS
origins = [
    "http://localhost:3000",  # El origen de tu frontend
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Carga de Modelos y Componentes (al inicio)
# ==========================================
def load_models():
    """Carga todos los modelos y componentes necesarios para la aplicación."""
    logger.info("Cargando modelos y componentes...")
    
    # --- Carga del motor STT ---
    stt_engine = STTEngine(asr_model_size="base", language="es", device="cuda", compute_type="float16")
    
    # --- Carga de componentes RAG ---
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    db_manager = DualCorpusManager(embeddings_model=embeddings, persist_directory="../data/chroma/local_chroma_db")
    db_manager.load_existing_db()
    
    # --- Carga del orquestador del agente ---
    # Se asume un modelo por defecto, podría ser configurable
    agent_orchestrator = AgentOrchestrator(
        db_manager=db_manager,
        credentials_path="../.cred/credentials.yaml",
        use_local_model=False  # O True, según el default deseado
    )
    
    logger.info("Modelos y componentes cargados exitosamente.")
    return stt_engine, db_manager, agent_orchestrator

stt_engine, db_manager, agent_orchestrator = load_models()

# ==========================================
# Endpoints de la API
# ==========================================
@app.post("/process-audio/")
async def process_audio(file: UploadFile = File(...), use_local_model: bool = False):
    """
    Endpoint para procesar un archivo de audio, transcribirlo y obtener insights.
    """
    try:
        # 1. Cargar y Remuestrear el Audio
        logger.info(f"Procesando archivo de audio: {file.filename}")
        audio_data, _ = librosa.load(file.file, sr=16000, mono=True)
        raw_audio_bytes = audio_data.astype(np.float32).tobytes()

        # 2. Transcripción del Audio
        logger.info("Iniciando transcripción de audio...")
        vocabulary = "Glucofast, posología, insuficiencia renal moderada."
        session = stt_engine.create_session()
        transcription = ""
        NETWORK_CHUNK_SIZE = 2048
        bytes_per_chunk = NETWORK_CHUNK_SIZE * 4
        
        for i in range(0, len(raw_audio_bytes), bytes_per_chunk):
            byte_chunk = raw_audio_bytes[i: i + bytes_per_chunk]
            record = session.process_chunk(byte_chunk, initial_prompt=vocabulary)
            if record and record["type"] == "transcript":
                transcription += record["text"] + " "
        
        final_transcription = transcription.strip()
        logger.info(f"Transcripción final: '{final_transcription}'")

        if not final_transcription:
            raise HTTPException(status_code=400, detail="No se pudo transcribir el audio.")

        # 3. Invocación del Agente
        logger.info(f"Invocando el orquestador del agente (modelo local: {use_local_model})...")
        
        input_state = {"transcription": final_transcription}
        final_state = agent_orchestrator.invoke(input_state)

        # 4. Devolver Resultados
        # Formatear los contextos para que la UI no rompa (espera title.es y body.es)
        commercial_str = final_state.get('commercial_context', '{}')
        clinical_str = final_state.get('clinical_context', '{}')

        commercial_doc = {
            "id": "COM-RAG",
            "title": {"es": "Historial CRM", "en": "CRM History"},
            "body": {"es": commercial_str, "en": commercial_str}
        }

        clinical_doc = {
            "id": "CLI-RAG",
            "title": {"es": "Ficha Técnica", "en": "Clinical Data"},
            "body": {"es": clinical_str, "en": clinical_str}
        }

        logger.info("Proceso completado. Devolviendo resultados estructurados para la UI.")
        return {
            "transcription": final_transcription,
            "is_compliant": final_state.get('is_compliant', False),
            "compliance_reasoning": final_state.get('compliance_reasoning', 'N/A'),
            "compliance_chain_of_thought": final_state.get('compliance_chain_of_thought', []),
            "strategic_insight": final_state.get('strategic_insight', 'N/A'),
            "final_recommendation": final_state.get('final_recommendation', 'No se generó ninguna recomendación.'),
            "commercial_context": commercial_doc,
            "clinical_context": clinical_doc,
            "ml_insights": final_state.get('ml_insights', {}),
        }
    except Exception as e:
        logger.error(f"Error durante el procesamiento del audio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "API para el análisis de interacciones"}

# Para ejecutar la aplicación:
# uvicorn main:app --reload