import json
from random import random
from time import time
from math import floor, ceil
from functools import singledispatch as default
from os import path

LAST_SNAPSHOT: int = int(time())
SNAPSHOT_DELAY: int = 300


class GameCharacter():
    def __init__(
        self,
        name: str,
        level: int = 1,
        strength: int = 4,
        agility: int = 4,
        vitality: int = 4,
        stat_alloc: int = 10,
        perk_alloc: int = 0,
        ability_alloc: int = 0,
        wins: list[dict[str, list]] = [],
        losses: list[dict[str, list]] = [],
        __perks: dict[str, int] = {},
        __abilities: dict[str, int] = {},
        badge: str = ''
    ):
        self.display_name: str = name
        self.name: str = name.lower()
        self.level: int = level
        self.wins: list[dict[str, list]] = wins
        self.losses: list[dict[str, list]] = losses
        self.in_game: bool = False
        self.stat_alloc: int = stat_alloc
        self.perk_alloc: int = perk_alloc
        self.ability_alloc: int = ability_alloc

        self.strength: int = strength
        # Every 10 levels of str gives +3 to modifier.
        # Every 3 levels gives +2 to die.

        self.agility: int = agility
        # Every 15 levels of agi gets an extra roll.
        # Every 5  levels of agi gives +20% chance to crit (add +1 dice)
        # Every 10 levels of agi increases chance to evade an attack by 6%
        # Base crit is 30%.

        self.vitality: int = vitality
        # Every 10 levels of vit gets +2 flat DR, that reduces EVERY attack
        # Every 5 levels of vit gets a per round +3 damage buffer/round.
        # Every 5 levels of vit gets +15 max hitpoints and +5 max stamina.

        self.status_effects = dict[str, CharacterStatus] = {}

        self.hp: float = 1.0
        self.stamina: float = 1.0

        self.modifiers = Modifier.template.copy()

        self.ability_modifiers = Modifier.template.copy()
        self.ability_modifiers.update(Modifier.template_ability)

        self.deceased: bool = False
        self.incapacitated: bool = False

        self.__perks: dict[str, int] = __perks
        self.perks: dict[str, CharacterPerk] = {}
        self.build_perkbilities(CharacterPerk, self.perks, self.__perks)
        self.__abilities: dict[str, int] = __abilities
        self.abilities: dict[str, CharacterAbility] = {}
        self.build_perkbilities(
            CharacterAbility,
            self.abilities,
            self.__abilities
        )
        delattr(self, '__abilities')
        delattr(self, '__perks')
        self.badge: str = badge
        self.has_badges: str = ''

    def build_perkbilities(self, cls, new_li: dict, li: dict[str, int]):
        for name in li:
            level: int = li[name]
            perkbility: cls = cls(self, name, level)
            new_li[name] = perkbility

    def remove_perk(self, perk: str) -> None:
        self.perks.pop(perk)

    def add_perk(self, perk: str, level: int) -> None:
        perk_inst = CharacterPerk(
            self,
            perk,
            level
        )
        self.perks[perk] = perk_inst

    def update_cooldowns(self) -> None:
        for name in self.abilities:
            ability: CharacterAbility = self.abilities[name]
            if ability.cooldown:
                ability.cooldown -= 1

    def update_statuses(self) -> None:
        for name in self.status_effects:
            status: CharacterStatus = self.status_effects[name]
            if status.duration == 1:
                self.status_effects.pop(name)


class CharacterStatus:
    def __init__(
        self,
        character: GameCharacter,
        name: str,
        description: str,
        duration: int,
        level: int = 1,
        incapacitated: bool = False,
        deceased: bool = False,
        indefinite: bool = False,
        **kwargs
    ):
        self.name: str = name
        self.description: str = description
        self.level: int = level
        self.duration: int = duration
        self.deceased: bool = deceased
        self.incapacitated: bool = incapacitated
        self.indefinite: bool = indefinite
        self.character: GameCharacter = character
        self.modified: dict[str, int | float]
        for arg, value in kwargs.items():
            self.modified[arg] = value
            self.character.modifiers[arg] += value

    def remove(self) -> None:
        for modifier, value in self.modified.items():
            self.character.modifiers[modifier] -= value


