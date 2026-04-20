from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.services.importer import replace_import
from app.schemas import ImportResponse

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/{user_id}", response_model=ImportResponse)
async def upload_json(
    user_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un JSON.")

    content = await file.read()

    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 100 Mo).")

    try:
        result = await replace_import(db, user_id, content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'import : {str(e)}")

    return result


@router.get("/{user_id}/active")
async def get_active_import(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retourne l'import actif de l'utilisateur."""
    result = await db.execute(
        text("""
            SELECT id, wizard_id, wizard_name, rune_count, imported_at
            FROM sw_imports
            WHERE user_id = :user_id AND is_active = true
            ORDER BY imported_at DESC
            LIMIT 1
        """),
        {"user_id": user_id}
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Aucun import trouvé.")

    return {
        "import_id":   row.id,
        "wizard_id":   row.wizard_id,
        "wizard_name": row.wizard_name,
        "rune_count":  row.rune_count,
        "imported_at": row.imported_at,
    }
