import json
import logging
import os
from typing import TypedDict

import yaml
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
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
    raw_commercial_context: dict
    raw_clinical_context: dict
    is_compliant: bool
    compliance_reasoning: str
    compliance_chain_of_thought: list[str]
    ml_insights: dict
    strategic_insight: str
    final_recommendation: str


class ComplianceResult(BaseModel):
    chain_of_thought: list[str] = Field(
        description="Paso 1: Extrae la dosis del delegado. Paso 2: Extrae la dosis de la Ficha Técnica. Paso 3: Compara ambas paso a paso."
    )
    is_compliant: bool = Field(
        description="True if the action respects the clinical context and medical guidelines, False otherwise."
    )
    reasoning: str = Field(description="Breve justificación técnica de la decisión final.")


class CommercialInsightResult(BaseModel):
    ml_rationale: str = Field(
        description="Explicación detallada de cómo las métricas del modelo predictivo (ej. client_segment, churn_risk_score, predicted_value_tier) justifican y dan forma a la estrategia propuesta."
    )
    strategic_insight: str = Field(
        description="Un párrafo explicando cómo el delegado puede aumentar la cuota de prescripción, estrictamente dentro de las indicaciones aprobadas."
    )
    tactical_actions: list[str] = Field(
        description="Lista de 2 a 3 recomendaciones accionables claras (ej. enviar email, agendar visita). Si te basas en una restricción médica, cita el [Source: ID_DEL_DOCUMENTO]."
    )