class Modifier:
    template: dict[str, int | float] = {
            'add_hp': 0,
            'mod_hp': 1.0,
            'add_max_hp': 0,
            'mod_max_hp': 1.0,
            'add_stamina': 0,
            'mod_stamina': 1.0,
            'add_stamina_max': 0,
            'mod_stamina_max': 1.0,
            'add_strength': 0,
            'mod_strength': 1.0,
            'add_agility': 0,
            'mod_agility': 1.0,
            'add_vitality': 0,
            'mod_vitality': 1.0,
            'mod_damage': 1.0,
            'add_heal': 0,
            'mod_heal': 1.0,
            'add_damage_reduction': 0,
            'add_damage_buffer': 0,
            'mod_damage_buffer': 1.0,
            'add_damage': 0,
            'mod_damage': 1.0
    }
    template_ability: dict[str, int | float] = {
        'attacking': 0,
        'healing': 0,
        'resting': 0,
        'defending': 0
    }


class Passive:
    """
    Passive-type abilities.
    """

    """
    Acheivement Perk, unlocked by reaching milestones.
    Unlocked every 10 levels, to a maximum of level 60.
    Veteran adds +1 str, +0.33 vitality, +0.5 agilty per rank. [6 ranks max]
    Maximum adds +6 str, +2 vit, +3 agi
    """
    @staticmethod
    def veteran(level: int, ref: dict) -> None:
        ref['add_strength'] = level
        ref['add_agility'] = floor(0.5 * level)
        ref['add_vitality'] = floor(1 / 3 * level)

    """
    Acheivement Perk, unlocked by reaching milestones.
    Unlocked every time a single predator manages to win against a group of 5
    Veteran adds +0.4 str, +1 vitality, +0.4 agility per rank. [10 ranks max]
    Maximum adds: +4 str, +10 vit, +4 agi.
    """
    @staticmethod
    def raid_boss(level: int, ref: dict) -> None:
        ref['add_strength'] = floor(0.4 * level)
        ref['add_agility'] = floor(0.4 * level)
        ref['add_vitality'] = level

    """
    Acheivement Perk, unlocked by cursing yourself with being a programmer.
    """
    @staticmethod
    def developer(level: int, ref: dict) -> None:
        ref['add_strength'] = -2
        ref['add_vitality'] = 2

    """
    Acheivement Perk, unlocked by winning numerous times as prey.
    Levels every 10 wins to a total of 6 levels.
    Extra DR at level 1: 2 and +1 DR for every perk level after.
    +1 vit/level
    """
    @staticmethod
    def hard_to_digest(level: int, ref: dict) -> None:
        ref['add_vitality'] = level
        ref['add_damage_reduction'] = 1 + level

    """
    Acheivement Perk, unlocked by being prey party's MVP healer 5 times.
    Each level unlocks after 5 MVPs, to a total of level 10.
    Each level after level 1 gains +8% healing effectiveness.
    Multiplicative
    """
    @staticmethod
    def best_friend(level: int, ref: dict) -> None:
        ref['mod_heal'] = level * 0.08

    """
    Purchased Perk, requires level 6.
    For each level, decrease vit by 10%.
                    inc agi/str by 10%
    Multiplicative
    """
    @staticmethod
    def rage_fueled(level: int, ref: int) -> None:
        ref['mod_strength'] = level * 0.1
        ref['mod_agility'] = level * 0.1
        ref['mod_vitality'] = level * -0.1

    """
    Purchased Perk, requires level 6.
    For each level, increase vit/agi by 10%
                    decrease str by 10%
    Multiplicative
    """
    @staticmethod
    def stalwart(level: int, ref: dict) -> None:
        ref['mod_strength'] = level * -0.1
        ref['mod_agility'] = level * 0.1
        ref['mod_vitality'] = level * 0.1


class CharacterPerk:
    # Perk database, stores data including method pointer.
    perkiary: dict[str, dict] = {
        'developer': {
            'level': 1,
            'max_level': 1,
            'setup': Passive.developer,
            'badge': u'\U0001f6e0'
        },
        'raid boss': {
            'level': 1,
            'max_level': 10,
            'setup': Passive.raid_boss,
            'badge': u'\U0001f480'
        },
        'veteran': {
            'level': 1,
            'max_level': 6,
            'setup': Passive.veteran,
            'badge': u'\u2694'
        },
        'hard to digest': {
            'level': 1,
            'max_level': 6,
            'setup': Passive.hard_to_digest,
            'badge': u'\u26a0'
        },
        'best friend': {
            'level': 1,
            'max_level': 10,
            'setup': Passive.best_friend,
            'badge': u'\u26e8'
        },
        'rage-fueled': {
            'level': 1,
            'max_level': 4,
            'setup': Passive.rage_fueled,
            'costs': 2,
            'requires': 6
        },
        'stalwart': {
            'level': 1,
            'max_level': 4,
            'setup': Passive.stalwart,
            'costs': 2,
            'requires': 6
        }
    }

    def __init__(
        self,
        name: str,
        level: int,
        character: GameCharacter
    ) -> None:
        self.name: str = name
        self.level: int = level
        self.character: GameCharacter = character
        self.modified: dict[str, int | float] = {}
        for modifier, value in self.modified.items():
            self.character.modifiers[modifier] += value
        self.badge: str = CharacterAbility.abiliary[name].get('badge', '')
        character.has_badges += self.badge

    def remove(self) -> None:
        for modifier, value in self.modified.items():
            self.character.modifiers[modifier] -= value


