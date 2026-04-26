"""
Calcul des moyennes des effets secondaires d'artefacts.

Mapping basé sur sw-exporter/app/mapping.js (source officielle).

Répartition réelle vérifiée sur les données :
  type=1 (Attribut)  : 206-226 + 300-309
  type=2 (Archetype) : 206-226 + 400-411

Valeurs max théoriques (source : elliabot.neocities.org, quadroll)
Note : corrections appliquées à l'import dans parser.py pour 221 et 223.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional

# Valeurs max en % réels après corrections (quadroll = 4 upgrades max)
EFFECT_MAX_VALUE: dict[int, float] = {
    # Communs type1 + type2 (206-226)
    204: 25.0,   # Effet aug. ATQ
    205: 25.0,   # Effet aug. DEF
    206: 30.0,   # Effet aug. VIT
    207: 30.0,   # Effet Tx Crit
    208: 20.0,   # Dgts contre-attaque
    209: 20.0,   # Dgts attaque conjointe
    210: 20.0,   # Dgts bombes
    213: 20.0,   # Dgts reçus sous incapacité
    214: 20.0,   # Dgts CRIT reçus
    215: 40.0,   # Drain de vie
    218:  1.5,   # Dgts supp. % PV
    219: 20.0,   # Dgts supp. % ATQ
    220: 20.0,   # Dgts supp. % DEF
    221: 200.0,  # Dgts supp. % VIT (après ÷10 dans parser)
    222: 30.0,   # D.CRIT+ bon état PV enn.
    223: 60.0,   # D.CRIT+ mauvais état PV enn. (après ÷2 dans parser)
    224: 30.0,   # D.CRIT skill cible unique
    225: 20.0,   # Contre-attaque/Co-op
    226: 25.0,   # Effet aug. ATQ/DEF
    # Spécifiques type=1 (300-309)
    300: 25.0,   # Dgts infligés Feu
    301: 25.0,   # Dgts infligés Eau
    302: 25.0,   # Dgts infligés Vent
    303: 25.0,   # Dgts infligés Lum.
    304: 25.0,   # Dgts infligés Tén.
    305: 30.0,   # Dgts reçus Feu
    306: 30.0,   # Dgts reçus Eau
    307: 30.0,   # Dgts reçus Vent
    308: 30.0,   # Dgts reçus Lum.
    309: 30.0,   # Dgts reçus Tén.
    # Spécifiques type=2 (400-411)
    400: 30.0,   # [Comp.1] Dgts CRIT
    401: 30.0,   # [Comp.2] Dgts CRIT
    402: 30.0,   # [Comp.3] Dgts CRIT
    403: 30.0,   # [Comp.4] Dgts CRIT
    404: 30.0,   # [Comp.1] Soins
    405: 30.0,   # [Comp.2] Soins
    406: 30.0,   # [Comp.3] Soins
    407: 30.0,   # [Comp.1] Précision
    408: 30.0,   # [Comp.2] Précision
    409: 30.0,   # [Comp.3] Précision
    410: 30.0,   # [Comp. 3/4] Dgts CRIT
    411: 30.0,   # 1re attaque Dgts CRIT
}

# Ordre d'affichage pour chaque type — spécifiques en premier comme dans le jeu
ORDER_ATTRIBUT = [
    # Spécifiques type=1 en premier
    300, 301, 302, 303, 304,   # Dgts infligés par élément
    305, 306, 307, 308, 309,   # Dgts reçus par élément
    # Communs ensuite
    204, 205, 206, 207,
    208, 209, 210,
    213, 214, 215,
    218, 219, 220, 221,
    222, 223, 224, 225, 226,
]

ORDER_ARCHETYPE = [
    # Spécifiques type=2 en premier
    400, 401, 402, 403,        # Dgts CRIT comp 1/2/3/4
    404, 405, 406,             # Soins comp 1/2/3
    407, 408, 409,             # Précision comp 1/2/3
    410, 411,                  # Dgts CRIT [3/4] + 1re attaque
    # Communs ensuite
    204, 205, 206, 207,
    208, 209, 210,
    213, 214, 215,
    218, 219, 220, 221,
    222, 223, 224, 225, 226,
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

    order = ORDER_ARCHETYPE if artifact_type == 2 else ORDER_ATTRIBUT

    averages = []
    for eid in order:
        row = rows_by_id.get(eid)
        if row:
            averages.append({
                "effect_id":      eid,
                "avg_value":      float(row.avg_value),
                "max_value":      EFFECT_MAX_VALUE.get(eid, 0.0),
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
