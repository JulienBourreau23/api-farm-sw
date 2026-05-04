import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db

router = APIRouter(prefix="/monsters", tags=["monsters"])

ICONS_DIR = "/srv/sw_coaching/icons/monsters"


@router.get("/icon/{unit_master_id}")
async def get_monster_icon(unit_master_id: int):
    """Sert l'icône d'un monstre depuis le dossier partagé Proxmox."""
    icon_path = f"{ICONS_DIR}/{unit_master_id}.png"
    if not os.path.exists(icon_path):
        raise HTTPException(status_code=404, detail="Icône non trouvée.")
    return FileResponse(icon_path, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/{user_id}")
async def get_owned_monsters(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne les monstres possédés de l'import actif,
    enrichis avec nom FR/EN et élément depuis monsters_ref.
    """
    # ── 1. Récupérer l'import actif ──────────────────────────
    result = await db.execute(
        text("""
            SELECT id FROM sw_imports
            WHERE user_id = :user_id AND is_active = true
            ORDER BY imported_at DESC LIMIT 1
        """),
        {"user_id": user_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Aucun import actif trouvé.")

    import_id = row.id

    # ── 2. JOIN owned_monsters + monsters_ref ────────────────
    result = await db.execute(
        text("""
            SELECT
                om.unit_id_sw,
                om.unit_master_id,
                om.stars,
                om.level,
                mr.name_fr,
                mr.name_en,
                mr.element,
                mr.natural_stars
            FROM owned_monsters om
            LEFT JOIN monsters_ref mr ON mr.id = om.unit_master_id
            WHERE om.import_id = :import_id
            ORDER BY mr.element ASC, mr.natural_stars DESC NULLS LAST
        """),
        {"import_id": import_id}
    )
    rows = result.fetchall()

    ELEMENT_NAMES = {
        1: {"fr": "Feu",     "en": "Fire"},
        2: {"fr": "Eau",     "en": "Water"},
        3: {"fr": "Vent",    "en": "Wind"},
        4: {"fr": "Lumière", "en": "Light"},
        5: {"fr": "Ténèbre", "en": "Dark"},
    }

    monsters = []
    for row in rows:
        element = row.element or 0
        element_names = ELEMENT_NAMES.get(element, {"fr": "Inconnu", "en": "Unknown"})
        monsters.append({
            "unit_id_sw":     row.unit_id_sw,
            "unit_master_id": row.unit_master_id,
            "name_fr":        row.name_fr or f"Monstre {row.unit_master_id}",
            "name_en":        row.name_en or f"Monster {row.unit_master_id}",
            "element":        element,
            "element_fr":     element_names["fr"],
            "element_en":     element_names["en"],
            "natural_stars":  row.natural_stars,
            "stars":          row.stars,
            "level":          row.level,
        })

    return monsters
