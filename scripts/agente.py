from core.stt.stt_pipeline import STTEngine
import json
import logging
import os
from typing import Any, Dict, TypedDict
import yaml
import librosa

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph

import numpy as np

from pydantic import BaseModel, Field
import pandas as pd



# Importar el gestor dual
from core.rag.vector_db import DualCorpusManager

# ==========================================
# 0. Configuración de Logging
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("AgentOrchestrator")


def setup_environment() -> None:
    """Carga credenciales y variables de entorno."""
    try:
        with open("../.cred/credentials.yaml", "r") as file:
            cred = yaml.safe_load(file)
        os.environ["HF_TOKEN"] = cred["HF_TOKEN"]
        os.environ["GOOGLE_API_KEY"] = cred["GOOGLE_API_KEY"]
        logger.info("Variables de entorno y credenciales cargadas exitosamente.")
    except Exception as e:
        logger.error(f"Error cargando el archivo de credenciales: {e}")
        raise


# ==========================================
# 1. Definición del Estado del Grafo y Schemas
# ==========================================
class AgentState(TypedDict):
    transcription: str
    commercial_context: str
    clinical_context: str
    is_compliant: bool
    compliance_reasoning: str
    final_recommendation: str


class ComplianceResult(BaseModel):
    is_compliant: bool = Field(
        description="True if the action respects the clinical context and medical guidelines, False otherwise."
    )
    reasoning: str = Field(
        description="Breve justificación técnica de la decisión basada en la ficha técnica."
    )


# ==========================================
# 2. Configuración de Modelos
# ==========================================
setup_environment()

llm_validator = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)
llm_generator = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)


# ==========================================
# 3. Nodos del Grafo
# ==========================================
def retrieve_data_node(state: AgentState, db_manager: DualCorpusManager) -> AgentState:
    """Nodo 1: Ejecuta la recuperación dual y formatea el contexto."""
    logger.info("Ejecutando nodo: retrieve_data_node")
    raw_context = db_manager.retrieve(state["transcription"], k_comercial=1, k_clinico=1)

    com_ctx = json.dumps(raw_context["contexto_comercial"], ensure_ascii=False, indent=2)
    clin_ctx = json.dumps(raw_context["contexto_clinico"], ensure_ascii=False, indent=2)

    logger.debug(f"Contexto Comercial recuperado:\n{com_ctx}")
    logger.debug(f"Contexto Clínico recuperado:\n{clin_ctx}")

    return {"commercial_context": com_ctx, "clinical_context": clin_ctx}


def compliance_gate_node(state: AgentState) -> AgentState:
    """Nodo 2: Valida si la acción del delegado respeta la Ficha Técnica utilizando Pydantic."""
    logger.info("Ejecutando nodo: compliance_gate_node")

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Eres un auditor estricto de compliance farmacéutico. Tu tarea es comparar la transcripción "
         "del delegado comercial con las reglas de la ficha técnica. El delegado no puede inventar dosis, "
         "recomendar fuera de indicación (off-label) ni omitir advertencias graves.\n\n"
         "Ficha Técnica (Ground Truth):\n{clinical_context}"),
        ("user", "Transcripción del delegado:\n{transcription}")
    ])

    structured_validator = llm_validator.with_structured_output(ComplianceResult)
    chain = prompt | structured_validator

    try:
        result: ComplianceResult = chain.invoke({
            "clinical_context": state["clinical_context"],
            "transcription": state["transcription"]
        })

        is_compliant = result.is_compliant
        reasoning = result.reasoning
        logger.info(f"Evaluación de Compliance completada. Resultado: is_compliant={is_compliant}")

    except Exception as e:
        is_compliant = False
        reasoning = f"Fallo en la validación estructurada (Fallback a false): {str(e)}"
        logger.exception("Excepción durante la invocación del guardrail de compliance:")

    return {"is_compliant": is_compliant, "compliance_reasoning": reasoning}


def generate_alert_node(state: AgentState) -> AgentState:
    """Nodo 3A: Se ejecuta si el delegado violó las reglas de compliance."""
    logger.warning("Ejecutando nodo: generate_alert_node (ALERTA DE SEGURIDAD DESENCHUFADA)")
    alert = (
        "⚠️ ALERTA DE COMPLIANCE: La acción descrita en la visita no respeta las directrices médicas.\n"
        f"Motivo detectado por el auditor: {state['compliance_reasoning']}\n"
        "Acción: Notificar al responsable de zona y bloquear el registro en el CRM."
    )
    return {"final_recommendation": alert}


