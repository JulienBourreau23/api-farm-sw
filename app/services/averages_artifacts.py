"""
Calcul des moyennes des effets secondaires d'artefacts.

Groupement statique (pas FLOOR) :
  - group 100 : effets spécifiques élémentaires (attribut gauche uniquement)
                206,210,214,215,218,219,220,221,222,223
  - group 200 : effets communs aux deux types
                224,225,226,227,306,307,308,309,
                400,401,404,405,406,407,408,409,410,411
  - group 300 : effets spécifiques type (droite uniquement)
                300,301,302,303,304,305
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional

# Mapping statique effect_id → group
EFFECT_GROUP_MAP = {
    # Spécifiques élémentaires (attribut) → group 100
    206: 100, 210: 100, 214: 100, 215: 100, 218: 100,
    219: 100, 220: 100, 221: 100, 222: 100, 223: 100,
    # Communs aux deux → group 200
    224: 200, 225: 200, 226: 200, 227: 200,
    306: 200, 307: 200, 308: 200, 309: 200,
    400: 200, 401: 200, 404: 200, 405: 200, 406: 200,
    407: 200, 408: 200, 409: 200, 410: 200, 411: 200,
    # Spécifiques type → group 300
    300: 300, 301: 300, 302: 300,
    303: 300, 304: 300, 305: 300,
}


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
            ROUND(AVG(ase.value)::numeric, 2)                  AS avg_base,
            ROUND(AVG(ase.value + ase.lock_level)::numeric, 2) AS avg_with_lock,
            COUNT(*)::int                                       AS artifact_count
        FROM artifact_sec_effects ase
        JOIN artifacts a ON a.id = ase.artifact_id
        WHERE {where_clause}
        GROUP BY ase.effect_id
        ORDER BY ase.effect_id
    """)

    result = await db.execute(query, params)
    rows = result.fetchall()

    return [
        {
            "effect_id":      row.effect_id,
            "avg_base":       float(row.avg_base),
            "avg_with_lock":  float(row.avg_with_lock),
            "artifact_count": row.artifact_count,
            "effect_group":   EFFECT_GROUP_MAP.get(row.effect_id, 200),
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
