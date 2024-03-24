import json

from os import path
from random import random
from time import time
from math import floor, ceil
from modules.utils import log
from modules.channel import Channel

DOC: dict[str, dict[str, complex]] = {}


def load_doc() -> None:
    f = open('src/game_templates.json', 'r', encoding='utf-8')
    obj: dict[str, dict[str, complex]] = json.load(f)
    for name in obj:
        DOC[name] = obj[name]
    f.close()


load_doc()

MODIFIER_TEMPLATE: dict[str, int | float] = {
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
    'add_damage': 0,
    'mod_damage': 1.0,
    'add_heal': 0,
    'mod_heal': 1.0,
    'add_damage_reduction': 0,
    'mod_damage_reduction': 1.0,
    'add_damage_buffer': 0,
    'mod_damage_buffer': 1.0,
    'add_evasion': 0,
    'mod_evasion': 1.0,
    'add_damage': 0,
    'mod_damage': 1.0
}


class Character():
    def __init__(
        self,
        name: str,
        level: int = 1,
        max_level: int = 1,
        strength: int = 4,
        agility: int = 4,
        vitality: int = 4,
        spent_stat: int = 11,
        spent_perk: int = 0,
        spent_ability: int = 0,
        wins: list[dict[str, list]] = [],
        losses: list[dict[str, list]] = [],
        perk_levels: dict[str, int] = {},
        ability_levels: dict[str, int] = {
            'attack': 1,
            'heal': 1,
            'rest': 1,
            'defend': 1
        },
        badge: str = ''
    ):
        self.proper_name: str = name
        self.name: str = name.lower()
        self.level: int = level
        self.max_level: int = max_level
        self.wins: list[dict[str, list]] = wins
        self.losses: list[dict[str, list]] = losses
        self.spent_stat: int = spent_stat
        self.spent_perk: int = spent_perk
        self.spent_ability: int = spent_ability
        self.str: int = strength
        self.agi: int = agility
        self.vit: int = vitality
        self.status: dict[str, Status] = {}
        self.hp: float = 1.0
        self.stamina: float = 1.0
        self.desires_refund: int = 0
        self.modifiers: dict[str, int | float] = MODIFIER_TEMPLATE.copy()
        self.ability_modifiers: dict[str, int | float] = self.modifiers.copy()
        self.deceased: bool = False
        self.badge: str = badge
        self.perk_levels: dict[str, int] = perk_levels
        self.ability_levels: dict[str, int] = ability_levels
        self.perks: dict[str, Perk] = {}
        self.build_perkbilities(Perk, self.perks, perk_levels)
        self.abilities: dict[str, Ability] = {}
        self.build_perkbilities(Ability, self.abilities, ability_levels)

    def build_perkbilities(self, cls, ref: dict, obj: dict[str, int]):
        for name in obj:
            level: int = obj[name]
            perkbility: cls = cls(name, level, self)
            ref[name] = perkbility

    def remove_perk(self, perk: str) -> None:
        self.perks.pop(perk)

    def add_perk(self, perk: str, level: int) -> None:
        perk_instance: Perk = Perk(
            perk,
            level,
            self
        )
        self.perks[perk] = perk_instance

    def update_cooldowns(self) -> None:
        for name in self.abilities:
            ability: Ability = self.abilities[name]
            if ability.cooldown:
                ability.cooldown -= 1

    def update_statuses(self) -> None:
        for name in self.status:
            status: Status = self.status[name]
            if status.duration == 1:
                self.status.pop(name)

    def get_unspent(self) -> tuple[int, int, int]:
        """
        -> tuple(stat, perk, ability)
        """
        return (
            10 + self.max_level - self.spent_stat,
            floor(self.max_level / 2) - self.spent_perk,
            floor(self.max_level / 4) - self.spent_ability
        )


class Status:
    def __init__(
        self,
        name: str,
        level: int,
        character: Character,
        duration: int,
        deceased: bool = False,
        **kwargs
    ):
        self.name: str = name
        self.level: int = level
        self.duration: int = duration
        self.deceased: bool = deceased
        self.character: Character = character
        self.modified: dict[str, int | float] = {}
        for arg, value in kwargs.items():
            self.modified[arg] = value
            self.character.modifiers[arg] += value

    def remove(self) -> None:
        for modifier, value in self.modified.items():
            self.character.modifiers[modifier] -= value


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