def generate_actionable_insight_node(state: AgentState) -> AgentState:
    """Nodo 3B: Genera los siguientes pasos citando la ficha técnica."""
    logger.info("Ejecutando nodo: generate_actionable_insight_node")

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Eres un asistente comercial farmacéutico inteligente. Basándote en el historial del cliente y "
         "la nueva transcripción de la visita, genera 2 recomendaciones accionables (ej. enviar email, "
         "agendar visita, preparar material).\n\n"
         "REGLA CRÍTICA DE TRAZABILIDAD: Si basas tu recomendación en una restricción o dosis médica, "
         "debes citar el documento clínico extraído utilizando este formato exacto: [Source: ID_DEL_DOCUMENTO].\n\n"
         "Historial Previo:\n{commercial_context}\n\n"
         "Ficha Técnica:\n{clinical_context}"),
        ("user", "Nueva visita (Transcripción):\n{transcription}\n\nExtrae las acciones:")
    ])

    chain = prompt | llm_generator
    response = chain.invoke({
        "commercial_context": state["commercial_context"],
        "clinical_context": state["clinical_context"],
        "transcription": state["transcription"]
    })

    return {"final_recommendation": response.content}


# ==========================================
# 4. Enrutamiento Condicional
# ==========================================
def route_compliance(state: AgentState) -> str:
    """Decide el camino en base al status de compliance."""
    if state["is_compliant"]:
        logger.info("Enrutando hacia: generate_insight")
        return "generate_insight"
    else:
        logger.info("Enrutando hacia: generate_alert")
        return "generate_alert"


# ==========================================
# 5. Construcción y Compilación del Grafo
# ==========================================
def build_agent_graph(db_manager: DualCorpusManager):
    workflow = StateGraph(AgentState)

    workflow.add_node("retrieve", lambda state: retrieve_data_node(state, db_manager))
    workflow.add_node("compliance_gate", compliance_gate_node)
    workflow.add_node("generate_insight", generate_actionable_insight_node)
    workflow.add_node("generate_alert", generate_alert_node)

    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "compliance_gate")

    workflow.add_conditional_edges(
        "compliance_gate",
        route_compliance,
        {
            "generate_insight": "generate_insight",
            "generate_alert": "generate_alert"
        }
    )

    workflow.add_edge("generate_insight", END)
    workflow.add_edge("generate_alert", END)

    return workflow.compile()


# ==========================================
# Ejecución Principal
# ==========================================
if __name__ == "__main__":

    #Speech pipeline
    vocabulary = "Glucofast, posología, insuficiencia renal moderada."
    # 1. Initialize the Engine (loads weights into VRAM)
    print("Initializing STT Engine...")
    engine = STTEngine(asr_model_size="large-v3-turbo", language="es", device="cuda", compute_type="float16")

    # 2. Create a fresh streaming session
    session = engine.create_session()

    # Getting transcription
    # --- Configuration ---
    TEST_AUDIO_PATH = "/media/edwardl.campbell/D/code/AmetsAI/data/audio/audio.wav"
    NETWORK_CHUNK_SIZE = 2048  # Simulating ~128ms network payloads

    logger.info(f"Loading and resampling: {TEST_AUDIO_PATH}")
    # Ensure 16kHz mono for Silero/Whisper
    audio_data, _ = librosa.load(TEST_AUDIO_PATH, sr=16000, mono=True)

    # Convert the float32 numpy array into raw bytes (simulating WebSocket binary transfer)
    raw_audio_bytes = audio_data.astype(np.float32).tobytes()

    results = []
    bytes_per_chunk = NETWORK_CHUNK_SIZE * 4  # 4 bytes per float32
    logger.info("Simulating WebSocket stream...")
    transcription = ""
    # Feed the bytes into the session chunk by chunk
    for i in range(0, len(raw_audio_bytes), bytes_per_chunk):
        byte_chunk = raw_audio_bytes[i: i + bytes_per_chunk]

        # This is the exact function your FastAPI server calls
        record = session.process_chunk(byte_chunk, initial_prompt=vocabulary)

        if record and record["type"] == "transcript":
            results.append(record)
            logger.info(f"Captured: {record['text']}")
            transcription += record["text"] + " "
    #


    from langchain_huggingface import HuggingFaceEmbeddings

    logger.info("Inicializando modelo de Embeddings y Vector DB...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    db_manager = DualCorpusManager(embeddings_model=embeddings, persist_directory="../data/chroma/local_chroma_db")
    db_manager.load_existing_db()

    agent = build_agent_graph(db_manager)

    input_state = {
        "transcription": (transcription)
    }

    # "Visita de seguimiento con la doctora Elena Torres. Le he llevado la ficha técnica "
    # "de Glucofast que me pidió la semana pasada. Hemos estado revisando juntos el apartado "
    # "de posología. Le he subrayado que, según la ficha, para el segmento de pacientes con "
    # "insuficiencia renal moderada, es decir, con un filtrado entre 30 y 60, la indicación de "
    # "la marca es ajustar a 25 miligramos al día."


    logger.info("Iniciando Orquestador LangGraph...")
    final_state = agent.invoke(input_state)

    logger.info("=== RESULTADO FINAL DE LA PoC ===")
    logger.info(f"Compliance Validado: {final_state['is_compliant']}")
    logger.info(f"Razonamiento Auditor: {final_state['compliance_reasoning']}")
    logger.info(f"Recomendación del Orquestador:\n{final_state['final_recommendation']}")