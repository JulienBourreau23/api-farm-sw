"""
Calcul des moyennes de substats avec filtres optionnels.
Deux colonnes : moyenne sans grind (base) et moyenne avec grind (base + grind_val).
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional


async def compute_averages(
    db: AsyncSession,
    user_id: int,
    import_id: int,
    set_id: Optional[int] = None,
    slot_no: Optional[int] = None,
    pri_stat_filter: Optional[int] = None,
    min_upgrade: Optional[int] = None,
) -> list[dict]:
    """
    Calcule les moyennes des substats selon les filtres.
    Sauvegarde le résultat dans stats_averages (cache).
    Retourne la liste des moyennes par stat.
    """

    # ── Construction dynamique de la requête ────────────────────
    conditions = ["r.import_id = :import_id"]
    params: dict = {"import_id": import_id}

    if set_id is not None:
        conditions.append("r.set_id = :set_id")
        params["set_id"] = set_id

    if slot_no is not None:
        conditions.append("r.slot_no = :slot_no")
        params["slot_no"] = slot_no

    if pri_stat_filter is not None:
        conditions.append("r.pri_stat_id = :pri_stat_filter")
        params["pri_stat_filter"] = pri_stat_filter

    if min_upgrade is not None:
        conditions.append("r.upgrade_curr >= :min_upgrade")
        params["min_upgrade"] = min_upgrade

    where_clause = " AND ".join(conditions)

    query = text(f"""
        SELECT
            st.id            AS stat_id,
            st.code          AS stat_code,
            st.name_fr       AS stat_name_fr,
            st.is_percent    AS is_percent,
            ROUND(AVG(rs.base_val)::numeric, 2)                    AS avg_base,
            ROUND(AVG(rs.base_val + rs.grind_val)::numeric, 2)     AS avg_with_grind,
            COUNT(*)::int                                           AS rune_count
        FROM rune_substats rs
        JOIN runes r       ON r.id  = rs.rune_id
        JOIN stat_types st ON st.id = rs.stat_id
        WHERE {where_clause}
        GROUP BY st.id, st.code, st.name_fr, st.is_percent
        ORDER BY st.id
    """)

    result = await db.execute(query, params)
    rows = result.fetchall()

    averages = [
        {
            "stat_id":        row.stat_id,
            "stat_code":      row.stat_code,
            "stat_name_fr":   row.stat_name_fr,
            "is_percent":     row.is_percent,
            "avg_base":       float(row.avg_base),
            "avg_with_grind": float(row.avg_with_grind),
            "rune_count":     row.rune_count,
        }
        for row in rows
    ]

    # ── Mise en cache ────────────────────────────────────────────
    await db.execute(
        text("""
            DELETE FROM stats_averages
            WHERE user_id = :user_id
              AND import_id = :import_id
              AND (set_id IS NOT DISTINCT FROM :set_id)
              AND (slot_no IS NOT DISTINCT FROM :slot_no)
              AND (pri_stat_filter IS NOT DISTINCT FROM :pri_stat_filter)
        """),
        {
            "user_id":         user_id,
            "import_id":       import_id,
            "set_id":          set_id,
            "slot_no":         slot_no,
            "pri_stat_filter": pri_stat_filter,
        }
    )

    for avg in averages:
        await db.execute(
            text("""
                INSERT INTO stats_averages (
                    user_id, import_id, set_id, slot_no,
                    pri_stat_filter, stat_id,
                    avg_base, avg_with_grind, rune_count
                ) VALUES (
                    :user_id, :import_id, :set_id, :slot_no,
                    :pri_stat_filter, :stat_id,
                    :avg_base, :avg_with_grind, :rune_count
                )
            """),
            {
                "user_id":         user_id,
                "import_id":       import_id,
                "set_id":          set_id,
                "slot_no":         slot_no,
                "pri_stat_filter": pri_stat_filter,
                "stat_id":         avg["stat_id"],
                "avg_base":        avg["avg_base"],
                "avg_with_grind":  avg["avg_with_grind"],
                "rune_count":      avg["rune_count"],
            }
        )

    await db.commit()

    return averages


async def get_cached_averages(
    db: AsyncSession,
    user_id: int,
    import_id: int,
    set_id: Optional[int] = None,
    slot_no: Optional[int] = None,
    pri_stat_filter: Optional[int] = None,
) -> list[dict] | None:
    """
    Retourne les moyennes depuis le cache si disponibles, sinon None.
    """
    result = await db.execute(
        text("""
            SELECT
                sa.stat_id, st.code AS stat_code, st.name_fr AS stat_name_fr,
                st.is_percent, sa.avg_base, sa.avg_with_grind, sa.rune_count
            FROM stats_averages sa
            JOIN stat_types st ON st.id = sa.stat_id
            WHERE sa.user_id   = :user_id
              AND sa.import_id = :import_id
              AND (sa.set_id IS NOT DISTINCT FROM :set_id)
              AND (sa.slot_no IS NOT DISTINCT FROM :slot_no)
              AND (sa.pri_stat_filter IS NOT DISTINCT FROM :pri_stat_filter)
            ORDER BY sa.stat_id
        """),
        {
            "user_id":         user_id,
            "import_id":       import_id,
            "set_id":          set_id,
            "slot_no":         slot_no,
            "pri_stat_filter": pri_stat_filter,
        }
    )
    rows = result.fetchall()

    if not rows:
        return None

    return [
        {
            "stat_id":        row.stat_id,
            "stat_code":      row.stat_code,
            "stat_name_fr":   row.stat_name_fr,
            "is_percent":     row.is_percent,
            "avg_base":       float(row.avg_base),
            "avg_with_grind": float(row.avg_with_grind),
            "rune_count":     row.rune_count,
        }
        for row in rows
    ]