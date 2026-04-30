from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.services.averages import compute_averages, get_cached_averages
from app.schemas import SetAveragesOut, SubstatAverage

router = APIRouter(prefix="/averages", tags=["averages"])


@router.get("/{user_id}/{import_id}", response_model=SetAveragesOut)
async def get_averages(
    user_id: int,
    import_id: int,
    set_id: Optional[int]    = Query(None, description="ID du set, null = tous sets"),
    slot_no: Optional[int]   = Query(None, ge=1, le=6, description="Slot 1-6, null = tous"),
    pri_stat: Optional[int]  = Query(None, description="Filtre stat principale (slots 2/4/6)"),
    min_upgrade: Optional[int] = Query(None, ge=0, le=15, description="Niveau minimum de la rune"),
    is_ancient: Optional[bool] = Query(None, description="True = immémorial, False = normales, null = toutes"),
    refresh: bool            = Query(False, description="Forcer le recalcul même si cache présent"),
    db: AsyncSession         = Depends(get_db),
):
    """
    Retourne les moyennes de substats selon les filtres.
    Utilise le cache si disponible (sauf si is_ancient ou min_upgrade sont spécifiés).

    Exemples d'appels :
    - Tous sets, tous slots         : /averages/1/1
    - Runes normales uniquement     : /averages/1/1?is_ancient=false
    - Runes immémorial uniquement   : /averages/1/1?is_ancient=true
    - Set Violent, runes normales   : /averages/1/1?set_id=13&is_ancient=false
    """
    # Cache uniquement si pas de filtre is_ancient ni min_upgrade
    use_cache = not refresh and min_upgrade is None and is_ancient is None

    if use_cache:
        cached = await get_cached_averages(db, user_id, import_id, set_id, slot_no, pri_stat)
        if cached:
            return _build_response(cached, set_id, slot_no, pri_stat)

    averages = await compute_averages(
        db, user_id, import_id,
        set_id=set_id,
        slot_no=slot_no,
        pri_stat_filter=pri_stat,
        min_upgrade=min_upgrade,
        is_ancient=is_ancient,
    )

    return _build_response(averages, set_id, slot_no, pri_stat)


def _build_response(averages: list[dict], set_id, slot_no, pri_stat) -> SetAveragesOut:
    return SetAveragesOut(
        set_id=set_id,
        set_name=None,
        slot_no=slot_no,
        pri_stat_filter=pri_stat,
        averages=[SubstatAverage(**a) for a in averages],
    )
