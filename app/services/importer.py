"""
Service d'import : remplace l'ancien import de l'utilisateur dans une transaction unique.
Si quelque chose plante, l'ancien import est conservé intact.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.parser import parse_sw_json


async def replace_import(
    db: AsyncSession,
    user_id: int,
    raw_data: bytes,
) -> dict:
    """
    Parse le JSON et remplace l'import existant de l'utilisateur.
    Retourne les infos du nouvel import.
    """
    wizard_info, runes, artifacts = parse_sw_json(raw_data)

    async with db.begin():
        # ── 1. Récupérer l'ancien import actif ──────────────────
        result = await db.execute(
            text("SELECT id FROM sw_imports WHERE user_id = :uid AND is_active = true"),
            {"uid": user_id}
        )
        old_import = result.fetchone()

        # ── 2. Créer le nouvel import ────────────────────────────
        result = await db.execute(
            text("""
                INSERT INTO sw_imports (user_id, wizard_id, wizard_name, rune_count, is_active)
                VALUES (:user_id, :wizard_id, :wizard_name, :rune_count, true)
                RETURNING id, imported_at
            """),
            {
                "user_id":     user_id,
                "wizard_id":   wizard_info["wizard_id"],
                "wizard_name": wizard_info["wizard_name"],
                "rune_count":  len(runes),
            }
        )
        new_import    = result.fetchone()
        new_import_id = new_import.id

        # ── 3. Insérer les runes ─────────────────────────────────
        for rune in runes:
            result = await db.execute(
                text("""
                    INSERT INTO runes (
                        import_id, rune_id_sw, set_id, slot_no, rank, class,
                        upgrade_curr, is_equipped, occupied_unit_id,
                        pri_stat_id, pri_stat_val,
                        innate_stat_id, innate_stat_val
                    ) VALUES (
                        :import_id, :rune_id_sw, :set_id, :slot_no, :rank, :class,
                        :upgrade_curr, :is_equipped, :occupied_unit_id,
                        :pri_stat_id, :pri_stat_val,
                        :innate_stat_id, :innate_stat_val
                    ) RETURNING id
                """),
                {
                    "import_id":        new_import_id,
                    "rune_id_sw":       rune["rune_id_sw"],
                    "set_id":           rune["set_id"],
                    "slot_no":          rune["slot_no"],
                    "rank":             rune["rank"],
                    "class":            rune["class"],
                    "upgrade_curr":     rune["upgrade_curr"],
                    "is_equipped":      rune["is_equipped"],
                    "occupied_unit_id": rune["occupied_unit_id"],
                    "pri_stat_id":      rune["pri_stat_id"],
                    "pri_stat_val":     rune["pri_stat_val"],
                    "innate_stat_id":   rune["innate_stat_id"],
                    "innate_stat_val":  rune["innate_stat_val"],
                }
            )
            new_rune_id = result.fetchone().id

            for sub in rune["substats"]:
                await db.execute(
                    text("""
                        INSERT INTO rune_substats (rune_id, stat_id, base_val, grind_val, is_enchanted)
                        VALUES (:rune_id, :stat_id, :base_val, :grind_val, :is_enchanted)
                    """),
                    {
                        "rune_id":      new_rune_id,
                        "stat_id":      sub["stat_id"],
                        "base_val":     sub["base_val"],
                        "grind_val":    sub["grind_val"],
                        "is_enchanted": sub["is_enchanted"],
                    }
                )

        # ── 4. Insérer les artefacts ─────────────────────────────
        for artifact in artifacts:
            result = await db.execute(
                text("""
                    INSERT INTO artifacts (
                        import_id, rid, type, attribute, unit_style,
                        rank, level, pri_effect_id, pri_effect_val,
                        occupied_id, locked, date_add
                    ) VALUES (
                        :import_id, :rid, :type, :attribute, :unit_style,
                        :rank, :level, :pri_effect_id, :pri_effect_val,
                        :occupied_id, :locked, :date_add
                    ) RETURNING id
                """),
                {
                    "import_id":      new_import_id,
                    "rid":            artifact["rid"],
                    "type":           artifact["type"],
                    "attribute":      artifact["attribute"],
                    "unit_style":     artifact["unit_style"],
                    "rank":           artifact["rank"],
                    "level":          artifact["level"],
                    "pri_effect_id":  artifact["pri_effect_id"],
                    "pri_effect_val": artifact["pri_effect_val"],
                    "occupied_id":    artifact["occupied_id"],
                    "locked":         artifact["locked"],
                    "date_add":       artifact["date_add"],
                }
            )
            new_artifact_id = result.fetchone().id

            for eff in artifact["sec_effects"]:
                await db.execute(
                    text("""
                        INSERT INTO artifact_sec_effects (artifact_id, effect_id, value, lock_level)
                        VALUES (:artifact_id, :effect_id, :value, :lock_level)
                    """),
                    {
                        "artifact_id": new_artifact_id,
                        "effect_id":   eff["effect_id"],
                        "value":       eff["value"],
                        "lock_level":  eff["lock_level"],
                    }
                )

        # ── 5. Supprimer l'ancien import (CASCADE runes + artefacts) ──
        if old_import:
            await db.execute(
                text("DELETE FROM sw_imports WHERE id = :id"),
                {"id": old_import.id}
            )

        # ── 6. Invalider le cache des moyennes ───────────────────
        await db.execute(
            text("DELETE FROM stats_averages WHERE user_id = :uid"),
            {"uid": user_id}
        )

    return {
        "import_id":      new_import_id,
        "wizard_name":    wizard_info["wizard_name"],
        "wizard_id":      wizard_info["wizard_id"],
        "rune_count":     len(runes),
        "artifact_count": len(artifacts),
        "imported_at":    new_import.imported_at,
    }
