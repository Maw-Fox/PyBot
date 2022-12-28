import json
import os

from modules.channel import Channel
from modules.character import Character


class ModLog():
    def __init__(
        self,
        channel: str,
        action: str,
        type: str,
        character: str,
        reason: str
    ) -> None:
        self.channel: str = channel
        self.type: str = type
        self.character: str = character
        self.reason: str = reason
        self.action: str = action
        MOD_LOGS.insert(0, self)
        __save_to_file()


MOD_LOGS: list[ModLog] = []

if os.path.exists('moderation_log.json'):
    f = open('moderation_log.json', 'r', encoding='UTF-8')
    f_s: str = f.read()
    f.close()
    old: list[dict[str, str]] = json.loads(f_s)

    for log in old:
        ModLog(
            channel=log['channel'],
            type=log['type'],
            action=log['action'],
            character=log['character'],
            reason=log['reason']
        )


def __save_to_file() -> None:
    f = open('moderation_log.json', 'w', encoding='UTF-8')
    logs: list[dict[str, str]] = []
    for log in MOD_LOGS:
        logs.append({
            'channel': log.channel,
            'type': log.type,
            'action': log.action,
            'character': log.character,
            'reason': log.reason
        })
    f.write(json.dumps(logs, indent=2))
    f.close()