"""
Parser du JSON export Summoners War.
Structure sec_eff : [stat_id, base_val, enchant_flag, grind_val]
  - enchant_flag 0 = normal, 1 = enchantée/grinée
occupied_type : 1 = équipée sur unité, 2 = inventaire

Artefacts :
  pri_effect : [effect_id, value, level, 0, 0]
    - 100 = PV%, 101 = ATQ%, 102 = DEF%
  sec_effects : [[effect_id, value, lock_level, 0, 0], ...]
    - lock_level 0-4 = nb de fois upgradé (équivalent grind)
  type : 1 = élémentaire (attribute), 2 = style de monstre (unit_style)
  attribute : 1=Feu 2=Eau 3=Vent 4=Lum 5=Tén (0 si type=2)
  unit_style : 1=ATQ 2=DEF 3=PV 4=Support (0 si type=1)
"""
import json
from datetime import datetime


def extract_all_runes(data: dict) -> list[dict]:
    """Extrait toutes les runes (inventaire + équipées sur unités)."""
    runes = []

    if "runes" in data:
        runes.extend(data["runes"])

    if "unit_list" in data:
        for unit in data["unit_list"]:
            if "runes" in unit:
                runes.extend(unit["runes"])

    return runes


def extract_all_artifacts(data: dict) -> list[dict]:
    """Extrait tous les artefacts (inventaire + équipés sur unités)."""
    artifacts = []

    if "artifacts" in data:
        artifacts.extend(data["artifacts"])

    if "unit_list" in data:
        for unit in data["unit_list"]:
            if "artifacts" in unit:
                artifacts.extend(unit["artifacts"])

    return artifacts


def parse_rune(raw: dict) -> dict | None:
    """
    Transforme une rune brute du JSON en dict prêt pour l'INSERT.
    Retourne None si la rune est invalide.
    """
    try:
        pri_eff    = raw["pri_eff"]
        prefix_eff = raw.get("prefix_eff", [0, 0])
        sec_eff    = raw.get("sec_eff", [])

        innate_stat_id  = prefix_eff[0] if prefix_eff[0] != 0 else None
        innate_stat_val = prefix_eff[1] if prefix_eff[0] != 0 else None

        rune = {
            "rune_id_sw":       raw["rune_id"],
            "set_id":           raw["set_id"],
            "slot_no":          raw["slot_no"],
            "rank":             raw["rank"],
            "class":            raw["class"],
            "upgrade_curr":     raw["upgrade_curr"],
            "is_equipped":      raw["occupied_type"] == 1,
            "occupied_unit_id": raw["occupied_id"] if raw["occupied_type"] == 1 else None,
            "pri_stat_id":      pri_eff[0],
            "pri_stat_val":     pri_eff[1],
            "innate_stat_id":   innate_stat_id,
            "innate_stat_val":  innate_stat_val,
            "substats":         [],
        }

        for eff in sec_eff:
            if len(eff) < 4:
                continue
            stat_id, base_val, enchant_flag, grind_val = eff[0], eff[1], eff[2], eff[3]
            if stat_id == 0:
                continue
            rune["substats"].append({
                "stat_id":      stat_id,
                "base_val":     base_val,
                "grind_val":    grind_val,
                "is_enchanted": enchant_flag == 1,
            })

        return rune

    except (KeyError, IndexError, TypeError):
        return None


def _parse_date(value: str | None) -> datetime | None:
    """Convertit une string 'YYYY-MM-DD HH:MM:SS' en datetime, ou None."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def parse_artifact(raw: dict) -> dict | None:
    """
    Transforme un artefact brut du JSON en dict prêt pour l'INSERT.
    Retourne None si l'artefact est invalide.
    """
    try:
        pri_effect  = raw["pri_effect"]
        sec_effects = raw.get("sec_effects", [])

        artifact = {
            "rid":            raw["rid"],
            "type":           raw["type"],
            "attribute":      raw.get("attribute", 0),
            "unit_style":     raw.get("unit_style", 0),
            "rank":           raw["rank"],
            "level":          raw["level"],
            "pri_effect_id":  pri_effect[0],
            "pri_effect_val": pri_effect[1],
            "occupied_id":    raw.get("occupied_id", 0),
            "locked":         raw.get("locked", 0),
            "date_add":       _parse_date(raw.get("date_add")),
            "sec_effects":    [],
        }

        for eff in sec_effects:
            if len(eff) < 3:
                continue
            effect_id, value, lock_level = eff[0], eff[1], eff[2]
            if effect_id == 0:
                continue
            artifact["sec_effects"].append({
                "effect_id":  effect_id,
                "value":      value,
                "lock_level": lock_level,
            })

        return artifact

    except (KeyError, IndexError, TypeError):
        return None


def parse_sw_json(raw_data: bytes | str | dict) -> tuple[dict, list[dict], list[dict]]:
    """
    Point d'entrée principal.
    Retourne (wizard_info, runes_parsées, artifacts_parsés).
    """
    if isinstance(raw_data, (bytes, str)):
        data = json.loads(raw_data)
    else:
        data = raw_data

    wizard_info = {
        "wizard_id":   data["wizard_info"]["wizard_id"],
        "wizard_name": data["wizard_info"]["wizard_name"],
    }

    raw_runes = extract_all_runes(data)
    runes = [p for raw in raw_runes if (p := parse_rune(raw))]

    raw_artifacts = extract_all_artifacts(data)
    artifacts = [p for raw in raw_artifacts if (p := parse_artifact(raw))]

    return wizard_info, runes, artifacts
