from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ── Import ──────────────────────────────────────────────────

class ImportResponse(BaseModel):
    import_id: int
    wizard_name: str
    wizard_id: int
    rune_count: int
    imported_at: datetime


# ── Rune ────────────────────────────────────────────────────

class SubstatOut(BaseModel):
    stat_id: int
    stat_code: str
    stat_name_fr: str
    base_val: int
    grind_val: int
    total_val: int          # base_val + grind_val
    is_enchanted: bool
    is_percent: bool


class RuneOut(BaseModel):
    id: int
    rune_id_sw: int
    set_id: int
    set_name: str
    slot_no: int
    rank: int
    upgrade_curr: int
    is_equipped: bool
    pri_stat_id: int
    pri_stat_code: str
    pri_stat_name_fr: str
    pri_stat_val: int
    innate_stat_id: Optional[int]
    innate_stat_name_fr: Optional[str]
    innate_stat_val: Optional[int]
    substats: list[SubstatOut]


# ── Moyennes ────────────────────────────────────────────────

class SubstatAverage(BaseModel):
    stat_id: int
    stat_code: str
    stat_name_fr: str
    is_percent: bool
    avg_base: float
    avg_with_grind: float
    rune_count: int


class SetAveragesOut(BaseModel):
    set_id: Optional[int]       # None = tous sets confondus
    set_name: Optional[str]
    slot_no: Optional[int]      # None = tous slots
    pri_stat_filter: Optional[int]
    averages: list[SubstatAverage]


# ── Requête de calcul ────────────────────────────────────────

class ComputeAveragesRequest(BaseModel):
    user_id: int
    import_id: int
    set_id: Optional[int] = None
    slot_no: Optional[int] = None
    pri_stat_filter: Optional[int] = None
    min_upgrade: Optional[int] = None   # ex: 12 pour runes +12 minimum
