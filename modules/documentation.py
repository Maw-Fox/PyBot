import json


class Documentation:
    def __init__(
        self,
        id: str,
        pretense: str,
        subtext: list[dict[str, str | list[str]]] | None = None
    ):
        self.id: str = id
        self.pretense: str = pretense
        self.subtext: list[dict[str, str | list[str]]] = subtext
        self.output: str = f'[color=white]{pretense}'
        if not subtext:
            self.output += '[/color]'
            docs[id] = self
            return
        if type(subtext[0]) == str:
            temp: str = '\n'.join(subtext)
            self.output += f'\n{temp}[/color]'
            docs[id] = self
            return
        for group in subtext:
            name: str = group['name']
            lines: list[str] = group['subtext']
            self.output += f'\n[color=green][b]{name}:[/b][/color]'
            for line in lines:
                self.output += f'\n   {line}'
        self.output += '[/color]'
        docs[id] = self


docs: dict[str, Documentation] = {}


def __load_doc() -> None:
    f = open('src/docs.json', 'r', encoding='utf-8')
    obj: dict[str, complex] = json.load(f)
    for name in obj:
        Documentation(
            name,
            obj[name]['pretense'],
            obj[name].get('subtext', None)
        )
    f.close()


__load_doc()
