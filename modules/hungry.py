import json

from os import path
from random import random
from time import time
from math import floor, ceil
from modules.utils import log
from modules.channel import Channel


DOC: dict[str, dict[str, complex]] = {}


def load_doc() -> None:
    f = open('src/templates.json', 'r', encoding='utf-8')
    obj: dict[str, dict[str, complex]] = json.load(f)
    for name in obj:
        DOC[name] = obj[name]


load_doc()


class GameCharacter():
    def __init__(
        self,
        name: str,
        level: int = 1,
        strength: int = 4,
        agility: int = 4,
        vitality: int = 4,
        stat_alloc: int = 11,
        perk_alloc: int = 0,
        ability_alloc: int = 0,
        wins: list[dict[str, list]] = [],
        losses: list[dict[str, list]] = [],
        perks: dict[str, int] = {},
        abilities: dict[str, int] = {
            'attack': 1,
            'heal': 1,
            'rest': 1,
            'defend': 1
        },
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
        self.agility: int = agility
        self.vitality: int = vitality
        self.status_effects: dict[str, CharacterStatus] = {}
        self.hp: float = 1.0
        self.stamina: float = 1.0
        self.modifiers = Modifier.template.copy()
        self.ability_modifiers = Modifier.template.copy()
        self.ability_modifiers.update(Modifier.template_ability)
        self.deceased: bool = False
        self.incapacitated: bool = False
        self.badge: str = badge
        self.has_badges: str = ''
        self.desires_refund: int = 0
        self.perks: dict[str, CharacterPerk] = {}
        self.build_perkbilities(CharacterPerk, self.perks, perks)
        self.abilities: dict[str, CharacterAbility] = {}
        self.build_perkbilities(
            CharacterAbility,
            self.abilities,
            abilities
        )
        Game.add_character(self.name, self)

    def build_perkbilities(self, cls, new_li: dict, li: dict[str, int]):
        for name in li:
            level: int = li[name]
            perkbility: cls = cls(name=name, level=level, character=self)
            new_li[name] = perkbility

    def remove_perk(self, perk: str) -> None:
        self.perks.pop(perk)

    def add_perk(self, perk: str, level: int) -> None:
        perk_inst = CharacterPerk(
            name=perk,
            level=level,
            character=self
        )
        self.perks[perk] = perk_inst

    def remove_ability(self, ability: str) -> None:
        self.abilities.pop(ability)

    def add_ability(self, ability: str, level: int) -> None:
        ability_inst = CharacterAbility(
            name=ability,
            level=level,
            character=self
        )
        self.abilities[ability] = ability_inst

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
        self.modified: dict[str, int | float] = {}
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
            'add_evasion': 0,
            'mod_evasion': 1.0,
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
    @staticmethod
    def veteran(level: int, ref: dict) -> None:
        ref['add_strength'] = level
        ref['add_agility'] = floor(0.5 * level)
        ref['add_vitality'] = floor(1 / 3 * level)

    @staticmethod
    def raid_boss(level: int, ref: dict) -> None:
        ref['add_strength'] = floor(0.4 * level)
        ref['add_agility'] = floor(0.4 * level)
        ref['add_vitality'] = level

    @staticmethod
    def developer(level: int, ref: dict) -> None:
        ref['mod_strength'] = 0.1
        ref['mod_strength'] = 0.1
        ref['mod_vitality'] = 0.2

    @staticmethod
    def tester(level: int, ref: dict) -> None:
        ref['add_strength'] = 2
        ref['add_agility'] = 1
        ref['add_vitality'] = 3

    @staticmethod
    def hard_to_digest(level: int, ref: dict) -> None:
        ref['add_vitality'] = level
        ref['add_damage_reduction'] = floor(level / 2)

    @staticmethod
    def best_friend(level: int, ref: dict) -> None:
        ref['mod_heal'] = level * 0.08

    @staticmethod
    def rage_fueled(level: int, ref: int) -> None:
        ref['mod_strength'] = level * 0.1
        ref['mod_agility'] = level * -0.1
        ref['mod_vitality'] = level * -0.1

    @staticmethod
    def stalwart(level: int, ref: dict) -> None:
        ref['mod_strength'] = level * -0.1
        ref['mod_agility'] = level * -0.1
        ref['mod_vitality'] = level * 0.1

    @staticmethod
    def speedy(level: int, ref: dict) -> None:
        ref['mod_strength'] = level * -0.1
        ref['mod_agility'] = level * 0.1
        ref['mod_vitality'] = level * -0.1


class CharacterPerk:
    # Perk database, stores data including method pointer.
    perkiary: dict[str, dict] = DOC['passives']

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
        self.fn = getattr(Passive, CharacterPerk.perkiary[name]['setup'])
        self.fn(self.level, self.modified)
        for modifier, value in self.modified.items():
            self.character.modifiers[modifier] += value
        self.badge: str = CharacterPerk.perkiary[name].get('badge', '')
        if not character.badge:
            character.badge = self.badge
        character.has_badges += self.badge

    def remove(self) -> None:
        for modifier, value in self.modified.items():
            self.character.modifiers[modifier] -= value


class Ability:
    @staticmethod
    def attack(level: int, ref: dict[str, int | float]) -> None:
        ref['attacking'] = 1
        ref['add_stamina'] = ceil((1 - (0.05 * (level - 1))) * 30)

    @staticmethod
    def heal(level: int, ref: dict[str, int | float]) -> None:
        ref['healing'] = 1
        ref['add_heal'] = ceil((level + 1) * 4 * random()) + 5
        ref['add_stamina'] -= 25

    @staticmethod
    def rest(level: int, ref: dict[str, int | float]) -> None:
        ref['resting'] = 1
        ref['add_stamina'] = ceil(40 * (1 + ((level - 1) * 0.075)))

    @staticmethod
    def defend(level: int, ref: dict[str, int | float]) -> None:
        ref['defending'] = 1
        ref['add_stamina'] = ceil(20 * (1 + ((level - 1) * 0.05)))
        ref['add_damage_reduction'] = level * 1 + 3
        ref['add_damage_buffer'] = level * 2 + 4


class CharacterAbility:
    abiliary: dict[str, dict] = DOC['abilities']

    def __init__(
        self,
        name: str,
        level: int,
        character: GameCharacter,
        cooldown: int = 0
    ) -> None:
        self.name: str = name
        self.level: int = level
        self.character: GameCharacter = character
        self.cooldown: int = cooldown
        self.fn = getattr(Ability, CharacterAbility.abiliary[name]['setup'])
        self.modified: dict[str, int | float] = {}

    def remove(self) -> None:
        for modifier, value in self.modified.items():
            self.character.ability_modifiers[modifier] -= value

    def use_ability(self) -> None:
        self.remove()
        self.modified = {}
        self.fn(
            self.level, self.modified
        )
        for modifier, value in self.modified.items():
            self.character.ability_modifiers[modifier] += value


class HungryCharacter(GameCharacter):
    def __init__(
        self,
        name: str,
        level: int = 1,
        strength: int = 4,
        agility: int = 4,
        vitality: int = 4,
        stat_alloc: int = 11,
        perk_alloc: int = 0,
        ability_alloc: int = 0,
        wins: list[dict[str, list]] = [],
        losses: list[dict[str, list]] = [],
        perks: dict[str, int] = {},
        abilities: dict[str, int] = {},
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
            perks,
            abilities,
            badge
        )
        self.status_effects['Pred'] = CharacterStatus(
            self,
            'Pred',
            'You are pred and are at optimal strength!',
            99,
            indefinite=True
        )
        self.current_damage_buffer: int = 0


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
        perks: dict[str, int] = {},
        abilities: dict[str, int] = {},
        badge: str = ''
    ):
        super().__init__(
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
            perks,
            abilities,
            badge
        )
        self.current_damage_buffer: int = 0