class Ability:
    """
    Attack
    Max: 10
    Every level reduces stamina cost of attacking by 5%.
    Starter
    """
    @staticmethod
    def attack(level: int, ref: dict[str, int | float]) -> None:
        ref['attacking'] = 1
        ref['add_stamina'] = ceil((1 - (0.05 * (level - 1))) * 30)

    """
    Heal ability
    base heal: 5
    base roll: 2d4
    Every level adds 1d4 to heal.
    Max level: 10
    Starter
    """
    @staticmethod
    def heal(level: int, ref: dict[str, int | float]) -> None:
        ref['healing'] = 1
        ref['add_heal'] = floor(level * 4 * random()) + level + 2
        ref['add_stamina'] -= 25

    """
    Rest ability
    Regenerate stamina for ability use 2x
    Max level: 10
    Each level increases efficiency by 5%.
    Starter
    """
    def rest(level: int, ref: dict[str, int | float]) -> None:
        ref['resting'] = 1
        ref['add_stamina'] = ceil(40 * (1 + ((level - 1) * 0.05)))

    """
    Defend ability
    Regenerate stamina + block incoming damage.
    Max level: 10
    Each level increases stamina regeneration by 5%
    Each second level increases damage reduction by 2
    Each second level increases damage buffer by 2
    Starter
    """
    def defend(level: int, ref: dict[str, int | float]) -> None:
        ref['defending'] = 1
        ref['add_stamina'] = ceil(20 * (1 + ((level - 1) * 0.05)))
        ref['add_damage_reduction'] = floor((level - 1) * 2)
        ref['add_damage_buffer'] = floor((level - 1) * 2)


class CharacterAbility:
    # Perk database, stores data including method pointer.
    abiliary: dict[str, dict] = {
        'attack': {
            'level': 1,
            'max_level': 1,
            'setup': Ability.attack,
            'cost': 2,
            'targetted': False
        },
        'heal': {
            'level': 1,
            'max_level': 10,
            'setup': Ability.heal,
            'cost': 2,
            'targetted': True
        },
        'rest': {
            'level': 1,
            'max_level': 5,
            'setup': Ability.rest,
            'cost': 2,
            'targetted': False
        },
        'defend': {
            'level': 1,
            'max_level': 5,
            'setup': Ability.defend,
            'cost': 2,
            'targetted': False
        }
    }

    def __init__(
        self,
        name: str,
        level: int,
        character: GameCharacter
    ) -> None:
        self.name: str = name
        self.level: int = level
        self.character: GameCharacter = character
        self.modified: dict[str, int | float] = {}

    def remove(self) -> None:
        for modifier, value in self.modified.items():
            self.character.ability_modifiers[modifier] -= value

    def use_ability(self) -> None:
        self.remove()
        self.modified = {}
        CharacterAbility.abiliary[self.name]['setup'](
            self.level, self.modified
        )
        for modifier, value in self.modified.items():
            self.character.ability_modifiers[modifier] += value


# Increases stat allocation points per level.
# A level is gained for defeating another player.
# A predator loses 2 levels per loss to a floor of level 1,
# However, if a predator is battling more than 1 person, they only
# lose 1 level if they lose to both prey, for a maximum of no penalty
# if the predator managed to finish off a prey,
# Defeating multiple prey gives the standard +1 level per prey.
# Maximum allocated stat points will be 60.
# Every 2 levels = 1 perk point.
# Every 4 levels = 1 ability point.
class HungryCharacter(GameCharacter):
    def __init__(
        self,
        name: str,
        level: int = 1,
        strength: int = 4,
        agility: int = 4,
        vitality: int = 4,
        stat_alloc: int = 0,
        perk_alloc: int = 0,
        ability_alloc: int = 0,
        wins: list[dict[str, list]] = [],
        losses: list[dict[str, list]] = [],
        __perks: dict[str, int] = {},
        __abilities: dict[str, int] = {},
        badge: str = ''
    ):
        super().__init__(
            self,
            name,
            level,
            strength,
            agility,
            vitality,
            stat_alloc,
            perk_alloc,
            ability_alloc,
            wins,
            losses,
            __perks,
            __abilities,
            badge
        )
        self.status_effects['Pred'] = CharacterStatus(
            self,
            'Pred',
            'You are pred and are at optimal strength!',
            99,
            indefinite=True
        )


