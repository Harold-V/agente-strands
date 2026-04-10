"""
policies/retriever.py
=====================
Parser y recuperador de secciones de políticas desde archivos Markdown.

Estrategia: parsing por encabezados + scoring TF simple.
- No inyecta el documento completo al prompt.
- Retorna solo las secciones más relevantes (top-2).
- Latencia < 50ms (puro Python, sin red, sin embeddings).
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

from core.config import POLICIES_DIR


# ---------------------------------------------------------------------------
# Tipos de datos
# ---------------------------------------------------------------------------

class PolicySection(NamedTuple):
    document: str    # Nombre del documento (sin extensión)
    heading: str     # Texto del encabezado
    level: int       # Nivel de encabezado (1=H1, 2=H2, 3=H3)
    content: str     # Contenido de la sección (sin el encabezado)
    score: float     # Score de relevancia (asignado en búsqueda)


# ---------------------------------------------------------------------------
# Stopwords básicas (español + inglés) para no contaminar el scoring
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "de", "la", "el", "en", "y", "a", "los", "del", "se", "las", "un",
    "por", "con", "una", "para", "al", "es", "su", "que", "no", "si",
    "the", "of", "and", "to", "in", "is", "it", "for", "on", "with",
    "are", "or", "an", "at", "be", "this", "that", "can", "will",
}


# ---------------------------------------------------------------------------
# Parser de Markdown por encabezados
# ---------------------------------------------------------------------------

def _parse_markdown(filepath: Path) -> list[dict]:
    """
    Parsea un archivo Markdown y retorna lista de secciones.
    Cada sección corresponde a un bloque entre encabezados consecutivos.
    """
    if not filepath.exists():
        print(f"[WARNING] Política no encontrada: {filepath}")
        return []

    with open(filepath, encoding="utf-8") as f:
        text = f.read()

    sections = []
    heading_pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(text))

    for i, match in enumerate(matches):
        level = len(match.group(1))
        heading = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()

        sections.append({
            "heading": heading,
            "level": level,
            "content": content,
        })

    # Si no hay encabezados, tratar el documento completo como una sección
    if not sections:
        sections.append({
            "heading": filepath.stem,
            "level": 1,
            "content": text.strip(),
        })

    return sections


# ---------------------------------------------------------------------------
# Carga de todas las políticas
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_all_policies() -> list[PolicySection]:
    """
    Carga y parsea todos los archivos .md del directorio de políticas.
    Cacheado: se ejecuta una sola vez por proceso.
    """
    all_sections: list[PolicySection] = []
    policy_dir = POLICIES_DIR

    if not policy_dir.exists():
        print(f"[WARNING] Directorio de políticas no encontrado: {policy_dir}")
        return []

    md_files = list(policy_dir.glob("*.md"))
    if not md_files:
        print(f"[WARNING] No se encontraron archivos .md en {policy_dir}")
        return []

    for md_file in md_files:
        document_name = md_file.stem
        sections = _parse_markdown(md_file)
        for s in sections:
            all_sections.append(PolicySection(
                document=document_name,
                heading=s["heading"],
                level=s["level"],
                content=s["content"],
                score=0.0,
            ))

    return all_sections


# ---------------------------------------------------------------------------
# Motor de scoring
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> set[str]:
    """Tokeniza texto a palabras lowercase, filtrando stopwords y tokens cortos."""
    tokens = re.findall(r"[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+", text.lower())
    return {t for t in tokens if len(t) > 2 and t not in _STOPWORDS}


def _score_section(section: PolicySection, query_tokens: set[str]) -> float:
    """
    Calcula relevancia de una sección dado un conjunto de tokens de consulta.

    Ponderación:
        - Coincidencia en heading: peso 3
        - Coincidencia en content: peso 1
    """
    if not query_tokens:
        return 0.0

    heading_tokens = _tokenize(section.heading)
    content_tokens = _tokenize(section.content)

    heading_hits = len(query_tokens & heading_tokens)
    content_hits = len(query_tokens & content_tokens)

    return float(heading_hits * 3 + content_hits)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def search_policy(query: str, top_k: int = 2, max_content_chars: int = 1200) -> str:
    """
    Busca y retorna las secciones más relevantes de las políticas para la query.

    Args:
        query:            Consulta del usuario.
        top_k:            Número de secciones top a retornar (default 2).
        max_content_chars: Máximo de caracteres por sección.

    Returns:
        Texto con las secciones relevantes formateadas.
    """
    all_sections = _load_all_policies()
    if not all_sections:
        return "No se encontraron documentos de política disponibles."

    query_tokens = _tokenize(query)
    if not query_tokens:
        return "No se pudo procesar la consulta."

    # Asignar scores
    scored: list[tuple[float, PolicySection]] = []
    for section in all_sections:
        score = _score_section(section, query_tokens)
        scored.append((score, section))

    # Ordenar por score descendente
    scored.sort(key=lambda x: x[0], reverse=True)

    # Verificar que hay resultados relevantes
    if scored[0][0] == 0.0:
        return (
            "No encontré información específica sobre ese tema en las políticas. "
            "Puedo ayudarte con preguntas sobre devoluciones, garantías o envíos."
        )

    # Construir respuesta con las top_k secciones
    parts = []
    for score, section in scored[:top_k]:
        if score == 0.0:
            break
        content = section.content
        if len(content) > max_content_chars:
            content = content[:max_content_chars] + "..."

        parts.append(
            f"[{section.document} — {section.heading}]\n{content}"
        )

    return "\n\n".join(parts)
