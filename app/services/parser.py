"""
Parser du JSON export Summoners War.
Structure sec_eff : [stat_id, base_val, enchant_flag, grind_val]
  - enchant_flag 0 = normal, 1 = enchantée/grinée
occupied_type : 1 = équipée sur unité, 2 = inventaire
"""
import json
from typing import Any


def extract_all_runes(data: dict) -> list[dict]:
    """Extrait toutes les runes (inventaire + équipées sur unités)."""
    runes = []

    # Runes en inventaire
    if "runes" in data:
        runes.extend(data["runes"])

    # Runes équipées sur les unités
    if "unit_list" in data:
        for unit in data["unit_list"]:
            if "runes" in unit:
                runes.extend(unit["runes"])

    return runes


def parse_rune(raw: dict) -> dict:
    """
    Transforme une rune brute du JSON en dict prêt pour l'INSERT.
    Retourne None si la rune est invalide.
    """
    try:
        pri_eff = raw["pri_eff"]
        prefix_eff = raw.get("prefix_eff", [0, 0])
        sec_eff = raw.get("sec_eff", [])

        # Innate stat (prefix_eff[0] == 0 = pas d'innate)
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
            "substats": []
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


def parse_sw_json(raw_data: bytes | str | dict) -> tuple[dict, list[dict]]:
    """
    Point d'entrée principal.
    Retourne (wizard_info, runes_parsées).
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
    runes = []
    for raw in raw_runes:
        parsed = parse_rune(raw)
        if parsed:
            runes.append(parsed)

    return wizard_info, runes
