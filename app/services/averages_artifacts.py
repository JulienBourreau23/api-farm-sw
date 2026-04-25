"""
Calcul des moyennes des effets secondaires d'artefacts.

Répartition réelle (vérifiée sur les données) :
  - 206-226 : présents sur les deux types (élémentaires ET style)
  - 300-309 : type=1 uniquement (élémentaire)
  - 400-411 : type=2 uniquement (style)

Ordre d'affichage défini par le JSON de traduction du jeu :
  Artefact_attribut  : 206,210,214,215,218,219,220,221,222,223,306,307,308,309,
                       400,401,404,405,406,407,408,409,410,411,224,225,226
  Artefact_de_type   : 224,225,226,300,301,302,303,304,305,306,307,308,309,
                       400,401,404,405,406,407,408,409,410,411
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional

# Ordre d'affichage exact selon le JSON de traduction
ORDER_ATTRIBUT = [
    206, 210, 214, 215, 218,   # Aug. dgts élément
    219, 220, 221, 222, 223,   # Réd. dgts élément
    306, 307, 308, 309,        # Renf ATQ/DEF, VIT, Bombes, CRIT reçus
    400, 401, 404, 405, 406,   # Drain vie, Dgts/PV, ATQ, DEF, VIT
    407, 408, 409, 410, 411,   # D.CRIT+, Contre-attaque, Autres
    224, 225, 226,             # CRIT comp (en fin car pas dans Artefact_attribut EN premier)
]

ORDER_TYPE = [
    224, 225, 226,             # [Comp.1/2] Aug. CRIT, CRIT [3/4]
    300, 301, 302,             # [Comp.1/2/3] Soins
    303, 304, 305,             # [Comp.1/2/3] Précision
    306, 307, 308, 309,        # Renf ATQ/DEF, VIT, Bombes, CRIT reçus
    400, 401, 404, 405, 406,   # Drain vie, Dgts/PV, ATQ, DEF, VIT
    407, 408, 409, 410, 411,   # D.CRIT+, Contre-attaque, Autres
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
            ROUND(AVG(ase.value)::numeric, 2)                  AS avg_base,
            ROUND(AVG(ase.value + ase.lock_level)::numeric, 2) AS avg_with_lock,
            COUNT(*)::int                                       AS artifact_count
        FROM artifact_sec_effects ase
        JOIN artifacts a ON a.id = ase.artifact_id
        WHERE {where_clause}
        GROUP BY ase.effect_id
    """)

    result = await db.execute(query, params)
    rows = result.fetchall()
    rows_by_id = {row.effect_id: row for row in rows}

    # Choisir l'ordre selon le type demandé
    order = ORDER_TYPE if artifact_type == 2 else ORDER_ATTRIBUT

    averages = []
    for eid in order:
        row = rows_by_id.get(eid)
        if row:
            averages.append({
                "effect_id":      row.effect_id,
                "avg_base":       float(row.avg_base),
                "avg_with_lock":  float(row.avg_with_lock),
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
