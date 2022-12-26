from modules.channel import Channel


class Log():
    pass


class AgeLog(Log):
    pass


KILLS_LOG: dict[Channel, Log] = {}
