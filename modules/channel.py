class Channel:
    def __init__(
        self,
        name: str
    ) -> None:
        self.channel = name
        self.title = name
        self.users: list[str] = []

    def remove_user(self, user: str) -> None:
        try:
            self.users.remove(user)
        except ValueError:
            return

    def add_user(self, user: str) -> None:
        self.users.append(user)

    def remove_channel(self, channel: str) -> None:
        CHANNELS.pop(channel)


def remove_from_all_channels(user: str) -> None:
    for c_name in CHANNELS:
        if len(CHANNELS[c_name].users):
            CHANNELS[c_name].remove_user(user)


CHANNELS: dict[str, Channel] = {}
