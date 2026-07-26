"""Log compartilhado de reversao: guarda o estado original de tudo que o app altera
(inicializacao, servicos, tweaks de registro) para poder desfazer com um clique."""

import json
import os

REVERT_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guaxinim_revert_log.json")
SECTIONS = ("startup", "services", "registry_tweaks")


def load():
    if os.path.isfile(REVERT_LOG_PATH):
        try:
            with open(REVERT_LOG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for section in SECTIONS:
                    data.setdefault(section, {})
                return data
        except Exception:
            pass
    return {section: {} for section in SECTIONS}


def save(data):
    try:
        with open(REVERT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def record_if_new(section, key, value):
    data = load()
    if key not in data[section]:
        data[section][key] = value
        save(data)


def has_any_changes():
    data = load()
    return any(data[section] for section in SECTIONS)
