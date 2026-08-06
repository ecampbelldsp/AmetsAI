import json
import logging
import os
from typing import TypedDict

import yaml
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from core.rag.vector_db import DualCorpusManager

# ==========================================
# 0. Configuración de Logging
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


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


def setup_environment(credentials_path: str = ".cred/credentials.yaml") -> None:
    """Carga credenciales y variables de entorno."""
    try:
        with open(credentials_path, "r") as file:
            cred = yaml.safe_load(file)
        os.environ["HF_TOKEN"] = cred["HF_TOKEN"]
        os.environ["GOOGLE_API_KEY"] = cred["GOOGLE_API_KEY"]
        logger.info("Variables de entorno y credenciales cargadas exitosamente.")
    except FileNotFoundError:
        logger.error(
            f"Archivo de credenciales no encontrado en: {credentials_path}. "
            "Asegúrate de que el path es correcto o configura las variables de entorno manualmente."
        )
        raise
    except Exception as e:
        logger.error(f"Error cargando el archivo de credenciales: {e}")
        raise


class AgentOrchestrator:
    def __init__(
        self,
        db_manager: DualCorpusManager,
        credentials_path: str = ".cred/credentials.yaml",
    ):
        self.db_manager = db_manager
        self._setup_llms(credentials_path)
        self.graph = self._build_graph()

    def _setup_llms(self, credentials_path: str):
        setup_environment(credentials_path)
        # The 2.5 series respects the temperature=0.0 parameter for strict determinism
        self.llm_validator = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", temperature=0.0
        )
        self.llm_generator = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", temperature=0.2
        )

    def _retrieve_data_node(self, state: AgentState) -> AgentState:
        """Nodo 1: Ejecuta la recuperación dual y formatea el contexto."""
        logger.info("Ejecutando nodo: retrieve_data_node")
        raw_context = self.db_manager.retrieve(
            state["transcription"], k_comercial=1, k_clinico=1
        )

        com_ctx = json.dumps(
            raw_context["contexto_comercial"], ensure_ascii=False, indent=2
        )
        clin_ctx = json.dumps(
            raw_context["contexto_clinico"], ensure_ascii=False, indent=2
        )

        return {"commercial_context": com_ctx, "clinical_context": clin_ctx}

    def _compliance_gate_node(self, state: AgentState) -> AgentState:
        """Nodo 2: Valida si la acción del delegado respeta la Ficha Técnica."""
        logger.info("Ejecutando nodo: compliance_gate_node")

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Eres un auditor estricto de compliance farmacéutico. Tu tarea es comparar la transcripción "
                    "del delegado comercial con las reglas de la ficha técnica. El delegado no puede inventar dosis, "
                    "recomendar fuera de indicación (off-label) ni omitir advertencias graves.\n\n"
                    "Ficha Técnica (Ground Truth):\n{clinical_context}",
                ),
                ("user", "Transcripción del delegado:\n{transcription}"),
            ]
        )

        structured_validator = self.llm_validator.with_structured_output(
            ComplianceResult
        )
        chain = prompt | structured_validator

        try:
            result: ComplianceResult = chain.invoke(
                {
                    "clinical_context": state["clinical_context"],
                    "transcription": state["transcription"],
                }
            )

            is_compliant = result.is_compliant
            reasoning = result.reasoning
            logger.info(
                f"Evaluación de Compliance completada. Resultado: is_compliant={is_compliant}"
            )

        except Exception as e:
            is_compliant = False
            reasoning = f"Fallo en la validación estructurada (Fallback a false): {str(e)}"
            logger.exception(
                "Excepción durante la invocación del guardrail de compliance:"
            )

        return {"is_compliant": is_compliant, "compliance_reasoning": reasoning}

    def _generate_alert_node(self, state: AgentState) -> AgentState:
        """Nodo 3A: Se ejecuta si el delegado violó las reglas de compliance."""
        logger.warning(
            "Ejecutando nodo: generate_alert_node (ALERTA DE SEGURIDAD DESENCHUFADA)"
        )
        alert = (
            "⚠️ ALERTA DE COMPLIANCE: La acción descrita en la visita no respeta las directrices médicas.\n"
            f"Motivo detectado por el auditor: {state['compliance_reasoning']}\n"
            "Acción: Notificar al responsable de zona y bloquear el registro en el CRM."
        )
        return {"final_recommendation": alert}

    def _generate_actionable_insight_node(self, state: AgentState) -> AgentState:
        """Nodo 3B: Genera los siguientes pasos citando la ficha técnica."""
        logger.info("Ejecutando nodo: generate_actionable_insight_node")

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Eres un asistente comercial farmacéutico inteligente. Basándote en el historial del cliente y "
                    "la nueva transcripción de la visita, genera 2 recomendaciones accionables (ej. enviar email, "
                    "agendar visita, preparar material).\n\n"
                    "REGLA CRÍTICA DE TRAZABILIDAD: Si basas tu recomendación en una restricción o dosis médica, "
                    "debes citar el documento clínico extraído utilizando este formato exacto: [Source: ID_DEL_DOCUMENTO].\n\n"
                    "Historial Previo:\n{commercial_context}\n\n"
                    "Ficha Técnica:\n{clinical_context}",
                ),
                (
                    "user",
                    "Nueva visita (Transcripción):\n{transcription}\n\nExtrae las acciones:",
                ),
            ]
        )

        chain = prompt | self.llm_generator
        response = chain.invoke(
            {
                "commercial_context": state["commercial_context"],
                "clinical_context": state["clinical_context"],
                "transcription": state["transcription"],
            }
        )

        return {"final_recommendation": response.content}

    def _route_compliance(self, state: AgentState) -> str:
        """Decide el camino en base al status de compliance."""
        if state["is_compliant"]:
            logger.info("Enrutando hacia: generate_insight")
            return "generate_insight"
        else:
            logger.info("Enrutando hacia: generate_alert")
            return "generate_alert"

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("retrieve", self._retrieve_data_node)
        workflow.add_node("compliance_gate", self._compliance_gate_node)
        workflow.add_node("generate_insight", self._generate_actionable_insight_node)
        workflow.add_node("generate_alert", self._generate_alert_node)

        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "compliance_gate")

        workflow.add_conditional_edges(
            "compliance_gate",
            self._route_compliance,
            {"generate_insight": "generate_insight", "generate_alert": "generate_alert"},
        )

        workflow.add_edge("generate_insight", END)
        workflow.add_edge("generate_alert", END)

        return workflow.compile()

    def invoke(self, input_state: dict) -> dict:
        """Invokes the agent with a given input state."""
        logger.info("Iniciando Orquestador LangGraph...")
        final_state = self.graph.invoke(input_state)
        logger.info("Orquestador LangGraph finalizado.")
        return final_state
