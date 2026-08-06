import json
import os
from pydantic import BaseModel, Field
from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_vertexai import ChatVertexAI
import yaml



# Importar el gestor dual (simulado en base a la librería core del paso anterior)
from core.rag.vector_db import DualCorpusManager

def setup_environment():
    """Carga credenciales y variables de entorno."""
    with open("../.cred/credentials.yaml", "r") as file:
        cred = yaml.safe_load(file)
    os.environ["HF_TOKEN"] = cred["HF_TOKEN"]
    os.environ['GOOGLE_API_KEY'] = cred['GOOGLE_API_KEY']

# ==========================================
# 1. Definición del Estado del Grafo
# ==========================================
class AgentState(TypedDict):
    transcription: str
    commercial_context: str
    clinical_context: str
    is_compliant: bool
    compliance_reasoning: str
    final_recommendation: str

class ComplianceResult(BaseModel):
    is_compliant: bool = Field(description="True if the action respects the clinical context and medical guidelines, False otherwise.")
    reasoning: str = Field(description="Breve justificación técnica de la decisión basada en la ficha técnica.")

import os
from langchain_google_genai import ChatGoogleGenerativeAI

# ==========================================
# 2. Configuración de Modelos (Gemini Free Tier vía Google AI Studio)
# ==========================================

setup_environment()

# Instantiate using ChatGoogleGenerativeAI instead of ChatVertexAI
# Note: The parameter is 'model' instead of 'model_name'
llm_validator = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)
llm_generator = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)

# ==========================================
# 3. Nodos del Grafo
# ==========================================

def retrieve_data_node(state: AgentState, db_manager: DualCorpusManager) -> AgentState:
    """Nodo 1: Ejecuta la recuperación dual y formatea el contexto."""
    print("-> Ejecutando nodo: retrieve_data_node")
    raw_context = db_manager.retrieve(state["transcription"], k_comercial=1, k_clinico=1)

    # Formatear el output para inyectarlo como string al LLM
    com_ctx = json.dumps(raw_context["contexto_comercial"], ensure_ascii=False, indent=2)
    clin_ctx = json.dumps(raw_context["contexto_clinico"], ensure_ascii=False, indent=2)

    return {"commercial_context": com_ctx, "clinical_context": clin_ctx}


def compliance_gate_node(state: AgentState) -> AgentState:
    """Nodo 2: Valida si la acción del delegado respeta la Ficha Técnica utilizando Pydantic."""
    print("-> Ejecutando nodo: compliance_gate_node")

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Eres un auditor estricto de compliance farmacéutico. Tu tarea es comparar la transcripción "
         "del delegado comercial con las reglas de la ficha técnica. El delegado no puede inventar dosis, "
         "recomendar fuera de indicación (off-label) ni omitir advertencias graves.\n\n"
         "Ficha Técnica (Ground Truth):\n{clinical_context}"),
        ("user", "Transcripción del delegado:\n{transcription}")
    ])

    # Bind the Pydantic schema to the LLM
    structured_validator = llm_validator.with_structured_output(ComplianceResult)

    chain = prompt | structured_validator

    try:
        # The invoke method now returns a validated ComplianceResult object, not an AIMessage
        result = chain.invoke({
            "clinical_context": state["clinical_context"],
            "transcription": state["transcription"]
        })

        is_compliant = result.is_compliant
        reasoning = result.reasoning

    except Exception as e:
        is_compliant = False
        reasoning = f"Fallo en la validación estructurada (Fallback a false): {str(e)}"

    return {"is_compliant": is_compliant, "compliance_reasoning": reasoning}

def generate_alert_node(state: AgentState) -> AgentState:
    """Nodo 3A: Se ejecuta si el delegado violó las reglas de compliance."""
    print("-> Ejecutando nodo: generate_alert_node (ALERTA DE SEGURIDAD)")
    alert = (
        "⚠️ ALERTA DE COMPLIANCE: La acción descrita en la visita no respeta las directrices médicas.\n"
        f"Motivo detectado por el auditor: {state['compliance_reasoning']}\n"
        "Acción: Notificar al responsable de zona y bloquear el registro en el CRM."
    )
    return {"final_recommendation": alert}


def generate_actionable_insight_node(state: AgentState) -> AgentState:
    """Nodo 3B: Genera los siguientes pasos citando la ficha técnica."""
    print("-> Ejecutando nodo: generate_actionable_insight_node")

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
        return "generate_insight"
    else:
        return "generate_alert"


# ==========================================
# 5. Construcción y Compilación del Grafo
# ==========================================
def build_agent_graph(db_manager: DualCorpusManager):
    workflow = StateGraph(AgentState)

    # Añadir nodos (pasamos db_manager mediante functools.partial o lambdas si es necesario,
    # aquí usamos un wrapper simple)
    workflow.add_node("retrieve", lambda state: retrieve_data_node(state, db_manager))
    workflow.add_node("compliance_gate", compliance_gate_node)
    workflow.add_node("generate_insight", generate_actionable_insight_node)
    workflow.add_node("generate_alert", generate_alert_node)

    # Definir el flujo (Edges)
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "compliance_gate")

    # Edge condicional basado en la función de enrutamiento
    workflow.add_conditional_edges(
        "compliance_gate",
        route_compliance,
        {
            "generate_insight": "generate_insight",
            "generate_alert": "generate_alert"
        }
    )

    # Finalizar el grafo
    workflow.add_edge("generate_insight", END)
    workflow.add_edge("generate_alert", END)

    return workflow.compile()


# ==========================================
# Ejecución Principal
# ==========================================
if __name__ == "__main__":

    # 1. Instanciar el vector DB (asumiendo que ya fue persistido en pasos anteriores)
    from langchain_huggingface import HuggingFaceEmbeddings

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    db_manager = DualCorpusManager(embeddings_model=embeddings, persist_directory="../data/chroma/local_chroma_db")
    db_manager.load_existing_db()  # Carga las colecciones pre-existentes

    # 2. Compilar el grafo
    agent = build_agent_graph(db_manager)

    # 3. Input de la PoC (La transcripción Variante X ajustada)
    input_state = {
        "transcription": (
            "Visita de seguimiento con la doctora Elena Torres. Le he llevado la ficha técnica "
            "de Glucofast que me pidió la semana pasada. Hemos estado revisando juntos el apartado "
            "de posología. Le he subrayado que, según la ficha, para el segmento de pacientes con "
            "insuficiencia renal moderada, es decir, con un filtrado entre 30 y 60, la indicación de "
            "la marca es ajustar a 25 miligramos al día."
        )
    }

    # 4. Ejecutar el Agente
    print("\n--- Iniciando Orquestador LangGraph ---\n")
    final_state = agent.invoke(input_state)

    print("\n=== RESULTADO FINAL DE LA PoC ===")
    print(f"Compliance Validado: {final_state['is_compliant']}")
    print(f"Razonamiento Auditor: {final_state['compliance_reasoning']}\n")
    print(f"Recomendación del Orquestador:\n{final_state['final_recommendation']}")