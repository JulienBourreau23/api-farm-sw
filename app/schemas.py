from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ── Import ──────────────────────────────────────────────────

class ImportResponse(BaseModel):
    import_id:      int
    wizard_name:    str
    wizard_id:      int
    rune_count:     int
    artifact_count: int
    imported_at:    datetime


# ── Rune ────────────────────────────────────────────────────

class SubstatOut(BaseModel):
    stat_id:      int
    stat_code:    str
    stat_name_fr: str
    base_val:     int
    grind_val:    int
    total_val:    int           # base_val + grind_val
    is_enchanted: bool
    is_percent:   bool


class RuneOut(BaseModel):
    id:               int
    rune_id_sw:       int
    set_id:           int
    set_name:         str
    slot_no:          int
    rank:             int
    upgrade_curr:     int
    is_equipped:      bool
    pri_stat_id:      int
    pri_stat_code:    str
    pri_stat_name_fr: str
    pri_stat_val:     int
    innate_stat_id:   Optional[int]
    innate_stat_name_fr: Optional[str]
    innate_stat_val:  Optional[int]
    substats:         list[SubstatOut]


# ── Artefact ────────────────────────────────────────────────

class ArtifactSecEffectOut(BaseModel):
    effect_id:  int
    value:      int
    lock_level: int             # 0 = libre, 1-4 = nb upgrades


class ArtifactOut(BaseModel):
    id:             int
    rid:            int
    type:           int         # 1 = élémentaire, 2 = style
    attribute:      int         # 0-5
    unit_style:     int         # 0-4
    rank:           int
    level:          int
    pri_effect_id:  int         # 100=PV% 101=ATQ% 102=DEF%
    pri_effect_val: int
    occupied_id:    int         # 0 = inventaire
    sec_effects:    list[ArtifactSecEffectOut]


# ── Moyennes runes ───────────────────────────────────────────

class SubstatAverage(BaseModel):
    stat_id:        int
    stat_code:      str
    stat_name_fr:   str
    is_percent:     bool
    avg_base:       float
    avg_with_grind: float
    rune_count:     int


class SetAveragesOut(BaseModel):
    set_id:          Optional[int]      # None = tous sets confondus
    set_name:        Optional[str]
    slot_no:         Optional[int]      # None = tous slots
    pri_stat_filter: Optional[int]
    averages:        list[SubstatAverage]


# ── Moyennes artefacts ───────────────────────────────────────

class ArtifactEffectAverage(BaseModel):
    effect_id:        int
    avg_base:         float              # moyenne sans lock
    avg_with_lock:    float              # moyenne avec upgrades lock
    artifact_count:   int


class ArtifactAveragesOut(BaseModel):
    type:       Optional[int]           # None = tous types
    attribute:  Optional[int]           # None = tous attributs
    unit_style: Optional[int]           # None = tous styles
    averages:   list[ArtifactEffectAverage]


# ── Requête de calcul runes ──────────────────────────────────

class ComputeAveragesRequest(BaseModel):
    user_id:          int
    import_id:        int
    set_id:           Optional[int] = None
    slot_no:          Optional[int] = None
    pri_stat_filter:  Optional[int] = None
    min_upgrade:      Optional[int] = None