class Active:
    @staticmethod
    def attack(level: int, ref: dict[str, int | float]) -> None:
        ref['add_stamina'] = ceil((1 - (0.05 * (level - 1))) * 30)

    @staticmethod
    def heal(level: int, ref: dict[str, int | float]) -> None:
        ref['add_heal'] = ceil((level + 1) * 4 * random()) + 5
        ref['add_stamina'] -= 25

    @staticmethod
    def rest(level: int, ref: dict[str, int | float]) -> None:
        ref['add_stamina'] = ceil(40 * (1 + ((level - 1) * 0.075)))

    @staticmethod
    def defend(level: int, ref: dict[str, int | float]) -> None:
        ref['add_stamina'] = ceil(20 * (1 + ((level - 1) * 0.05)))
        ref['add_damage_reduction'] = level * 1 + 3
        ref['add_damage_buffer'] = level * 2 + 4


class Perk:
    perkiary: dict[str, dict] = DOC['passives']

    def __init__(
        self,
        name: str,
        level: int,
        character: Character
    ) -> None:
        self.name: str = name
        self.level: int = level
        self.character: Character = character
        self.modified: dict[str, int | float] = {}
        self.fn = getattr(Passive, Perk.perkiary[name]['setup'])
        self.fn(self.level, self.modified)
        for modifier, value in self.modified.items():
            self.character.modifiers[modifier] += value
        self.badge: str = Perk.perkiary[name].get('badge', '')
        if not character.badge:
            character.badge = self.badge

    def remove(self) -> None:
        for modifier, value in self.modified.items():
            self.character.modifiers[modifier] -= value


class Ability:
    abiliary: dict[str, dict] = DOC['abilities']

    def __init__(
        self,
        name: str,
        level: int,
        character: Character,
        cooldown: int = 0
    ) -> None:
        self.name: str = name
        self.level: int = level
        self.character: Character = character
        self.cooldown: int = cooldown
        self.fn = getattr(Active, Ability.abiliary[name]['setup'])
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


class Pred(Character):
    MOD: float = 1.0

    def __init__(
        self,
        name: str,
        level: int = 1,
        max_level: int = 1,
        strength: int = 4,
        agility: int = 4,
        vitality: int = 4,
        spent_stat: int = 0,
        spent_perk: int = 0,
        spent_ability: int = 0,
        wins: list[dict[str, list]] = [],
        losses: list[dict[str, list]] = [],
        perk_levels: dict[str, int] = {},
        ability_levels: dict[str, int] = {
            'attack': 1,
            'heal': 1,
            'defend': 1,
            'rest': 1
        },
        badge: str = ''
    ):
        super().__init__(
            name,
            level,
            max_level,
            strength,
            agility,
            vitality,
            spent_stat,
            spent_perk,
            spent_ability,
            wins,
            losses,
            perk_levels,
            ability_levels,
            badge
        )
        self.__str: int = self.str
        self.__agi: int = self.agi
        self.__vit: int = self.vit
        self.str: int = 0
        self.agi: int = 0
        self.vit: int = 0
        self.db: int = 0
        self.dr: int = 0
        self.crit: int = 0
        self.die: int = 0
        self.faces: int = 0
        self.heal: int = 0
        self.heal_mod: int = 0
        self.mod: int = 0
        self.evade: int = 0
        self.hp_max: int = 0
        self.recalculate()

    def recalculate(self) -> None:
        self.str = floor(
            (self.modifiers.get('add_strength', 0) + self.__str) *
            self.modifiers.get('mod_strength', 1.0) * self.MOD
        )
        self.agi = floor(
            (self.modifiers.get('add_agility', 0) + self.__agi) *
            self.modifiers.get('mod_agility', 1.0) * self.MOD
        )
        self.vit = floor(
            (self.modifiers.get('add_vitality', 0) + self.__vit) *
            self.modifiers.get('mod_vitality', 1.0) * self.MOD
        )
        self.hp_max = floor(
            self.modifiers.get('add_hp_max', 0) + 100 +
            floor(self.vit / 5) * 15 * self.modifiers.get('mod_hp_max', 1.0)
        )
        self.stamina_max = floor(
            self.modifiers.get('add_stamina_max', 0) + 100 +
            floor(self.vit / 5) * 15
        )
        self.crit = floor(10 + floor(self.agi / 5) * 12.5) % 100
        self.die = (
            1 + floor((30 + floor(self.agi / 5) * 12.5) / 100) +
            floor(self.agi / 15)
        )
        self.faces = 8 + floor(self.str / 4) * 2
        self.mod = floor(self.str / 10) * 3
        self.evade = floor(
            (
                self.modifiers.get('add_evasion', 0) +
                floor(self.agi / 10) * 6
            ) * self.modifiers.get('mod_evasion', 1.0)
        )
        self.dr = floor(
            (
                self.modifiers.get('add_damage_reduction', 0) +
                floor(self.vit / 10) * 2
            ) * self.modifiers.get('mod_damage_reduction', 1.0)
        )
        self.db = floor(
            (
                self.modifiers.get('add_damage_buffer', 0) +
                floor(self.vit / 5) * 3
            ) * self.modifiers.get('mod_damage_buffer', 1.0)
        )
        self.heal_mod = self.modifiers.get('add_heal', 0)
        self.heal = ceil(
            (12 + self.heal_mod) *
            self.modifiers.get('mod_heal', 1.0)
        )


