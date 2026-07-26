"""Paletas de cores para os modos escuro e claro."""

THEMES = {
    "dark": {
        "BG": "#101418",
        "BG_PANEL": "#171b20",
        "BG_CARD": "#1d232b",
        "BG_INPUT": "#242b33",
        "CHIP_BG": "#2a3038",
        "FG": "#e7edf3",
        "FG_MUTED": "#8b98a5",
        "ACCENT": "#4cc2ff",
        "ACCENT_DARK": "#2a9fd9",
        "ACCENT_FG": "#06141f",
        "ACCENT_TINT": "#152a38",
        "RISK_SAFE": "#4fd8ac",
        "RISK_SAFE_BG": "#1b3a2f",
        "RISK_CAUTION": "#f0b955",
        "RISK_CAUTION_BG": "#3a2f16",
        "DANGER": "#e05a4d",
        "DANGER_BG": "#3a201d",
        "SELECT_COLOR": "#0c1013",
        "LOG_BG": "#0c1013",
        "LOG_FG": "#c6d0da",
        "BORDER": "#262c34",
    },
    "light": {
        "BG": "#f4f6f8",
        "BG_PANEL": "#ffffff",
        "BG_CARD": "#ffffff",
        "BG_INPUT": "#eef1f4",
        "CHIP_BG": "#e7ebef",
        "FG": "#1b2228",
        "FG_MUTED": "#5b6672",
        "ACCENT": "#0067c0",
        "ACCENT_DARK": "#004e91",
        "ACCENT_FG": "#ffffff",
        "ACCENT_TINT": "#dcedfb",
        "RISK_SAFE": "#188a67",
        "RISK_SAFE_BG": "#dcf3ea",
        "RISK_CAUTION": "#9c6a12",
        "RISK_CAUTION_BG": "#faecd2",
        "DANGER": "#c9403a",
        "DANGER_BG": "#fbe2e0",
        "SELECT_COLOR": "#dfe6ec",
        "LOG_BG": "#eef1f4",
        "LOG_FG": "#1b2228",
        "BORDER": "#e2e6ea",
    },
}

_current = "dark"


def set_theme(name: str):
    global _current
    if name in THEMES:
        _current = name


def get_theme_name() -> str:
    return _current


def toggle_theme() -> str:
    set_theme("light" if _current == "dark" else "dark")
    return _current


def colors() -> dict:
    return THEMES[_current]