class Setup:
    __next_check: int = int(time()) + 60

    def __init__(
        self,
        pred: GameCharacter,
        prey: list[GameCharacter],
        channel: Channel,
        output
    ):
        self.pred: GameCharacter = pred
        self.prey: list[GameCharacter] = prey
        self.need_consent = list[GameCharacter] = prey
        self.channel: Channel = channel
        self.output = output
        channel.setup = True
        self.timeout: int = int(time()) + 300
        SETUPS[self] = Channel

    def add_consent(self, character: GameCharacter) -> None:
        self.need_consent.pop(self.need_consent.index(character))
        if not len(self.need_consent):
            self.channel.hungry = Game(
                self.pred,
                self.prey,
                self.channel,
                self.output
            )
            self.channel.setup = False

    def no_consent(self) -> None:
        SETUPS.pop(self)

    @staticmethod
    def get_instance_by_prey(character: GameCharacter):
        for setup in SETUPS:
            if character.name in setup.prey:
                return setup
        return None

    @staticmethod
    async def check_timeout(t: int) -> None:
        if not len(SETUPS):
            return
        if Setup.__next_check > t:
            return
        Setup.__next_check += t + 60

        for setup in SETUPS:
            if setup.timeout < t:
                setup.channel.setup = False
                SETUPS.pop(setup)
                await setup.output.send(
                    '[b]Hungry Game[/b]: Setup phase timed out, aborting game.'
                )


