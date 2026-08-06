# core/data_processor.py
import json
from typing import List, Tuple
from langchain_core.documents import Document


def load_historial_documents(file_path: str) -> List[Document]:
    """Carga el corpus comercial (historial de visitas)."""
    docs = []
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for entry in data:
            content = f"Cliente: {entry['Cliente']} | Especialidad: {entry['Especialidad']} | Texto: {entry['Texto']}"
            docs.append(Document(
                page_content=content,
                metadata={"source": "historial", "id_visita": entry["ID_Visita"], "cliente": entry["Cliente"]}
            ))
    return docs


def load_clinical_documents(file_path: str) -> List[Document]:
    """Carga el corpus clínico (fichas técnicas estructuradas)."""
    docs = []
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for entry in data:
            entities = entry.get("extracted_entities", {})
            medication = entities.get("medication", {}).get("brand_name", "Desconocido")

            content = f"Medicamento: {medication}\n"
            content += f"Indicaciones: {', '.join(entities.get('indications', []))}\n"
            content += f"Reglas posológicas: {json.dumps(entities.get('posology_rules', []), ensure_ascii=False)}\n"
            content += f"Contraindicaciones: {', '.join(entities.get('contraindications', []))}\n"
            content += f"Efectos adversos: {', '.join(entities.get('adverse_effects', []))}\n"

            docs.append(Document(
                page_content=content,
                metadata={"source": "ficha_tecnica", "medicamento": medication}
            ))
    return docs