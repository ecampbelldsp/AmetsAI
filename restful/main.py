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

from pydantic import BaseModel

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

class TextInput(BaseModel):
    text: str
    use_local_model: bool = False

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
async def process_audio(file: UploadFile = File(...), use_local_model: bool = False, streaming: bool = False):
    """
    Endpoint para procesar un archivo de audio, transcribirlo y obtener insights.
    Permite alternar entre procesamiento en batch (por defecto) a streaming.
    """
    try:
        # 1. Cargar y Remuestrear el Audio
        logger.info(f"Procesando archivo de audio: {file.filename}")
        audio_data, _ = librosa.load(file.file, sr=16000, mono=True)

        # 2. Transcripción del Audio
        logger.info(f"Iniciando transcripción de audio (Streaming: {streaming})...")
        vocabulary = "Glucofast, posología, insuficiencia renal moderada, doctora."

        if streaming:
            raw_audio_bytes = audio_data.astype(np.float32).tobytes()
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
        else:
            # Batch Processing
            audio_array = audio_data.astype(np.float32)
            record = stt_engine.transcribe_batch(audio_array, sample_rate=16000, initial_prompt=vocabulary)
            final_transcription = record.get("text", "")

        logger.info(f"Transcripción final: '{final_transcription}'")

        if not final_transcription:
            raise HTTPException(status_code=400, detail="No se pudo transcribir el audio.")

        # 3. Invocación del Agente
        logger.info(f"Invocando el orquestador del agente (modelo local: {use_local_model})...")
        
        input_state = {"transcription": final_transcription}
        final_state = agent_orchestrator.invoke(input_state)

        # 4. Devolver Resultados
        # Formatear los contextos para que la UI no rompa (espera title.es y body.es)
        # Reemplazar el bloque de 'commercial_doc' y 'clinical_doc' con esto:
        raw_com = final_state.get('raw_commercial_context', {})
        raw_clin = final_state.get('raw_clinical_context', {})

        commercial_doc = {
            "id": raw_com.get("id", "COM-RAG"),
            "title": {
                "es": raw_com.get("title", "Historial CRM"),
                "en": raw_com.get("title", "CRM History")
            },
            "body": {
                "es": raw_com.get("body", "Sin datos"),
                "en": raw_com.get("body", "No data")
            }
        }

        clinical_doc = {
            "id": raw_clin.get("id", "CLI-RAG"),
            "title": {
                "es": raw_clin.get("title", "Ficha Técnica"),
                "en": raw_clin.get("title", "Clinical Data")
            },
            "body": {
                "es": raw_clin.get("body", "Sin datos"),
                "en": raw_clin.get("body", "No data")
            }
        }
        # Ensure record is a dictionary to prevent AttributeError if record is None
        record = record if isinstance(record, dict) else {}

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
            # STT metadata
            "audio_duration_s": record.get("metrics", {}).get("audio_duration_s", 0),
            "inference_time_ms": record.get("metrics", {}).get("inference_time_ms", 0),
            "rtf": record.get("metrics", {}).get("rtf", 0),
            "endpoint_latency_ms": record.get("metrics", {}).get("endpoint_latency_ms", 0),
            "average_words_confidence": np.mean(
                [word["confidence"] for word in record.get("words_data", [])]) if record.get("words_data") else 0,
            # Add this line to pass the array to the UI
            "words_data": record.get("words_data", []),
        }
    except Exception as e:
        logger.error(f"Error durante el procesamiento del audio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-text/")
async def process_text(input_data: TextInput):
    """
    Endpoint para procesar texto directo (sin audio). Salta el STT y va directo al Agente.
    """
    try:
        logger.info(f"Procesando texto directo: '{input_data.text[:50]}...'")

        # Invocación directa del Agente
        input_state = {"transcription": input_data.text}
        final_state = agent_orchestrator.invoke(input_state)

        # Formatear los contextos
        # Reemplazar el bloque de 'commercial_doc' y 'clinical_doc' con esto:
        raw_com = final_state.get('raw_commercial_context', {})
        raw_clin = final_state.get('raw_clinical_context', {})

        commercial_doc = {
            "id": raw_com.get("id", "COM-RAG"),
            "title": {
                "es": raw_com.get("title", "Historial CRM"),
                "en": raw_com.get("title", "CRM History")
            },
            "body": {
                "es": raw_com.get("body", "Sin datos"),
                "en": raw_com.get("body", "No data")
            }
        }

        clinical_doc = {
            "id": raw_clin.get("id", "CLI-RAG"),
            "title": {
                "es": raw_clin.get("title", "Ficha Técnica"),
                "en": raw_clin.get("title", "Clinical Data")
            },
            "body": {
                "es": raw_clin.get("body", "Sin datos"),
                "en": raw_clin.get("body", "No data")
            }
        }

        logger.info("Proceso de texto completado. Devolviendo resultados a la UI.")
        return {
            "transcription": input_data.text,
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
        logger.error(f"Error durante el procesamiento de texto: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "API para el análisis de interacciones"}

if __name__ == "__main__":
    import uvicorn
    # Ejecuta el servidor en el puerto 8000, exponiéndolo en localhost (o la red)
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Para ejecutar la aplicación:
# uvicorn main:app --reload