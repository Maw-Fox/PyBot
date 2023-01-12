from typing import TypeAlias, Callable

# Type Aliasing
StrInt: TypeAlias = str | int
DbRow: TypeAlias = list[StrInt]
Callback: TypeAlias = Callable[[], None]
StrNone: TypeAlias = str | None
IntMap: TypeAlias = dict[str, int]
StrMap: TypeAlias = dict[str, str]
StrIntMap: TypeAlias = dict[str, str | int]
FltMap: TypeAlias = dict[str, float]
StrFltMap: TypeAlias = dict[str, str | float]
FltIntMap: TypeAlias = dict[str, float | int]
