LEFT_TO_RIGHT_ISOLATE = "\u2066"
FIRST_STRONG_ISOLATE = "\u2068"
POP_DIRECTIONAL_ISOLATE = "\u2069"


def local_item_code(code: str) -> str:
    _, separator, local_code = code.partition("-")
    return local_code if separator else code


def isolated_code(code: str) -> str:
    return f"{LEFT_TO_RIGHT_ISOLATE}{code}{POP_DIRECTIONAL_ISOLATE}"


def isolated_title(title: str) -> str:
    return f"{FIRST_STRONG_ISOLATE}{title}{POP_DIRECTIONAL_ISOLATE}"
