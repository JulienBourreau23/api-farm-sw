"""
Calcul des moyennes des effets secondaires d'artefacts.

Groupement :
  - Effets communs  2xx : présents sur les deux types
  - Effets élémentaires 3xx : spécifiques type=1
  - Effets style        4xx : spécifiques type=2

Filtres optionnels :
  - type         : 1=élémentaire / 2=style
  - attribute    : 1-5 (Feu/Eau/Vent/Lum/Tén)  — ignoré si type=2
  - unit_style   : 1-4 (ATQ/DEF/PV/Support)     — ignoré si type=1
  - pri_effect_id: 100/101/102 (PV%/ATQ%/DEF%)

La stat principale n'est pas moyennée (valeur fixe par effect_id).
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional


async def compute_artifact_averages(
    db: AsyncSession,
    user_id: int,
    import_id: int,
    artifact_type: Optional[int] = None,
    attribute: Optional[int] = None,
    unit_style: Optional[int] = None,
    pri_effect_id: Optional[int] = None,
    min_level: Optional[int] = None,
) -> list[dict]:
    """
    Calcule les moyennes des sec_effects selon les filtres.
    Retourne la liste triée : communs 2xx d'abord, puis spécifiques 3xx/4xx.
    """
    conditions = ["a.import_id = :import_id"]
    params: dict = {"import_id": import_id}

    if artifact_type is not None:
        conditions.append("a.type = :artifact_type")
        params["artifact_type"] = artifact_type

    if attribute is not None:
        conditions.append("a.attribute = :attribute")
        params["attribute"] = attribute

    if unit_style is not None:
        conditions.append("a.unit_style = :unit_style")
        params["unit_style"] = unit_style

    if pri_effect_id is not None:
        conditions.append("a.pri_effect_id = :pri_effect_id")
        params["pri_effect_id"] = pri_effect_id

    if min_level is not None:
        conditions.append("a.level >= :min_level")
        params["min_level"] = min_level

    where_clause = " AND ".join(conditions)

    query = text(f"""
        SELECT
            ase.effect_id,
            ROUND(AVG(ase.value)::numeric, 2)                          AS avg_base,
            ROUND(AVG(ase.value + ase.lock_level)::numeric, 2)         AS avg_with_lock,
            COUNT(*)::int                                               AS artifact_count,
            FLOOR(ase.effect_id / 100) * 100                           AS effect_group
        FROM artifact_sec_effects ase
        JOIN artifacts a ON a.id = ase.artifact_id
        WHERE {where_clause}
        GROUP BY ase.effect_id
        ORDER BY effect_group, ase.effect_id
    """)

    result = await db.execute(query, params)
    rows = result.fetchall()

    return [
        {
            "effect_id":      row.effect_id,
            "avg_base":       float(row.avg_base),
            "avg_with_lock":  float(row.avg_with_lock),
            "artifact_count": row.artifact_count,
            "effect_group":   int(row.effect_group),
        }
        for row in rows
    ]


async def get_artifact_count(
    db: AsyncSession,
    import_id: int,
    artifact_type: Optional[int] = None,
    attribute: Optional[int] = None,
    unit_style: Optional[int] = None,
    pri_effect_id: Optional[int] = None,
) -> int:
    """Retourne le nombre d'artefacts correspondant aux filtres."""
    conditions = ["a.import_id = :import_id"]
    params: dict = {"import_id": import_id}

    if artifact_type is not None:
        conditions.append("a.type = :artifact_type")
        params["artifact_type"] = artifact_type
    if attribute is not None:
        conditions.append("a.attribute = :attribute")
        params["attribute"] = attribute
    if unit_style is not None:
        conditions.append("a.unit_style = :unit_style")
        params["unit_style"] = unit_style
    if pri_effect_id is not None:
        conditions.append("a.pri_effect_id = :pri_effect_id")
        params["pri_effect_id"] = pri_effect_id

    result = await db.execute(
        text(f"SELECT COUNT(*) AS total FROM artifacts a WHERE {' AND '.join(conditions)}"),
        params
    )
    return result.fetchone().total
