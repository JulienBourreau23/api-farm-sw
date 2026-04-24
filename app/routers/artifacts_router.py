from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.services.averages_artifacts import compute_artifact_averages, get_artifact_count

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/{user_id}/{import_id}/averages")
async def get_artifact_averages(
    user_id: int,
    import_id: int,
    type:          Optional[int] = Query(None, description="1=élémentaire, 2=style"),
    attribute:     Optional[int] = Query(None, ge=0, le=5, description="1=Feu 2=Eau 3=Vent 4=Lum 5=Tén"),
    unit_style:    Optional[int] = Query(None, ge=0, le=4, description="1=ATQ 2=DEF 3=PV 4=Support"),
    pri_effect_id: Optional[int] = Query(None, description="100=PV% 101=ATQ% 102=DEF%"),
    min_level:     Optional[int] = Query(None, ge=0, le=15, description="Niveau minimum de l'artefact"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne les moyennes des effets secondaires d'artefacts selon les filtres.

    Exemples :
    - Tous artefacts                          : /artifacts/1/1/averages
    - Élémentaires uniquement                 : /artifacts/1/1/averages?type=1
    - Élémentaires Feu, stat principale ATQ%  : /artifacts/1/1/averages?type=1&attribute=1&pri_effect_id=101
    - Style Attaque, stat principale ATQ%     : /artifacts/1/1/averages?type=2&unit_style=1&pri_effect_id=101
    - Artefacts niveau 15 minimum             : /artifacts/1/1/averages?min_level=15

    Réponse :
    - effect_group 200 = effets communs aux deux types
    - effect_group 300 = effets spécifiques élémentaires
    - effect_group 400 = effets spécifiques style de monstre
    """
    averages = await compute_artifact_averages(
        db, user_id, import_id,
        artifact_type=type,
        attribute=attribute,
        unit_style=unit_style,
        pri_effect_id=pri_effect_id,
        min_level=min_level,
    )

    total = await get_artifact_count(
        db, import_id,
        artifact_type=type,
        attribute=attribute,
        unit_style=unit_style,
        pri_effect_id=pri_effect_id,
    )

    return {
        "filters": {
            "type":          type,
            "attribute":     attribute,
            "unit_style":    unit_style,
            "pri_effect_id": pri_effect_id,
            "min_level":     min_level,
        },
        "artifact_count": total,
        "averages":        averages,
    }


@router.get("/{user_id}/{import_id}/stats")
async def get_artifact_stats(
    user_id: int,
    import_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Statistiques globales des artefacts de l'import :
    - total, répartition par type, par attribut, par style, par stat principale.
    Utile pour alimenter les dropdowns du front (ne proposer que ce qui existe).
    """
    from sqlalchemy import text

    result = await db.execute(
        text("""
            SELECT
                COUNT(*)                                            AS total,
                COUNT(*) FILTER (WHERE type = 1)                   AS elemental_count,
                COUNT(*) FILTER (WHERE type = 2)                   AS style_count,
                COUNT(*) FILTER (WHERE attribute = 1)              AS fire_count,
                COUNT(*) FILTER (WHERE attribute = 2)              AS water_count,
                COUNT(*) FILTER (WHERE attribute = 3)              AS wind_count,
                COUNT(*) FILTER (WHERE attribute = 4)              AS light_count,
                COUNT(*) FILTER (WHERE attribute = 5)              AS dark_count,
                COUNT(*) FILTER (WHERE unit_style = 1)             AS atk_count,
                COUNT(*) FILTER (WHERE unit_style = 2)             AS def_count,
                COUNT(*) FILTER (WHERE unit_style = 3)             AS hp_count,
                COUNT(*) FILTER (WHERE unit_style = 4)             AS support_count,
                COUNT(*) FILTER (WHERE pri_effect_id = 100)        AS pri_hp_count,
                COUNT(*) FILTER (WHERE pri_effect_id = 101)        AS pri_atk_count,
                COUNT(*) FILTER (WHERE pri_effect_id = 102)        AS pri_def_count
            FROM artifacts
            WHERE import_id = :import_id
        """),
        {"import_id": import_id}
    )
    row = result.fetchone()

    return {
        "total":           row.total,
        "by_type": {
            "elemental":   row.elemental_count,
            "style":       row.style_count,
        },
        "by_attribute": {
            "fire":        row.fire_count,
            "water":       row.water_count,
            "wind":        row.wind_count,
            "light":       row.light_count,
            "dark":        row.dark_count,
        },
        "by_unit_style": {
            "atk":         row.atk_count,
            "def":         row.def_count,
            "hp":          row.hp_count,
            "support":     row.support_count,
        },
        "by_pri_effect": {
            "hp":          row.pri_hp_count,
            "atk":         row.pri_atk_count,
            "def":         row.pri_def_count,
        },
    }
