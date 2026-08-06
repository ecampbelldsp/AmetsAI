import logging
import librosa
import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings

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
logger = logging.getLogger("AgenteModule")

# ==========================================
# Funciones reutilizables
# ==========================================

def transcribe_audio(stt_engine: STTEngine, audio_path: str, vocabulary: str) -> str:
    """
    Procesa un archivo de audio y devuelve la transcripción.
    """
    logger.info(f"Cargando y remuestreando: {audio_path}")
    audio_data, _ = librosa.load(audio_path, sr=16000, mono=True)
    raw_audio_bytes = audio_data.astype(np.float32).tobytes()

    logger.info("Simulando transmisión de WebSocket y transcribiendo...")
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
    logger.info(f"Transcripción final obtenida: '{final_transcription}'")
    return final_transcription

def run_analysis(transcription: str, use_local_model: bool) -> dict:
    """
    Ejecuta el análisis de la transcripción con el agente.
    """
    logger.info("Inicializando modelo de Embeddings y Vector DB...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    db_manager = DualCorpusManager(embeddings_model=embeddings, persist_directory="../data/chroma/local_chroma_db")
    db_manager.load_existing_db()

    logger.info(f"Instanciando el orquestador del agente con el modelo: {'local' if use_local_model else 'remoto'}")
    agent_orchestrator = AgentOrchestrator(
        db_manager=db_manager,
        credentials_path="../.cred/credentials.yaml",
        use_local_model=use_local_model
    )

    input_state = {"transcription": transcription}
    logger.info("Iniciando Orquestador LangGraph...")
    final_state = agent_orchestrator.invoke(input_state)
    
    return final_state