def setup_environment(credentials_path: str = "../.cred/credentials.yaml") -> None:
    """Carga credenciales y variables de entorno."""
    try:
        with open(credentials_path, "r") as file:
            cred = yaml.safe_load(file)
        os.environ["HF_TOKEN"] = cred["HF_TOKEN"]
        os.environ["GOOGLE_API_KEY"] = cred["GOOGLE_API_KEY"]
        os.environ["GROQ_API_KEY"] = cred["GROQ_API_KEY"]
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
        use_local_model: bool = False,
        local_model_config: dict = None,
    ):
        self.db_manager = db_manager
        self._setup_llms(credentials_path, use_local_model, local_model_config)
        self.graph = self._build_graph()

    def _setup_llms(
        self,
        credentials_path: str,
        use_local_model: bool,
        local_model_config: dict,
    ):
        if use_local_model:
            logger.info("Usando modelo local.")
            if not local_model_config:
                local_model_config = {
                    "model_name": "Qwen/Qwen2.5-3B-Instruct-AWQ",
                    "api_base": "http://localhost:8000/v1",
                }
            self.llm_validator = ChatOpenAI(
                model=local_model_config["model_name"],
                base_url=local_model_config["api_base"],
                api_key="EMPTY",
                temperature=0.0,
            )
            self.llm_generator = ChatOpenAI(
                model=local_model_config["model_name"],
                base_url=local_model_config["api_base"],
                api_key="EMPTY",
                temperature=0.2,
            )
        else:
            modelo_llm = "llama-3.3-70b-versatile"
            logger.info(f"Usando modelo {modelo_llm}")
            setup_environment(credentials_path)
            self.llm_validator = ChatGroq(
                model=modelo_llm,
                temperature=0.0
            )
            self.llm_generator = ChatGroq(
                model=modelo_llm,
                temperature=0.2
            )

    def _retrieve_data_node(self, state: AgentState) -> AgentState:
        """Nodo 1: Ejecuta la recuperación dual y formatea el contexto."""
        logger.info("Ejecutando nodo: retrieve_data_node")
        raw_context = self.db_manager.retrieve(
            state["transcription"], k_comercial=1, k_clinico=1
        )

        raw_com_doc = raw_context["contexto_comercial"][0] if raw_context["contexto_comercial"] else None
        raw_clin_doc = raw_context["contexto_clinico"][0] if raw_context["contexto_clinico"] else None

        com_ctx_for_llm = {}
        if raw_com_doc:
            # CORRECCIÓN: Usar 'metadatos' y 'contenido' devueltos por vector_db.py
            meta = raw_com_doc.get("metadatos", {}) if isinstance(raw_com_doc, dict) else raw_com_doc.metadata
            content = raw_com_doc.get("contenido", "") if isinstance(raw_com_doc, dict) else raw_com_doc.page_content

            com_ctx_for_llm = {
                "id": meta.get("id_visita", "N/A"),
                "title": f"Visita a {meta.get('cliente', 'Desconocido')}",
                "body": content,
            }

        clin_ctx_for_llm = {}
        if raw_clin_doc:
            # CORRECCIÓN: Usar 'metadatos' y 'contenido'
            meta = raw_clin_doc.get("metadatos", {}) if isinstance(raw_clin_doc, dict) else raw_clin_doc.metadata
            content = raw_clin_doc.get("contenido", "") if isinstance(raw_clin_doc, dict) else raw_clin_doc.page_content

            clin_ctx_for_llm = {
                "id": meta.get("medicamento", "N/A"),
                "title": f"Ficha Técnica: {meta.get('medicamento', 'Desconocido')}",
                "body": content,
            }

        return {
            "commercial_context": json.dumps(com_ctx_for_llm, ensure_ascii=False, indent=2),
            "clinical_context": json.dumps(clin_ctx_for_llm, ensure_ascii=False, indent=2),
            "raw_commercial_context": com_ctx_for_llm,
            "raw_clinical_context": clin_ctx_for_llm,
        }

    def _compliance_gate_node(self, state: AgentState) -> AgentState:
        """Nodo 2: Valida si la acción del delegado respeta la Ficha Técnica."""
        logger.info("Ejecutando nodo: compliance_gate_node")
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Eres un auditor estricto de compliance farmacéutico...",
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
            chain_of_thought = result.chain_of_thought
            logger.info(
                f"Evaluación de Compliance completada. Resultado: is_compliant={is_compliant}"
            )
        except Exception as e:
            is_compliant = False
            reasoning = f"Fallo en la validación estructurada (Fallback a false): {str(e)}"
            chain_of_thought = ["Error en la validación"]
            logger.exception(
                "Excepción durante la invocación del guardrail de compliance:"
            )
        return {
            "is_compliant": is_compliant,
            "compliance_reasoning": reasoning,
            "compliance_chain_of_thought": chain_of_thought
        }

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
        """Nodo 3B: Genera la estrategia y los siguientes pasos con salida estructurada."""
        logger.info("Ejecutando nodo: generate_actionable_insight_node")

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Eres un estratega comercial farmacéutico de alto nivel. Basándote en el historial del cliente, "
                    "los datos de nuestros modelos predictivos (ML) y la transcripción de la visita, tu objetivo es identificar "
                    "oportunidades de crecimiento comercial estrictamente dentro de las indicaciones médicas aprobadas.\n\n"
                    "Explica cómo tú analisis usa los resultados de los modelo predictivos como base."
                    "REGLA CRÍTICA DE TRAZABILIDAD: Si basas tu recomendación en una restricción médica, "
                    "debes citar el documento clínico extraído utilizando este formato exacto: [Source: ID_DEL_DOCUMENTO].\n\n"
                    "Historial Previo:\n{commercial_context}\n\n"
                    "Resultados del Modelo Predictivo (ML Scoring):\n{ml_insights}\n\n"
                    "Ficha Técnica:\n{clinical_context}",
                ),
                (
                    "user",
                    "Nueva visita (Transcripción):\n{transcription}",
                ),
            ]
        )

        structured_generator = self.llm_generator.with_structured_output(
            CommercialInsightResult
        )
        chain = prompt | structured_generator

        try:
            result: CommercialInsightResult = chain.invoke(
                {
                    "commercial_context": state["commercial_context"],
                    "clinical_context": state["clinical_context"],
                    "ml_insights": json.dumps(state.get("ml_insights", {}), ensure_ascii=False, indent=2),
                    "transcription": state["transcription"],
                }
            )

            strategic_insight = (
                f"📊 ANÁLISIS PREDICTIVO (ML):\n{result.ml_rationale}\n\n"
                f"🎯 ESTRATEGIA COMERCIAL:\n{result.strategic_insight}"
            )

            tactical_actions_str = "\n".join([f"- {action}" for action in result.tactical_actions])
            logger.info("Insights comerciales generados exitosamente.")

        except Exception as e:
            strategic_insight = "Error al generar la estrategia de crecimiento."
            tactical_actions_str = f"Fallo en la generación táctica estructurada: {str(e)}"
            logger.exception("Excepción durante la invocación del orquestador comercial:")

        return {
            "strategic_insight": strategic_insight,
            "final_recommendation": tactical_actions_str
        }

    def _predictive_scoring_node(self, state: AgentState) -> AgentState:
        """Nodo ML: Simula los algoritmos core (scoring, segmentación, valor)."""
        logger.info("Ejecutando nodo: predictive_scoring_node (Mock ML/DL)")

        mock_ml_output = {
            "client_segment": "High-Potential / Early Adopter",
            "churn_risk_score": 0.12,
            "predicted_value_tier": "Tier 1 (Top 20% prescriptores)",
            "recommended_action_type": "Upsell / Consolidación de cuota"
        }
        logger.info(mock_ml_output)

        return {"ml_insights": mock_ml_output}

    def _route_compliance(self, state: AgentState) -> str:
        """Decide el camino en base al status de compliance."""
        if state["is_compliant"]:
            logger.info("Enrutando hacia: predictive_scoring")
            return "predictive_scoring"
        else:
            logger.info("Enrutando hacia: generate_alert")
            return "generate_alert"

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("retrieve", self._retrieve_data_node)
        workflow.add_node("compliance_gate", self._compliance_gate_node)
        workflow.add_node("predictive_scoring", self._predictive_scoring_node)
        workflow.add_node("generate_insight", self._generate_actionable_insight_node)
        workflow.add_node("generate_alert", self._generate_alert_node)

        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "compliance_gate")

        workflow.add_conditional_edges(
            "compliance_gate",
            self._route_compliance,
            {"predictive_scoring": "predictive_scoring", "generate_alert": "generate_alert"},
        )

        workflow.add_edge("predictive_scoring", "generate_insight")

        workflow.add_edge("generate_insight", END)
        workflow.add_edge("generate_alert", END)

        return workflow.compile()

    def invoke(self, input_state: dict) -> dict:
        """Invokes the agent with a given input state."""
        logger.info("Iniciando Orquestador LangGraph...")
        final_state = self.graph.invoke(input_state)
        logger.info("Orquestador LangGraph finalizado.")
        return final_state