# Increases stat allocation points per level.
# A level is gained for defeating another player.
# A prey loses 1 level per loss to a floor of level 1.
# Prey that team up to take on a single predator at a time
# will lose 2 levels if they fall, if they both fall then
# both will lose 3 levels each.
# Maximum allocated stat points will be 60.
# Every 2 levels = 1 perk point.
# Every 4 levels = 1 ability point.
class ThirstyCharacter(GameCharacter):
    def __init__(
        self,
        name: str,
        level: int = 1,
        strength: int = 4,
        agility: int = 4,
        vitality: int = 4,
        stat_alloc: int = 0,
        perk_alloc: int = 0,
        ability_alloc: int = 0,
        wins: list[dict[str, list]] = [],
        losses: list[dict[str, list]] = [],
        __perks: dict[str, int] = {},
        __abilities: dict[str, int] = {},
        badge: str = ''
    ):
        super().__init__(
            self,
            name,
            level,
            strength,
            agility,
            vitality,
            stat_alloc,
            perk_alloc,
            ability_alloc,
            wins,
            losses,
            __perks,
            __abilities,
            badge
        )
        self.status_effects['Prey'] = CharacterStatus(
            self,
            'Pred',
            'You are pred and are at optimal strength!',
            99,
            indefinite=True
        )


class Game:
    characters: dict[str, GameCharacter] = {}

    def __init__(
        self,
        pred: str,
        prey: list[str],
        channel: str,
        challenger: HungryCharacter | ThirstyCharacter
    ):
        pred_character: HungryCharacter = Game.get_character(pred)
        prey_characters: HungryCharacter = Game.get_character(prey)
        self.pred: HungryCharacter = pred_character
        self.prey: list[ThirstyCharacter] = prey_characters
        self.channel: str = channel
        self.challenger: HungryCharacter | ThirstyCharacter = challenger
        self.rounds: list[Round] = []
        self.round: Round = Round(self.pred, self.prey)

        if path.exists('data/hungry_db.json'):
            f = open('data/hungry_db.json', 'r', encoding='utf-8')
            cdata = json.load(f)
            f.close()

            for name in cdata:
                c = cdata[name]
                Game.characters[name.lower()] = GameCharacter(
                    name=c['n'],
                    level=c['lv'],
                    strength=c['s'],
                    agility=c['a'],
                    vitality=c['v'],
                    stat_alloc=c['st'],
                    perk_alloc=c['pp'],
                    ability_alloc=c['ap'],
                    wins=c['w'],
                    losses=c['l'],
                    __perks=c['p'],
                    __abilities=c['a'],
                    badge=c['b']
                )

    @staticmethod
    @default
    def game_characters(_T):
        raise NotImplementedError

    @staticmethod
    @game_characters.register
    def game_characters() -> dict[str, GameCharacter]:
        return Game.characters

    @staticmethod
    @game_characters.register
    def game_characters(_T: GameCharacter) -> list[GameCharacter]:
        return list(Game.characters.values())

    @staticmethod
    @game_characters.register
    def game_characters(_T: str) -> list[str]:
        return list(Game.characters.keys())

    @staticmethod
    def add_character(name: str, char: GameCharacter) -> None:
        Game.characters[name] = char

    @staticmethod
    @default
    def get_character(arg):
        raise NotImplementedError

    @staticmethod
    @get_character.register
    def get_character(id: str) -> GameCharacter:
        pass

    @staticmethod
    @get_character.register
    def get_character(ids: list[str]) -> list[ThirstyCharacter]:
        pass


class Round:
    def __init__(
        self,
        pred: HungryCharacter,
        prey: list[ThirstyCharacter]
    ):
        self.pred: HungryCharacter = pred
        self.prey: list[ThirstyCharacter] = prey
        self.pred.update_cooldowns()
        self.pred.update_statuses()

        for prey in self.prey:
            prey.update_cooldowns()
            prey.update_statuses()

    def calculate_round(self) -> None:
        # Calculate incoming damage on pred
        for action in self.prey_act:
            continue
        # Calculate incoming damage on prey

    def end_turn(self) -> None:
        # Set the chosen action in stone, cycle to next or calculate round.
        pass


class UI:
    @staticmethod
    def get_modified_stats(char: GameCharacter) -> dict[complex]:
        pass

    @staticmethod
    def new() -> None:
        pass
