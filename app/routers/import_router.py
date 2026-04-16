from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
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
    """
    Upload du JSON export Summoners War.
    Remplace automatiquement l'import existant de l'utilisateur.
    """
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un JSON.")

    content = await file.read()

    # Limite de taille : 50 Mo
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 50 Mo).")

    try:
        result = await replace_import(db, user_id, content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'import : {str(e)}")

    return result