class Prey(Pred):
    MOD: float = 0.6


class Setup:
    __next_check: int = int(time()) + 60

    def __init__(
        self,
        pred: Character,
        prey: list[Character],
        channel: Channel,
        output
    ):
        self.pred: Character = pred
        self.prey: list[Character] = prey.copy()
        self.need_consent: list[Character] = prey.copy()
        self.channel: Channel = channel
        self.output = output
        channel.setup = True
        self.timeout: int = int(time()) + 300
        SETUPS[self] = channel

    def add_consent(self, character: Character) -> None:
        self.need_consent.pop(self.need_consent.index(character))

    def no_consent(self) -> None:
        SETUPS.pop(self)

    @staticmethod
    def get_instance_by_prey(character: Character):
        for setup in SETUPS:
            if character in setup.prey:
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
    MAX_LEVEL: int = 60
    snapshot_last: int = 0
    SNAPSHOT_DELAY: int = 600
    characters: dict[str, Character] = {}
    ACITIVITY_DELAY: int = 10800

    def __init__(
        self,
        pred: Character,
        prey: list[Character],
        channel: Channel,
        output
    ):
        self.activity: int = int(time())
        self.pred: Pred = Pred(
            pred.proper_name,
            pred.level,
            pred.max_level,
            pred.str,
            pred.agi,
            pred.vit,
            pred.spent_stat,
            pred.spent_perk,
            pred.spent_ability,
            pred.wins,
            pred.losses,
            pred.perk_levels,
            pred.ability_levels,
            pred.badge
        )
        self.prey: list[Prey] = [
            Prey(
                p.proper_name,
                p.level,
                p.max_level,
                p.str,
                p.agi,
                p.vit,
                p.spent_stat,
                p.spent_perk,
                p.spent_ability,
                p.wins,
                p.losses,
                p.perk_levels,
                p.ability_levels,
                p.badge
            ) for p in prey
        ]
        self.who: dict[str, Pred | Prey] = {}
        self.who[self.pred.name] = self.pred
        for p in self.prey:
            self.who[p.name] = p
        self.channel: Channel = channel
        channel.hungry = self
        self.output = output
        self.active: bool = True
        self.dead: list[Prey] = []
        GAMES[self] = int(time())
        self.initiative: list[Pred | Prey] = []
        self.reset_initiative()
        self.turn: Pred | Prey = self.initiative[0]

    @staticmethod
    def get_perkability_level_dict(
        perks: dict[str, Perk | Ability]
    ) -> dict[str, int]:
        obj: dict[str, int] = {}
        for perk_name, perk in perks.items():
            obj[perk_name] = perk.level
        return obj

    async def use_ability(
        self,
        char: Pred | Prey,
        ability: Ability,
        targets: list[Pred | Prey] | None = None
    ) -> None:
        event_parameters: dict[str, str | list | bool] = {
            'type': ability.name,
            'deltas_hp': [],
            'deltas_st': [],
            'results': []
        }

        event_parameters['targets'] = targets
        if ability.name == 'attack':
            for target in targets:
                damage: int = 0
                d: int = char.die
                if ceil(random() * 100) < char.crit:
                    d += 1
                for idx in range(d):
                    result: int = ceil(random() * char.faces)
                    damage += result
                damage += char.mod
                o_s: str = (
                    f'{UI.get_formatted_name(char)}\'s attack roll ' +
                    f'on {UI.get_formatted_name(target)}: ' +
                    f'{d}d{char.faces} + {char.mod} - '
                )
                damage = max(damage - target.dr, 0)
                if target.evade and ceil(random() * 100) < target.evade:
                    damage = 0
                    o_s = f'[i]EVADED![/i] {o_s}'
                if target.db:
                    diff: int = damage - target.db
                    o_s += (
                        str(
                            target.db
                        ) + f' - {target.dr}'
                    )
                    target.db = -diff if diff < 0 else 0
                    damage = max(diff, 0)
                else:
                    o_s += f'0 - {target.dr}'
                event_parameters['deltas_hp'].append(
                    damage
                )
                event_parameters['deltas_st'].append(0)
                event_parameters['results'].append(
                    o_s + f' =  {damage}'
                )
                target.hp = float(
                    max(
                        (
                            ceil(target.hp * target.hp_max) - damage
                        ) / target.hp_max, 0.0
                    )
                )
                if target.hp <= 0.0:
                    self.died(target)
        elif ability.name == 'heal':
            target: Pred | Prey = targets[0]
            o_s: str = (
                f'\n{UI.get_formatted_name(char)}\'s heal roll ' +
                f'on {UI.get_formatted_name(target)}: 1d{char.heal} +' +
                f' {char.heal_mod} = '
            )
            h_result: int = ceil(char.heal * random())
            h_result += char.heal_mod
            o_s += f'{h_result}'
            event_parameters['results'].append(o_s)
            event_parameters['deltas_hp'].append(-h_result)
            event_parameters['deltas_st'].append(0)
            event_parameters['roll'] += f'1d{char.heal} + {char.heal_mod}'
            event_parameters['result'] = h_result
            target.hp = float(
                min(
                    h_result + ceil(
                        target.hp * target.hp_max), target.hp_max
                    ) / target.hp_max
            )
        elif ability.name == 'defend':
            a_dr: int = ability.modified['add_damage_reduction']
            a_db: int = ability.modified['add_damage_buffer']
            st_delta: int = ability.modified['add_stamina']
            event_parameters['deltas_st'].append(-st_delta)
            event_parameters['deltas_hp'].append(0)
            char.db += a_db
            char.stamina = float(
                max(
                    ceil(char.stamina * char.stamina_max) + st_delta
                ) / char.stamina_max
            )
            event_parameters['results'].append(
                f'{UI.get_formatted_name(char)} defends! ' +
                f'+{st_delta} stamina, +{a_dr} DR, +{a_db} DB (' +
                f'{char.db})!'
            )
            Status(
                char,
                'Defend',
                'Defending and regenerating stamina',
                1,
                ability.level,
                {
                    'add_damage_reduction': a_dr
                }
            )
        else:
            st_delta: int = ability.modified['add_stamina']
            event_parameters['deltas_st'].append(-st_delta)
            event_parameters['deltas_hp'].append(0)
            char.stamina = float(
                max(
                    ceil(char.stamina * char.stamina_max) + st_delta
                ) / char.stamina_max
            )
            event_parameters['results'].append(
                f'{UI.get_formatted_name(char)} rests! ' +
                f'+{st_delta} stamina!'
            )
        if not self.active:
            event_parameters['game_over'] = True
            return await UI.draw_game(self, event_parameters)
        await UI.draw_game(self, event_parameters)
        await self.next()

    async def next(self) -> None:
        if len(self.initiative) == 1:
            self.reset_initiative()
        else:
            self.initiative.pop(0)
        self.turn = self.initiative[0]
        Game.update_cooldowns(self.turn)
        await self.output.send(
            f'[b]Hungry Game[/b]: ' +
            self.turn.badge +
            '[user]' +
            self.turn.proper_name +
            '[/user]\'s turn!'
        )

    def died(self, character: Pred | Prey) -> None:
        character.deceased = True
        if type(character) == Pred:
            return self.game_over(False)
        else:
            self.dead.append(character)
            if len(self.dead) == len(self.prey):
                return self.game_over(True)
        try:
            idx: int = self.initiative.index(character)
            self.initiative.pop(idx)
        except ValueError:
            return

    @staticmethod
    def set_level(char: Character, n: int) -> None:
        char.level = max(
            min(char.level + n, Game.MAX_LEVEL),
            1
        )
        char.max_level = max(char.level, char.max_level)

    async def game_over(self, pred_win: bool) -> None:
        self.active = False
        char: Character = Game.get_character(self.pred.name)
        if pred_win:
            if len(self.prey) > 1:
                Game.set_level(self.pred, 2)
            else:
                Game.set_level(self.pred, 1)
            for prey in self.prey:
                char: Character = Game.get_character(prey.name)
                if len(self.prey) > 1:
                    Game.set_level(char, -2)
                    continue
                Game.set_level(char, -1)
        else:
            if len(self.prey) > 1:
                Game.set_level(char, -1)
            else:
                Game.set_level(char, -2)
            for prey in self.prey:
                char: Character = Game.get_character(prey.name)
                if len(self.prey) > 1:
                    Game.set_level(char, 1)
                    continue
                Game.set_level(char, 2)

    @staticmethod
    def update_cooldowns(character: Pred | Prey) -> None:
        character.update_cooldowns()
        character.update_statuses()
        character.recalculate()

    def reset_initiative(self) -> None:
        self.initiative = self.prey.copy()
        self.initiative.append(self.pred)
        select: int = 0
        for idx in range(len(self.initiative)):
            if self.initiative[select].deceased:
                self.initiative.pop(select)
                continue
            select += 1
        self.initiative: list[Pred | Prey] = sorted(
            self.initiative,
            key=lambda char: char.agi,
            reverse=True
        )
        self.turn: Pred | Prey = self.initiative[0]

    @staticmethod
    def game_characters(
        _T: None | Character | str = None
    ) -> dict[str, Character] | list[Character] | list[str]:
        if not _T:
            return Game.characters
        elif type(_T) == Character:
            return list(Game.characters.values())
        else:
            return list(Game.characters.keys())

    @staticmethod
    def add_character(name: str, char: Character) -> None:
        Game.characters[name] = char

    def get_ingame(
        self, c: str | list[str]
    ) -> Pred | Prey | list[Pred | Prey] | None:
        li: list[Pred | Prey] = []
        if type(c) == str:
            return self.who.get(c.lower(), None)
        for char_string in c.copy():
            char = self.who.get(
                char_string.lower()
            )
            li.append(char)
        return li

    @staticmethod
    def get_character(
        c: str | list[str]
    ) -> Character | list[Character] | None:
        li: list[Character] = []
        if type(c) == str:
            return Game.characters.get(c.lower(), None)
        for char_string in c.copy():
            char: Character | None = Game.characters.get(
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
            char: Character = Game.characters[name]
            for name in char.perks:
                perk[name] = char.perks[name].level
            for name in char.abilities:
                ability[name] = char.abilities[name].level
            save_state[char.proper_name] = {
                'lv': char.level,
                'mlv': char.max_level,
                's': char.str,
                'a': char.agi,
                'v': char.vit,
                'st': char.spent_stat,
                'pp': char.spent_perk,
                'ap': char.spent_ability,
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
    def get_formatted_name(char: Pred | Prey) -> str:
        return f'[user]{char.proper_name.capitalize()}[/user]' + char.badge

    @staticmethod
    def get_formatted_name_full(char: Pred | Prey) -> str:
        return (
            f'[color=white][b][{char.level}][/b][/color]' +
            UI.get_formatted_name(char)
        )

    @staticmethod
    def get_formatted_bars(
        hp: float,
        stam: float,
        d_hp: int = 0,
        d_stam: int = 0
    ) -> str:
        o_s: str = '\n'
        o_s += UI.get_bar_str(hp)
        if d_hp:
            col: str = '  [color=red]-'
            if d_hp > 0:
                col = '  [color=green]+'
            o_s += f'{col}+{d_hp}[/color]'
        o_s += f'\n{UI.get_bar_str(stam)}'
        if d_stam:
            col: str = '  [color=red]-'
            if d_stam > 0:
                col = '  [color=green]+'
            o_s += f'{col}{d_stam}[/color]'
        return o_s

    @staticmethod
    async def draw_game_start(
        game: Game
    ) -> None:
        print(game.prey)
        o_s: str = '[b]Hungry Game[/b]:\n[b]Predator[/b]:\n'
        o_s += UI.get_formatted_name_full(game.pred)
        o_s += UI.get_formatted_bars(
            game.pred.hp,
            game.pred.stamina
        )
        o_s += '\n[b]Prey[/b]:'
        for c in game.prey:
            o_s += f'\n{UI.get_formatted_name_full(c)}'
            o_s += UI.get_formatted_bars(c.hp, c.stamina)
        o_s += (
            '\n[b]GAME START![b] ' +
            f'First turn:{game.turn.proper_name.capitalize()}'
        )
        await game.output.send(
            o_s
        )

    @staticmethod
    async def draw_game(
        game: Game,
        event: dict[str, list | str | int]
    ) -> None:
        o_s: str = '[b]Hungry Game[/b]:\n[b]Predator[/b]:\n'
        o_s += UI.get_formatted_name_full(game.pred)
        if game.pred in event['targets']:
            idx: int = event['targets'].index(game.pred)
            o_s += UI.get_formatted_bars(
                game.pred.hp,
                game.pred.stamina,
                event['deltas_hp'][idx],
                event['deltas_st'][idx]
            )
        else:
            o_s += UI.get_formatted_bars(
                game.pred.hp,
                game.pred.stamina
            )
        o_s += '\n[b]Prey[/b]:'
        for c in game.prey:
            o_s += f'\n{UI.get_formatted_name_full(c)}'
            if c in event['targets']:
                idx: int = event['targets'].index(c)
                o_s += UI.get_formatted_bars(
                    c.hp,
                    c.stamina,
                    event['deltas_hp'][idx],
                    event['deltas_st'][idx]
                )
            else:
                o_s += UI.get_formatted_bars(
                    c.hp,
                    c.stamina
                )
        for result in event['results']:
            o_s += '\n' + result
        await game.output.send(
            o_s
        )

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
        character: Character
    ) -> str:
        o_s: str = '\n'
        c_n: str = character.proper_name
        c_l: int = character.level
        b: str = character.badge
        s: int = floor(
            (character.modifiers.get('add_strength', 0) + character.str) *
            character.modifiers.get('mod_strength', 1.0)
        )
        a: int = floor(
            (character.modifiers.get('add_agility', 0) + character.agi) *
            character.modifiers.get('mod_agility', 1.0)
        )
        v: int = floor(
            (character.modifiers.get('add_vitality', 0) + character.vit) *
            character.modifiers.get('mod_vitality', 1.0)
        )
        m_hp: int = floor(
            character.modifiers.get('add_hp_max', 0) + 100 +
            floor(v / 5) * 15 *
            character.modifiers.get('mod_hp_max', 1.0)
        )
        m_st: int = floor(
            character.modifiers.get('add_stamina_max', 0) + 100 +
            floor(v / 5) * 15
        )
        c: int = (10 + floor(a / 5) * 12.5) % 100
        d: int = (
            1 + floor((30 + floor(a / 5) * 12.5) / 100) +
            floor(a / 15)
        )
        f: int = 8 + floor(s / 4) * 2
        m: int = floor(s / 10) * 3
        e: int = floor(
            (
                character.modifiers.get('add_evasion', 0) +
                floor(a / 10) * 6
            ) * character.modifiers.get('mod_evasion', 1.0)
        )
        dr: int = floor(
            (
                character.modifiers.get('add_damage_reduction', 0) +
                floor(v / 10) * 2
            ) * character.modifiers.get('mod_damage_reduction', 1.0)
        )
        db: int = floor(
            (
                character.modifiers.get('add_damage_buffer', 0) +
                floor(v / 5) * 3
            ) * character.modifiers.get('mod_damage_buffer', 1.0)
        )
        c_hp: int = floor(m_hp * character.hp)
        c_st: int = floor(m_st * character.stamina)
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
        sp, pp, ap = character.get_unspent()
        if sp or pp or ap:
            o_s += '\n[b]UNSPENT POINTS:[/b]'
            if sp:
                o_s += f'\n       [b]STAT POINTS:[/b] {sp}'
            if pp:
                o_s += f'\n       [b]PERK POINTS:[/b] {pp}'
            if ap:
                o_s += f'\n       [b]ABILITY POINTS:[/b] {ap}'
        o_s += '[/color]'
        return o_s


if path.exists('data/hungry_db.json'):
    f = open('data/hungry_db.json', 'r', encoding='utf-8')
    cdata = json.load(f)
    f.close()

    for name in cdata:
        c = cdata[name]
        char: Character = Character(
            name=name,
            level=c['lv'],
            max_level=c['mlv'],
            strength=c['s'],
            agility=c['a'],
            vitality=c['v'],
            spent_stat=c['st'],
            spent_perk=c['pp'],
            spent_ability=c['ap'],
            wins=c['w'],
            losses=c['l'],
            perk_levels=c['p'],
            ability_levels=c['as'],
            badge=c['b']
        )
        Game.add_character(char.name, char)
