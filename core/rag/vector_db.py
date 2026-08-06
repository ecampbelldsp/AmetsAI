# core/vector_db.py
import os
from typing import List, Dict, Any
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document


class DualCorpusManager:
    """Gestor de base de datos vectorial para arquitecturas de doble corpus (Comercial vs Clínico)."""

    def __init__(self, embeddings_model: Embeddings, persist_directory: str = "./chroma_db"):
        self.embeddings = embeddings_model
        self.persist_directory = persist_directory
        self.comercial_dir = os.path.join(self.persist_directory, "comercial")
        self.clinico_dir = os.path.join(self.persist_directory, "clinico")

        # Inicialización perezosa de las colecciones
        self.db_comercial = None
        self.db_clinico = None

    def build_and_persist(self, docs_comercial: List[Document], docs_clinico: List[Document]):
        """Crea las colecciones desde cero y las guarda en disco."""
        print(f"Persistiendo corpus comercial en: {self.comercial_dir}")
        self.db_comercial = Chroma.from_documents(
            documents=docs_comercial,
            embedding=self.embeddings,
            collection_name="corpus_comercial",
            persist_directory=self.comercial_dir
        )

        print(f"Persistiendo corpus clínico en: {self.clinico_dir}")
        self.db_clinico = Chroma.from_documents(
            documents=docs_clinico,
            embedding=self.embeddings,
            collection_name="corpus_clinico",
            persist_directory=self.clinico_dir
        )

    def load_existing_db(self):
        """Carga las colecciones existentes desde el disco."""
        if not os.path.exists(self.comercial_dir) or not os.path.exists(self.clinico_dir):
            raise FileNotFoundError("No se encontraron bases de datos persistidas. Ejecute build_and_persist primero.")

        self.db_comercial = Chroma(
            collection_name="corpus_comercial",
            embedding_function=self.embeddings,
            persist_directory=self.comercial_dir
        )

        self.db_clinico = Chroma(
            collection_name="corpus_clinico",
            embedding_function=self.embeddings,
            persist_directory=self.clinico_dir
        )

    def retrieve(self, query: str, k_comercial: int = 1, k_clinico: int = 1) -> Dict[str, Any]:
        """Ejecuta búsquedas independientes en ambos corpus."""
        if not self.db_comercial or not self.db_clinico:
            raise RuntimeError("Las bases de datos no están inicializadas.")

        results_comercial = self.db_comercial.similarity_search(query, k=k_comercial)
        results_clinico = self.db_clinico.similarity_search(query, k=k_clinico)

        return {
            "contexto_comercial": [{"contenido": doc.page_content, "metadatos": doc.metadata} for doc in
                                   results_comercial],
            "contexto_clinico": [{"contenido": doc.page_content, "metadatos": doc.metadata} for doc in results_clinico]
        }