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
    set_id: Optional[int]   = Query(None, description="ID du set, null = tous sets"),
    slot_no: Optional[int]  = Query(None, ge=1, le=6, description="Slot 1-6, null = tous"),
    pri_stat: Optional[int] = Query(None, description="Filtre stat principale (slots 2/4/6)"),
    min_upgrade: Optional[int] = Query(None, ge=0, le=15, description="Niveau minimum de la rune"),
    refresh: bool           = Query(False, description="Forcer le recalcul même si cache présent"),
    db: AsyncSession        = Depends(get_db),
):
    """
    Retourne les moyennes de substats selon les filtres.
    Utilise le cache si disponible, recalcule sinon.
    
    Exemples d'appels :
    - Tous sets, tous slots       : /averages/1/1
    - Set Violent uniquement      : /averages/1/1?set_id=13
    - Set Violent, slot 4, ATK%   : /averages/1/1?set_id=13&slot_no=4&pri_stat=4
    - Runes +12 minimum           : /averages/1/1?set_id=13&min_upgrade=12
    """
    # Essayer le cache d'abord (sauf si refresh forcé ou filtre min_upgrade)
    if not refresh and min_upgrade is None:
        cached = await get_cached_averages(db, user_id, import_id, set_id, slot_no, pri_stat)
        if cached:
            return _build_response(cached, set_id, slot_no, pri_stat)

    # Calcul frais
    averages = await compute_averages(
        db, user_id, import_id,
        set_id=set_id,
        slot_no=slot_no,
        pri_stat_filter=pri_stat,
        min_upgrade=min_upgrade,
    )

    return _build_response(averages, set_id, slot_no, pri_stat)


def _build_response(averages: list[dict], set_id, slot_no, pri_stat) -> SetAveragesOut:
    return SetAveragesOut(
        set_id=set_id,
        set_name=None,      # Le front enrichit avec son référentiel local
        slot_no=slot_no,
        pri_stat_filter=pri_stat,
        averages=[SubstatAverage(**a) for a in averages],
    )