SETUPS: dict[Setup, Channel] = {}


class Game:
    snapshot_last: int = 0
    SNAPSHOT_DELAY: int = 600
    characters: dict[str, GameCharacter] = {}
    ACITIVITY_DELAY: int = 10800

    def __init__(
        self,
        pred: GameCharacter,
        prey: list[GameCharacter],
        channel: Channel,
        output
    ):
        self.activity: int = int(time())
        self.pred: HungryCharacter = HungryCharacter(
            name=pred.name,
            level=pred.level,
            strength=pred.strength,
            agility=pred.agility,
            vitality=pred.vitality,
            stat_alloc=pred.stat_alloc,
            perk_alloc=pred.perk_alloc,
            ability_alloc=pred.ability_alloc,
            wins=pred.wins,
            losses=pred.losses,
            perks=pred.perks,
            abilities=pred.abilities,
            badge=pred.badge
        )
        self.prey: list[ThirstyCharacter] = []
        for p in prey:
            self.prey.append(
                ThirstyCharacter(
                    name=p.name,
                    level=p.level,
                    strength=p.strength,
                    agility=p.agility,
                    vitality=p.vitality,
                    stat_alloc=p.stat_alloc,
                    perk_alloc=p.perk_alloc,
                    ability_alloc=p.ability_alloc,
                    losses=p.losses,
                    wins=p.wins,
                    perks=p.perks,
                    abilities=p.abilities,
                    badge=p.badge
                )
            )
        self.pred.current_damage_buffer = Game.modded_damage_buffer(self.pred)
        for p in self.prey:
            p.current_damage_buffer = Game.modded_damage_buffer(p)
        self.channel: Channel = channel
        channel.hungry = self
        self.output = output
        self.dead: list[ThirstyCharacter] = []
        # Setting last active time.
        GAMES[self] = int(time())
        self.initiative: list[GameCharacter] = []
        self.reset_initiative()
        self.turn: ThirstyCharacter | HungryCharacter = self.initiative[0]
        UI.draw_game(self)

    @staticmethod
    def get_modded_hp(character: GameCharacter) -> tuple[int, int]:
        vitality: int = Game.get_modded_vitality(character)
        add_hp_max: int = character.modifiers.get('add_hp_max', 0)
        mod_hp_max: float = character.modifiers.get('mod_hp_max', 1.0)
        max_hp: int = floor(
            (
                add_hp_max + 100 + floor(vitality / 5) * 15
            ) * mod_hp_max
        )
        return (
            floor(max_hp * character.hp),
            max_hp
        )

    @staticmethod
    def get_modded_stamina(character: GameCharacter) -> tuple[int, int]:
        vitality: int = Game.get_modded_vitality(character)
        max_stamina: int = floor(
            (
                character.modifiers.get('add_stamina_max', 0) + 100 +
                floor(vitality / 5) * 5
            ) * character.modifiers.get('mod_stamina_max', 1.0)
        )
        return (
            floor(max_stamina * character.stamina),
            max_stamina
        )

    @staticmethod
    def get_modded_strength(character: GameCharacter) -> int:
        return floor(
            (
                character.strength + character.modifiers.get('add_strength', 0)
            ) * character.modifiers.get('mod_strength', 1.0)
        )

    @staticmethod
    def get_modded_agility(character: GameCharacter) -> int:
        return floor(
            (
               character.agility + character.modifiers.get('add_agility', 0)
            ) * character.modifiers.get('mod_agility', 1.0)
        )

    @staticmethod
    def get_modded_vitality(character: GameCharacter) -> int:
        return floor(
            (
               character.vitality + character.modifiers.get('add_vitality', 0)
            ) * character.modifiers.get('mod_vitality', 1.0)
        )

    @staticmethod
    def get_modded_stats(character: GameCharacter) -> tuple[int, int, int]:
        return (
            Game.get_modded_strength(character),
            Game.get_modded_agility(character),
            Game.get_modded_vitality(character)
        )

    @staticmethod
    def get_crit(
        agility: int
    ) -> int:
        return (
            10 + floor(
                floor(agility / 5) * 12.5
            ) % 100
        )

    @staticmethod
    def get_die(
        agility: int
    ) -> int:
        return (
            1 + floor(
                (
                    30 + floor(agility / 5) * 12.5
                ) / 100
            ) + floor(agility / 15)
        )

    def get_faces(
        strength: int
    ) -> int:
        return 8 + floor(strength / 4) * 2

    @staticmethod
    def get_mod(
        strength: int
    ) -> int:
        return floor(strength / 10) * 3

    @staticmethod
    def __get_evasion(
        agility: int
    ) -> int:
        return floor(agility / 10) * 6

    @staticmethod
    def get_modded_evasion(
        character: GameCharacter,
        agility: int
    ) -> int:
        return (
            floor(
                character.modifiers.get('add_evasion', 0) + (
                    Game.__get_evasion(agility)
                ) * character.modifiers.get('mod_evasion', 1.0)
            )
        )

    @staticmethod
    def __get_damage_reduction(
        vitality: int
    ) -> int:
        return floor(vitality / 10) * 2

    @staticmethod
    def get_modded_damage_reduction(
        character: GameCharacter,
        vitality: int
    ) -> int:
        return (
            floor(
                character.modifiers.get('add_damage_reduction') + (
                    Game.__get_damage_reduction(vitality)
                ) * character.modifiers.get('mod_damage_reduction')
            )
        )

    def __get_damage_buffer(
        vitality: int
    ) -> int:
        return floor(vitality / 5) * 3

    @staticmethod
    def get_modded_damage_buffer(
        character: GameCharacter,
        vitality: int
    ) -> int:
        return (
            floor(
                character.modifiers.get('add_damage_buffer') + (
                    Game.__get_damage_buffer(vitality)
                ) * character.modifiers.get('mod_damage_buffer')
            )
        )

    @staticmethod
    def modded_damage_buffer(
        character: GameCharacter
    ) -> int:
        vitality: int = Game.get_modded_vitality(character)
        return (
            floor(
                character.modifiers.get('add_damage_buffer') + (
                    Game.__get_damage_buffer(vitality)
                ) * character.modifiers.get('mod_damage_buffer')
            )
        )

    # Damage stats template:
    # die, faces, mod, crit
    @staticmethod
    def get_damage_stats(
        strength: int,
        agility: int
    ) -> tuple[int, int, int, int]:
        return (
            Game.get_die(agility),
            Game.get_faces(strength),
            Game.get_mod(strength),
            Game.get_crit(agility)
        )

    def use_ability(
        self,
        char: GameCharacter,
        ability: CharacterAbility,
        target: list[GameCharacter] | GameCharacter | None = None
    ) -> None:
        event_parameters: dict[str, int] = {
            'type': None,
            'targets': [],
            'deltas': [],
            'pre_deltas': [],
            'rolls': [],
            'evaded': []
        }

        if ability.name == 'attack':
            event_parameters['type'] = 'attack'
            if type(char) == ThirstyCharacter:
                target: HungryCharacter = self.pred
                t_v = Game.get_modded_vitality(target)
                t_a = Game.get_modded_agility(target)
                t_hp, t_m_hp = Game.get_modded_hp(target)
                t_dr = Game.get_modded_damage_reduction(target, t_v)
                t_ev = Game.get_modded_evasion(target, t_a)
                s, a, v = Game.get_modded_stats(char)
                d, f, m, c = Game.get_damage_stats(s, a)
                damage: int = 0
                if ceil(random() * 100) < c:
                    d += 1
                for idx in range(d):
                    result: int = ceil(random() * f)
                    damage += result
                    event_parameters['rolls'].append(result)
                damage += m
                if target.current_damage_buffer:
                    diff: int = damage - target.current_damage_buffer
                    target.current_damage_buffer = -diff if diff < 0 else 0
                    damage = max(diff, 0)
                damage = max(damage - t_dr, 0)
                event_parameters['pre_deltas'].append(t_hp)
                event_parameters['deltas'].append(
                    damage
                )
                if t_ev and ceil(random() * 100) < t_ev:
                    event_parameters['evaded'].append(True)
                else:
                    event_parameters['evaded'].append(False)
                    if t_hp - damage <= 0:
                        target.hp = 0.0
                        self.died(target)
                        return self.game_over(
                            pred_win=False
                        )
                    target.hp -= damage
                UI.draw_game(self, event_parameters)
            else:
                targets: list[ThirstyCharacter] = self.prey
                s, a, v = Game.get_modded_stats(char)
                d, f, m, c = Game.get_damage_stats(s, a)
                for target in targets:
                    t_v = Game.get_modded_vitality(target)
                    t_a = Game.get_modded_agility(target)
                    t_hp, t_m_hp = Game.get_modded_hp(target)
                    t_dr = Game.get_modded_damage_reduction(target, t_v)
                    t_ev = Game.get_modded_evasion(target, t_a)
                    damage: int = 0
                    if ceil(random() * 100) < c:
                        d += 1
                    for idx in range(d):
                        result: int = ceil(random() * f)
                        damage += result
                        event_parameters['rolls'].append(result)
                    damage += m
                    if target.current_damage_buffer:
                        diff: int = damage - target.current_damage_buffer
                        target.current_damage_buffer = -diff if diff < 0 else 0
                        damage = max(diff, 0)
                    damage = max(damage - t_dr, 0)
                    event_parameters['pre_deltas'].append(t_hp)
                    event_parameters['deltas'].append(
                        damage
                    )
                    if t_ev and ceil(random() * 100) < t_ev:
                        event_parameters['evaded'].append(True)
                    else:
                        event_parameters['evaded'].append(False)
                        if t_hp - damage <= 0:
                            target.hp = 0.0
                            self.died(target)
                        target.hp -= damage
                UI.draw_game(self, event_parameters)
        self.next()

    """
    Update with dictionary of changes, dict template:
    target[GameCharacter]:
      'add_hp'
    """
    def update(self) -> None:
        pass

    def next(self) -> None:
        pass

    def died(self, character: GameCharacter) -> None:
        character.deceased = True
        try:
            idx: int = self.initiative.index(character)
            self.initiative.pop(idx)
        except ValueError:
            return

    def game_over(self, pred_win: bool) -> None:
        pass

    @staticmethod
    def update_cooldowns(character: GameCharacter) -> None:
        character.update_cooldowns()
        character.update_statuses()

    def reset_initiative(self) -> None:
        self.initiative = self.prey.copy()
        self.initiative.append(self.pred)
        select: int = 0
        for idx in range(len(self.initiative)):
            if self.initiative[select].deceased:
                continue
            self.initiative.pop(select)
            select += 1
        self.initiative: list[ThirstyCharacter | HungryCharacter] = sorted(
            self.initiative, lambda char: char.agility
        )
        self.turn: ThirstyCharacter | HungryCharacter = self.initiative[0]

    @staticmethod
    def game_characters(
        _T: None | GameCharacter | str = None
    ) -> dict[str, GameCharacter] | list[GameCharacter] | list[str]:
        if not _T:
            return Game.characters
        elif type(_T) == GameCharacter:
            return list(Game.characters.values())
        else:
            return list(Game.characters.keys())

    @staticmethod
    def add_character(name: str, char: GameCharacter) -> None:
        Game.characters[name] = char

    @staticmethod
    def get_character(
        c: str | list[str]
    ) -> GameCharacter | list[GameCharacter] | None:
        li: list[GameCharacter] = []
        if type(c) == str:
            return Game.characters.get(c.lower(), None)
        else:
            for char_string in c.copy():
                char: GameCharacter | None = Game.characters.get(
                    char_string.lower()
                )
                li.append(char)
            return li

    @staticmethod
    def check_save(t: int) -> None:
        if t - Game.snapshot_last > Game.SNAPSHOT_DELAY:
            Game.snapshot_last = t
            return Game.save_characters()

    @staticmethod
    def save_characters() -> None:
        save_state: dict = {}
        log('HNG/SAV')
        for name in Game.characters:
            perk: dict[str, int] = {}
            ability: dict[str, int] = {}
            char: GameCharacter = Game.characters[name]
            for name in char.perks:
                perk[name] = char.perks[name].level
            for name in char.abilities:
                ability[name] = char.abilities[name].level
            save_state[char.display_name] = {
                'lv': char.level,
                's': char.strength,
                'a': char.agility,
                'v': char.vitality,
                'st': char.stat_alloc,
                'pp': char.perk_alloc,
                'ap': char.ability_alloc,
                'w': char.wins,
                'l': char.losses,
                'p': perk,
                'as': ability,
                'b': char.badge
            }
        f = open('data/hungry_db.json', 'w', encoding='utf-8')
        f.write(json.dumps(save_state))
        f.close()


