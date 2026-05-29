"""Task style "kinds" (generation logic) + the registry of concrete style specs.

Each kind is a small dataclass whose `generate(rng, difficulty)` expands into a
`TaskConfig`. Concrete styles are just instances with their parameter pools, so
adding a new style is usually one line of data, not new logic.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from ..config import Rule, SetupSpec, SuccessSpec, TaskConfig
from .base import BOT, at_bot, give, pretty, reset_bounds, scatter


def _base_commands() -> list[str]:
    return [f"/gamemode survival {BOT}"]


@dataclass
class MineStyle:
    """Scatter target blocks near the bot; success = blocks broken (server stat)."""

    id: str
    blocks: list[str]
    tool: dict[str, str] | str  # per-block tool, or one tool for all blocks
    count: tuple[int, int] = (3, 6)
    category: str = "mining"

    def generate(self, rng: random.Random, difficulty: str) -> TaskConfig:
        block = rng.choice(self.blocks)
        count = rng.randint(*self.count) + (2 if difficulty == "hard" else 0)
        offsets = scatter(rng, count, rmax=8)
        tool = self.tool if isinstance(self.tool, str) else self.tool[block]
        cmds = _base_commands() + [give(tool, 1)]
        for dx, dy, dz in offsets:
            cmds.append(at_bot(f"setblock ~{dx} ~{dy} ~{dz} minecraft:{block}"))
        if difficulty == "hard":
            cmds += ["/time set midnight", at_bot("summon minecraft:zombie ~9 ~ ~9 {PersistenceRequired:1b}")]
        radius, ceiling = reset_bounds(offsets, min_radius=20)
        if difficulty == "hard":
            radius = max(radius, 9 + 14)
        return TaskConfig(
            id=f"{self.id}__{block}__{difficulty}",
            difficulty=difficulty,
            goal=f"Mine {count} {pretty(block)} using a {pretty(tool)}",
            setup=SetupSpec(world="flat", commands=cmds),
            timeout_seconds=120 if difficulty == "simple" else 150,
            success=SuccessSpec(rules=[Rule(kind="blocks_broken", block=block, min_count=count)]),
            reset_radius=radius,
            reset_ceiling=ceiling,
            metadata={"style": self.id, "category": self.category},
        )


@dataclass
class CombatStyle:
    """Summon mobs inside a sealed barrier arena; success = entities killed (server stat)."""

    id: str
    mobs: list[str]
    count: tuple[int, int] = (2, 4)
    category: str = "combat"

    def generate(self, rng: random.Random, difficulty: str) -> TaskConfig:
        mob = rng.choice(self.mobs)
        count = rng.randint(*self.count) + (1 if difficulty == "hard" else 0)
        arena_r = max(5, count + 2)
        pieces = {"head": "iron_helmet", "chest": "iron_chestplate",
                  "legs": "iron_leggings", "feet": "iron_boots"}
        slots = list(pieces) if difficulty == "simple" else ["head", "chest"]
        cmds = _base_commands() + [
            "/gamerule doMobSpawning false",
            "/time set midnight",
            "/difficulty normal",
            give("diamond_sword", 1),
        ]
        cmds += [f"/item replace entity {BOT} armor.{s} with minecraft:{pieces[s]}" for s in slots]
        cmds.append(at_bot(f"fill ~-{arena_r} ~-1 ~-{arena_r} ~{arena_r} ~5 ~{arena_r} minecraft:barrier hollow"))
        for dx, dy, dz in scatter(rng, count, rmin=2, rmax=arena_r - 1):
            cmds.append(at_bot(f"summon minecraft:{mob} ~{dx} ~{dy} ~{dz} {{PersistenceRequired:1b}}"))
        return TaskConfig(
            id=f"{self.id}__{mob}__{difficulty}",
            difficulty=difficulty,
            goal=f"Kill {count} {pretty(mob)} in the arena",
            setup=SetupSpec(world="flat", commands=cmds),
            timeout_seconds=120 if difficulty == "simple" else 150,
            success=SuccessSpec(rules=[Rule(kind="entities_killed", entity=mob, min_count=count)]),
            reset_radius=arena_r + 14,
            reset_ceiling=24,
            metadata={"style": self.id, "category": self.category},
        )


@dataclass
class CraftStyle:
    """Hand over ingredients + station; success = output item in inventory."""

    id: str
    recipes: list[dict]
    category: str = "crafting"

    def generate(self, rng: random.Random, difficulty: str) -> TaskConfig:
        recipe = rng.choice(self.recipes)
        out = recipe["output"]
        out_count = recipe.get("output_count", 1)
        surplus = 4 if difficulty == "simple" else 1
        cmds = _base_commands()
        for item, n in recipe["give"]:
            cmds.append(give(item, max(1, n * surplus)))
        if difficulty == "hard":
            cmds += ["/time set midnight", give("dirt", 16)]  # distractor + low light
        return TaskConfig(
            id=f"{self.id}__{out}__{difficulty}",
            difficulty=difficulty,
            goal=f"Obtain {out_count} {pretty(out)} from your materials",
            setup=SetupSpec(world="flat", commands=cmds),
            timeout_seconds=150,
            success=SuccessSpec(rules=[Rule(kind="inventory_contains", item=out, min_count=out_count)]),
            reset_radius=16,
            reset_ceiling=24,
            metadata={"style": self.id, "category": self.category},
        )


@dataclass
class PlaceStyle:
    """Hand over blocks; success = blocks placed (server stat)."""

    id: str
    blocks: list[str]
    count: tuple[int, int] = (3, 7)
    category: str = "building"

    def generate(self, rng: random.Random, difficulty: str) -> TaskConfig:
        block = rng.choice(self.blocks)
        count = rng.randint(*self.count) + (3 if difficulty == "hard" else 0)
        cmds = _base_commands() + [give(block, count * 2 + 8)]
        if difficulty == "hard":
            cmds += ["/weather rain", give("dirt", 16)]
        return TaskConfig(
            id=f"{self.id}__{block}__{difficulty}",
            difficulty=difficulty,
            goal=f"Place {count} {pretty(block)} blocks",
            setup=SetupSpec(world="flat", commands=cmds),
            timeout_seconds=120,
            success=SuccessSpec(rules=[Rule(kind="blocks_placed", block=block, min_count=count)]),
            reset_radius=24,
            reset_ceiling=32,
            metadata={"style": self.id, "category": self.category},
        )


# --- Registry: concrete styles (mostly data). Add a style by adding a spec here. ---

_PICK = "stone_pickaxe"
_PICK_IRON = "iron_pickaxe"
_CT = ("crafting_table", 1)
_FURNACE_FUEL = [("furnace", 1), ("coal", 8)]

STYLE_LIST = [
    # --- Mining / digging: success = blocks broken (minecraft.mined) ---
    MineStyle(id="mine_ore", count=(3, 6),
              blocks=["iron_ore", "coal_ore", "copper_ore", "gold_ore"],
              tool={"iron_ore": _PICK, "coal_ore": _PICK, "copper_ore": _PICK, "gold_ore": _PICK_IRON}),
    MineStyle(id="mine_stone", tool=_PICK, count=(3, 6),
              blocks=["stone", "cobblestone", "granite", "andesite", "diorite"]),
    MineStyle(id="mine_deepslate", tool=_PICK_IRON, count=(3, 6),
              blocks=["deepslate", "cobbled_deepslate", "polished_deepslate", "deepslate_bricks"]),
    MineStyle(id="mine_wood", tool="stone_axe", count=(3, 6),
              blocks=["oak_log", "birch_log", "spruce_log", "acacia_log", "jungle_log", "dark_oak_log"]),
    MineStyle(id="dig_dirt", tool="stone_shovel", count=(4, 7),
              blocks=["dirt", "coarse_dirt", "grass_block", "podzol"]),
    MineStyle(id="mine_sandstone", tool=_PICK, count=(3, 6),
              blocks=["sandstone", "smooth_sandstone", "cut_sandstone", "red_sandstone"]),
    MineStyle(id="mine_terracotta", tool=_PICK, count=(3, 6),
              blocks=["terracotta", "white_terracotta", "orange_terracotta", "light_blue_terracotta"]),
    MineStyle(id="mine_concrete", tool=_PICK, count=(3, 6),
              blocks=["white_concrete", "red_concrete", "lime_concrete", "blue_concrete"]),
    MineStyle(id="mine_wool", tool="shears", count=(3, 6),
              blocks=["white_wool", "red_wool", "lime_wool", "blue_wool", "yellow_wool"]),

    # --- Combat / hunting: success = entities killed (minecraft.killed) ---
    CombatStyle(id="hunt_hostiles", mobs=["zombie", "skeleton", "spider", "husk"]),
    CombatStyle(id="hunt_passives", mobs=["pig", "cow", "sheep", "chicken"]),
    CombatStyle(id="hunt_undead", mobs=["zombie", "husk", "drowned", "zombie_villager"]),
    CombatStyle(id="hunt_skeletons", mobs=["skeleton", "stray"]),
    CombatStyle(id="hunt_arthropods", mobs=["spider", "cave_spider", "silverfish"]),
    CombatStyle(id="hunt_illagers", mobs=["pillager", "vindicator"]),
    CombatStyle(id="hunt_farm_animals", mobs=["rabbit", "goat", "horse", "donkey"]),

    # --- Crafting / smelting: success = output item in inventory ---
    CraftStyle(id="craft_basics", recipes=[
        {"output": "crafting_table", "give": [("oak_planks", 4)]},
        {"output": "stick", "give": [("oak_planks", 2)], "output_count": 4},
        {"output": "chest", "give": [("oak_planks", 8), _CT]},
        {"output": "furnace", "give": [("cobblestone", 8), _CT]},
        {"output": "torch", "give": [("coal", 4), ("stick", 4)], "output_count": 4},
    ]),
    CraftStyle(id="craft_wood_tools", recipes=[
        {"output": o, "give": [("oak_planks", 8), ("stick", 4), _CT]}
        for o in ["wooden_pickaxe", "wooden_axe", "wooden_shovel", "wooden_hoe", "wooden_sword"]
    ]),
    CraftStyle(id="craft_stone_tools", recipes=[
        {"output": o, "give": [("cobblestone", 8), ("stick", 4), _CT]}
        for o in ["stone_pickaxe", "stone_axe", "stone_shovel", "stone_sword", "stone_hoe"]
    ]),
    CraftStyle(id="craft_iron_tools", recipes=[
        {"output": o, "give": [("iron_ingot", 8), ("stick", 4), _CT]}
        for o in ["iron_pickaxe", "iron_axe", "iron_shovel", "iron_sword"]
    ]),
    CraftStyle(id="craft_iron_armor", recipes=[
        {"output": o, "give": [("iron_ingot", 8), _CT]}
        for o in ["iron_helmet", "iron_chestplate", "iron_leggings", "iron_boots"]
    ]),
    CraftStyle(id="craft_leather_armor", recipes=[
        {"output": o, "give": [("leather", 8), _CT]}
        for o in ["leather_helmet", "leather_chestplate", "leather_leggings", "leather_boots"]
    ]),
    CraftStyle(id="craft_wood_building", recipes=[
        {"output": o, "give": [("oak_planks", 12), ("stick", 4), _CT]}
        for o in ["oak_stairs", "oak_slab", "oak_fence", "oak_fence_gate", "oak_door", "oak_trapdoor"]
    ]),
    CraftStyle(id="craft_food", recipes=[
        {"output": "bread", "give": [("wheat", 6), _CT]},
        {"output": "cookie", "give": [("wheat", 4), ("cocoa_beans", 2), _CT], "output_count": 8},
        {"output": "pumpkin_pie", "give": [("pumpkin", 2), ("sugar", 2), ("egg", 2), _CT]},
        {"output": "mushroom_stew", "give": [("bowl", 1), ("red_mushroom", 2), ("brown_mushroom", 2)]},
    ]),
    CraftStyle(id="craft_decoration", recipes=[
        {"output": "item_frame", "give": [("stick", 8), ("leather", 2), _CT]},
        {"output": "painting", "give": [("stick", 8), ("white_wool", 2), _CT]},
        {"output": "flower_pot", "give": [("brick", 4), _CT]},
        {"output": "armor_stand", "give": [("stick", 6), ("smooth_stone_slab", 1), _CT]},
    ]),
    CraftStyle(id="craft_transport", recipes=[
        {"output": "oak_boat", "give": [("oak_planks", 8), _CT]},
        {"output": "minecart", "give": [("iron_ingot", 6), _CT]},
        {"output": "rail", "give": [("iron_ingot", 8), ("stick", 2), _CT], "output_count": 8},
    ]),
    CraftStyle(id="craft_redstone", recipes=[
        {"output": "redstone_torch", "give": [("redstone", 4), ("stick", 4), _CT]},
        {"output": "lever", "give": [("cobblestone", 4), ("stick", 4), _CT]},
        {"output": "piston", "give": [("oak_planks", 4), ("cobblestone", 8),
                                       ("iron_ingot", 2), ("redstone", 2), _CT]},
    ]),
    CraftStyle(id="craft_misc", recipes=[
        {"output": "ladder", "give": [("stick", 14), _CT], "output_count": 3},
        {"output": "oak_sign", "give": [("oak_planks", 12), ("stick", 2), _CT]},
        {"output": "bowl", "give": [("oak_planks", 6), _CT], "output_count": 4},
        {"output": "bucket", "give": [("iron_ingot", 6), _CT]},
    ]),
    CraftStyle(id="smelt_ingots", category="tool_use", recipes=[
        {"output": "iron_ingot", "give": [("raw_iron", 4), *_FURNACE_FUEL]},
        {"output": "copper_ingot", "give": [("raw_copper", 4), *_FURNACE_FUEL]},
        {"output": "gold_ingot", "give": [("raw_gold", 4), *_FURNACE_FUEL]},
    ]),
    CraftStyle(id="smelt_food", category="tool_use", recipes=[
        {"output": "cooked_beef", "give": [("beef", 4), *_FURNACE_FUEL]},
        {"output": "cooked_porkchop", "give": [("porkchop", 4), *_FURNACE_FUEL]},
        {"output": "cooked_chicken", "give": [("chicken", 4), *_FURNACE_FUEL]},
        {"output": "baked_potato", "give": [("potato", 4), *_FURNACE_FUEL]},
    ]),
    CraftStyle(id="smelt_misc", category="tool_use", recipes=[
        {"output": "glass", "give": [("sand", 4), *_FURNACE_FUEL]},
        {"output": "charcoal", "give": [("oak_log", 4), *_FURNACE_FUEL]},
        {"output": "brick", "give": [("clay_ball", 4), *_FURNACE_FUEL]},
        {"output": "stone", "give": [("cobblestone", 4), *_FURNACE_FUEL]},
    ]),

    # --- Building / placement: success = blocks placed (minecraft.used) ---
    PlaceStyle(id="place_blocks", count=(3, 6),
               blocks=["oak_planks", "cobblestone", "stone_bricks", "oak_log"]),
    PlaceStyle(id="place_fences", count=(3, 6),
               blocks=["oak_fence", "spruce_fence", "nether_brick_fence"]),
    PlaceStyle(id="place_walls", count=(3, 6),
               blocks=["cobblestone_wall", "stone_brick_wall", "mossy_cobblestone_wall"]),
    PlaceStyle(id="place_slabs", count=(3, 6),
               blocks=["oak_slab", "stone_slab", "cobblestone_slab", "smooth_stone_slab"]),
    PlaceStyle(id="place_stairs", count=(3, 6),
               blocks=["oak_stairs", "stone_stairs", "cobblestone_stairs"]),
    PlaceStyle(id="place_carpet", count=(4, 8), category="decoration",
               blocks=["white_carpet", "red_carpet", "blue_carpet", "lime_carpet"]),
    PlaceStyle(id="place_glass", count=(3, 6),
               blocks=["glass", "white_stained_glass", "light_blue_stained_glass", "glass_pane"]),
    PlaceStyle(id="place_wool", count=(3, 6),
               blocks=["white_wool", "red_wool", "blue_wool", "lime_wool"]),
    PlaceStyle(id="place_concrete", count=(3, 6),
               blocks=["white_concrete", "red_concrete", "lime_concrete", "blue_concrete"]),
    PlaceStyle(id="plant_saplings", count=(3, 6), category="decoration",
               blocks=["oak_sapling", "birch_sapling", "spruce_sapling"]),
]

STYLES = {s.id: s for s in STYLE_LIST}
