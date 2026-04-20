"""
Endpoints statistiques optimisés — une seule requête SQL par appel.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/{user_id}/top-sets")
async def get_top_sets(
    user_id: int,
    limit: int = Query(5, ge=1, le=23),
    db: AsyncSession = Depends(get_db),
):
    """Top sets par nombre de runes — une seule requête SQL."""
    result = await db.execute(
        text("""
            SELECT
                r.set_id,
                rs.name        AS set_name,
                COUNT(r.id)    AS rune_count
            FROM runes r
            JOIN sw_imports si  ON si.id   = r.import_id
            JOIN rune_sets rs   ON rs.id   = r.set_id
            WHERE si.user_id   = :user_id
              AND si.is_active = true
            GROUP BY r.set_id, rs.name
            ORDER BY rune_count DESC
            LIMIT :limit
        """),
        {"user_id": user_id, "limit": limit}
    )
    rows = result.fetchall()
    return [
        {"set_id": row.set_id, "set_name": row.set_name, "rune_count": row.rune_count}
        for row in rows
    ]


@router.get("/{user_id}/top3-by-stat")
async def get_top3_by_stat(
    user_id: int,
    stat_code: str = Query(...),
    min_pct: float = Query(10.0, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Top 3 sets pour une stat donnée.
    Seuil calculé sur le total de runes ayant cette stat en substat.
    """
    result = await db.execute(
        text("""
            WITH stat_total AS (
                SELECT COUNT(sub.id) AS total_with_stat
                FROM rune_substats sub
                JOIN runes r       ON r.id  = sub.rune_id
                JOIN stat_types st ON st.id = sub.stat_id
                JOIN sw_imports si ON si.id = r.import_id
                WHERE si.user_id   = :user_id
                  AND si.is_active = true
                  AND st.code      = :stat_code
                  AND sub.stat_id != r.pri_stat_id
            ),
            set_stats AS (
                SELECT
                    r.set_id,
                    rs.name                                               AS set_name,
                    ROUND(AVG(sub.base_val)::numeric, 2)                 AS avg_base,
                    ROUND(AVG(sub.base_val + sub.grind_val)::numeric, 2) AS avg_with_grind,
                    COUNT(sub.id)                                         AS rune_count,
                    st.is_percent
                FROM rune_substats sub
                JOIN runes r        ON r.id   = sub.rune_id
                JOIN rune_sets rs   ON rs.id  = r.set_id
                JOIN stat_types st  ON st.id  = sub.stat_id
                JOIN sw_imports si  ON si.id  = r.import_id
                WHERE si.user_id   = :user_id
                  AND si.is_active = true
                  AND st.code      = :stat_code
                  AND sub.stat_id != r.pri_stat_id
                GROUP BY r.set_id, rs.name, st.is_percent
            )
            SELECT
                ss.set_id, ss.set_name, ss.avg_base, ss.avg_with_grind,
                ss.rune_count, ss.is_percent,
                ROUND((ss.rune_count::numeric / NULLIF(st.total_with_stat, 0)) * 100, 1) AS pct
            FROM set_stats ss, stat_total st
            WHERE (ss.rune_count::numeric / NULLIF(st.total_with_stat, 0)) * 100 >= :min_pct
            ORDER BY ss.avg_with_grind DESC
            LIMIT 3
        """),
        {"user_id": user_id, "stat_code": stat_code, "min_pct": min_pct}
    )
    rows = result.fetchall()
    return [
        {
            "set_id": row.set_id, "set_name": row.set_name,
            "avg_base": float(row.avg_base), "avg_with_grind": float(row.avg_with_grind),
            "rune_count": row.rune_count, "is_percent": row.is_percent, "pct": float(row.pct),
        }
        for row in rows
    ]


@router.get("/{user_id}/total-runes")
async def get_total_runes(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Total de runes de l'import actif."""
    result = await db.execute(
        text("""
            SELECT COUNT(r.id) AS total
            FROM runes r
            JOIN sw_imports si ON si.id = r.import_id
            WHERE si.user_id = :user_id AND si.is_active = true
        """),
        {"user_id": user_id}
    )
    row = result.fetchone()
    return {"total_runes": row.total if row else 0}


@router.get("/{user_id}/available-pri-stats")
async def get_available_pri_stats(
    user_id: int,
    set_id: int = Query(..., description="ID du set de runes"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne pour chaque slot pair (2, 4, 6) les stats principales
    disponibles avec leur count de runes.
    Une stat est disponible si au moins une rune existe avec cette
    combinaison set_id + slot_no + pri_stat_id.
    """
    result = await db.execute(
        text("""
            SELECT
                r.slot_no,
                r.pri_stat_id,
                st.code      AS stat_code,
                st.name_fr   AS stat_name_fr,
                COUNT(r.id)  AS rune_count
            FROM runes r
            JOIN sw_imports si  ON si.id  = r.import_id
            JOIN stat_types st  ON st.id  = r.pri_stat_id
            WHERE si.user_id   = :user_id
              AND si.is_active = true
              AND r.set_id     = :set_id
              AND r.slot_no    IN (2, 4, 6)
            GROUP BY r.slot_no, r.pri_stat_id, st.code, st.name_fr
            ORDER BY r.slot_no, rune_count DESC
        """),
        {"user_id": user_id, "set_id": set_id}
    )
    rows = result.fetchall()

    # Grouper par slot
    slots: dict = {2: [], 4: [], 6: []}
    for row in rows:
        slots[row.slot_no].append({
            "stat_id":    row.pri_stat_id,
            "stat_code":  row.stat_code,
            "stat_name":  row.stat_name_fr,
            "rune_count": row.rune_count,
        })

    return slots