GAMES: dict[Game, int] = {}


class UI:
    HP_WIDTH: int = 35

    @staticmethod
    def get_bar_str(hp: float) -> None:
        out_str: str = '[color=green]'
        orange_len: int = round(UI.HP_WIDTH * hp)
        if hp == 1.0:
            for idx in range(UI.HP_WIDTH):
                out_str += '▰'
            return f'{out_str}[/color]'

        for idx in range(UI.HP_WIDTH):
            if idx == orange_len - 3:
                out_str += '[/color][color=orange]'
            if idx == orange_len:
                out_str += '[/color][color=red]'
            out_str += '▰'
        return f'{out_str}[/color]'

    @staticmethod
    def sheet(
        character: GameCharacter
    ) -> str:
        o_s: str = '\n'
        c_n: str = character.display_name
        c_l: int = character.level
        s, a, v = Game.get_modded_stats(character)
        b: str = character.badge
        bs: str = '   '.join([x for x in character.has_badges])
        c_hp, m_hp = Game.get_modded_hp(character)
        c_st, m_st = Game.get_modded_stamina(character)
        d, f, m, c = Game.get_damage_stats(s, a)
        e: int = Game.get_modded_evasion(character, a)
        dr: int = Game.get_modded_damage_reduction(character, v)
        db: int = Game.get_modded_damage_buffer(character, v)

        o_s += (
            f'{b}[user]{c_n}[/user] [color=white][b][{c_l}][/b][/color]\n' +
            f'[color=red][b][{c_hp}/{m_hp}][/b][/color] ' +
            f'[color=white][STR:{s} AGI:{a} VIT:{v}][/color]\n' +
            f'{UI.get_bar_str(c_hp / m_hp)}\n' +
            f'{UI.get_bar_str(c_st / m_st)}\n' +
            f'[color=green][b][{c_st}/{m_st}][/b][/color]' +
            f' [color=white][ROLL:{d}d{f}+{m} CRIT:{c}% EV:{e}% DR:{dr}' +
            f' DB:{db}]'
        )
        if b:
            o_s += f'\n{bs}'
            o_s += '\n[b]ACHEIVEMENTS:[/b]'
            for name, perk in character.perks.items():
                if not perk.perkiary[name].get('cost'):
                    perk_obj: dict[str, complex] = perk.perkiary.get(name)
                    badge: str = perk_obj.get('badge')
                    max_level: int = perk_obj.get('max_level')
                    badge = badge if badge else '    '
                    o_s += (
                        f'\n{badge}   [b]{name.upper()}[/b]: {perk.level}/' +
                        f'{max_level}'
                    )
        if len(character.perks.keys()):
            o_s += '\n[b]PERKS:[/b]'
            for name, perk in character.perks.items():
                if perk.perkiary[name].get('cost'):
                    perk_obj: dict[str, complex] = perk.perkiary.get(name)
                    max_level: int = perk_obj.get('max_level')
                    o_s += (
                        f'\n       [b]{name.upper()}[/b]: {perk.level}/' +
                        f'{max_level}'
                    )
        o_s += '\n[b]ABILITIES:[/b]'
        for name, ability in character.abilities.items():
            ability_obj: dict[str, complex] = ability.abiliary.get(name)
            max_level: int = ability_obj.get('max_level')
            o_s += (
                f'\n       [b]{name.upper()}[/b]: {ability.level}/' +
                f'{max_level}'
            )
        if (
            character.ability_alloc or
            character.perk_alloc or
            character.stat_alloc
        ):
            o_s += '\n[b]UNSPENT POINTS:[/b]'
            if character.stat_alloc:
                o_s += (
                    '\n       [b]STAT POINTS:[/b] ' +
                    f'{character.stat_alloc}'
                )
            if character.perk_alloc:
                o_s += (
                    '\n       [b]PERK POINTS:[/b] ' +
                    f'{character.perk_alloc}'
                )
            if character.ability_alloc:
                o_s += (
                    '\n       [b]ABILITY POINTS:[/b] ' +
                    f'{character.ability_alloc}'
                )
            o_s += '[/color]'
        return o_s


if path.exists('data/hungry_db.json'):
    f = open('data/hungry_db.json', 'r', encoding='utf-8')
    cdata = json.load(f)
    f.close()

    for name in cdata:
        c = cdata[name]
        char: GameCharacter = GameCharacter(
            name=name,
            level=c['lv'],
            strength=c['s'],
            agility=c['a'],
            vitality=c['v'],
            stat_alloc=c['st'],
            perk_alloc=c['pp'],
            ability_alloc=c['ap'],
            wins=c['w'],
            losses=c['l'],
            perks=c['p'],
            abilities=c['as'],
            badge=c['b']
        )
        Game.add_character(char.name, char)
