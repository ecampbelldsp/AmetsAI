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
logger = logging.getLogger("MainScript")

# ==========================================
# Ejecución Principal
# ==========================================
if __name__ == "__main__":
    # --- Configuración de STT ---
    vocabulary = "Glucofast, posología, insuficiencia renal moderada."
    TEST_AUDIO_PATH = "/media/edwardl.campbell/D/code/AmetsAI/data/audio/audio.wav"
    NETWORK_CHUNK_SIZE = 2048  # Simula ~128ms de carga útil de red

    # 1. Inicializar el motor STT
    logger.info("Inicializando el motor STT...")
    engine = STTEngine(asr_model_size="large-v3-turbo", language="es", device="cuda", compute_type="float16")
    session = engine.create_session()

    # 2. Procesar el archivo de audio
    logger.info(f"Cargando y remuestreando: {TEST_AUDIO_PATH}")
    audio_data, _ = librosa.load(TEST_AUDIO_PATH, sr=16000, mono=True)
    raw_audio_bytes = audio_data.astype(np.float32).tobytes()

    logger.info("Simulando transmisión de WebSocket y transcribiendo...")
    transcription = ""
    bytes_per_chunk = NETWORK_CHUNK_SIZE * 4  # 4 bytes por float32
    for i in range(0, len(raw_audio_bytes), bytes_per_chunk):
        byte_chunk = raw_audio_bytes[i: i + bytes_per_chunk]
        record = session.process_chunk(byte_chunk, initial_prompt=vocabulary)
        if record and record["type"] == "transcript":
            logger.info(f"Fragmento capturado: {record['text']}")
            transcription += record["text"] + " "
    
    logger.info(f"Transcripción final obtenida: '{transcription.strip()}'")

    # 3. Inicializar componentes de RAG y Agente
    logger.info("Inicializando modelo de Embeddings y Vector DB...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    db_manager = DualCorpusManager(embeddings_model=embeddings, persist_directory="../data/chroma/local_chroma_db")
    db_manager.load_existing_db()

    logger.info("Instanciando el orquestador del agente...")
    # La ruta a las credenciales es relativa a la raíz del proyecto
    agent_orchestrator = AgentOrchestrator(db_manager=db_manager, credentials_path="../.cred/credentials.yaml")

    # 4. Invocar el agente con la transcripción
    input_state = {"transcription": transcription.strip()}

    logger.info("Iniciando Orquestador LangGraph...")
    final_state = agent_orchestrator.invoke(input_state)

    # 5. Mostrar resultados
    logger.info("\n" + "="*30)
    logger.info("=== RESULTADO FINAL DE LA PoC ===")
    logger.info("="*30)
    logger.info(f"Compliance Validado: {final_state.get('is_compliant', 'N/A')}")
    logger.info(f"Razonamiento del Auditor: {final_state.get('compliance_reasoning', 'N/A')}")
    logger.info(f"Recomendación del Orquestador:\n{final_state.get('final_recommendation', 'No se generó ninguna recomendación.')}")
    logger.info("="*30)
