"""
Calcul des moyennes des effets secondaires d'artefacts.

Répartition réelle (vérifiée sur les données) :
  - 206-226 : présents sur les deux types
  - 300-309 : type=1 uniquement (élémentaire)
  - 400-411 : type=2 uniquement (style)

max_value = valeur maximale possible (quadroll, source : elliabot.neocities.org)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional

# Valeurs max possibles par effect_id (quadroll = 4 upgrades au maximum)
EFFECT_MAX_VALUE: dict[int, float] = {
    206: 25.0, 210: 25.0, 214: 25.0, 215: 25.0, 218: 25.0,  # Aug. dgts élément
    219: 30.0, 220: 30.0, 221: 30.0, 222: 30.0, 223: 30.0,  # Réd. dgts élément
    224: 30.0, 225: 30.0, 226: 30.0, 227: 30.0,              # CRIT comp
    300: 30.0, 301: 30.0, 302: 30.0,                          # Soins comp
    303: 30.0, 304: 30.0, 305: 30.0,                          # Précision comp
    306: 25.0,  # Renf ATQ/DEF
    307: 30.0,  # Aug VIT
    308: 20.0,  # Dgts bombes
    309: 20.0,  # CRIT reçus
    400: 40.0,  # Drain de vie
    401:  1.5,  # Dgts/HP
    404: 20.0,  # Dgts/ATQ
    405: 20.0,  # Dgts/DEF
    406: 200.0, # Dgts/VIT
    407: 30.0,  # D.CRIT+ PV ok
    408: 60.0,  # D.CRIT+ état enn.
    409: 20.0,  # D.CRIT+ comp alliés
    410: 20.0,  # Contre-attaque
    411: 20.0,  # Autres
}

# Ordre d'affichage exact selon le JSON de traduction
ORDER_ATTRIBUT = [
    206, 210, 214, 215, 218,
    219, 220, 221, 222, 223,
    306, 307, 308, 309,
    400, 401, 404, 405, 406,
    407, 408, 409, 410, 411,
    224, 225, 226,
]

ORDER_TYPE = [
    224, 225, 226,
    300, 301, 302,
    303, 304, 305,
    306, 307, 308, 309,
    400, 401, 404, 405, 406,
    407, 408, 409, 410, 411,
]


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
            ROUND(AVG(ase.value)::numeric, 2) AS avg_value,
            COUNT(*)::int                     AS artifact_count
        FROM artifact_sec_effects ase
        JOIN artifacts a ON a.id = ase.artifact_id
        WHERE {where_clause}
        GROUP BY ase.effect_id
    """)

    result = await db.execute(query, params)
    rows = result.fetchall()
    rows_by_id = {row.effect_id: row for row in rows}

    order = ORDER_TYPE if artifact_type == 2 else ORDER_ATTRIBUT

    averages = []
    for eid in order:
        row = rows_by_id.get(eid)
        if row:
            averages.append({
                "effect_id":      row.effect_id,
                "avg_value":      float(row.avg_value),
                "max_value":      EFFECT_MAX_VALUE.get(row.effect_id, 0.0),
                "artifact_count": row.artifact_count,
            })

    return averages


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
