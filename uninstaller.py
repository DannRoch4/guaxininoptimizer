"""
Desinstalador assistido: roda o desinstalador OFICIAL do proprio programa
(pego do registro, igual o "Aplicativos e Recursos" do Windows usa) e depois
procura pastas residuais para voce decidir, uma por uma, o que apagar.

Nada e apagado automaticamente — a busca so lista candidatos com caminho
completo e tamanho, e cada um precisa ser confirmado.
"""

import os
import re
import subprocess

import cleaner_core as core

LOCALAPPDATA = os.environ.get("LOCALAPPDATA", "")
APPDATA = os.environ.get("APPDATA", "")
PROGRAMDATA = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
PROGRAMFILES = os.environ.get("PROGRAMFILES", r"C:\Program Files")
PROGRAMFILES_X86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")

LEFTOVER_ROOTS = [LOCALAPPDATA, APPDATA, PROGRAMDATA, PROGRAMFILES, PROGRAMFILES_X86]

_STOPWORDS = {"x64", "x86", "64bit", "32bit", "version", "inc", "corp", "corporation",
               "ltd", "llc", "software", "technologies", "the"}


def _normalize(text):
    text = (text or "").lower()
    text = re.sub(r"[™®©]", "", text)
    text = re.sub(r"\bv?\d+(\.\d+)+\b", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    words = [w for w in text.split() if w and w not in _STOPWORDS]
    return " ".join(words)


def launch_uninstaller(program, log_callback=None):
    """Inicia o desinstalador oficial do programa (o instalador pode abrir uma tela). Retorna o Popen ou None."""
    cmd = program.get("quiet_uninstall_string") or program.get("uninstall_string")
    if not cmd:
        if log_callback:
            log_callback("  nenhum comando de desinstalacao encontrado no registro para este programa.")
        return None
    try:
        return subprocess.Popen(cmd, shell=True)
    except Exception as exc:
        if log_callback:
            log_callback(f"  erro ao iniciar o desinstalador: {exc}")
        return None


def find_leftovers(program):
    """Procura pastas cujo nome bate com o nome do programa/publisher nas pastas comuns de instalacao."""
    name_norm = _normalize(program.get("name", ""))
    publisher_norm = _normalize(program.get("publisher", ""))
    if len(name_norm) < 3:
        return []

    seen_paths = set()
    candidates = []

    for root in LEFTOVER_ROOTS:
        if not root or not os.path.isdir(root):
            continue
        try:
            with os.scandir(root) as it:
                entries = list(it)
        except OSError:
            continue
        for entry in entries:
            try:
                if not entry.is_dir(follow_symlinks=False):
                    continue
            except OSError:
                continue
            folder_norm = _normalize(entry.name)
            if len(folder_norm) < 3:
                continue
            match = folder_norm in name_norm or name_norm in folder_norm
            if not match and publisher_norm and len(publisher_norm) >= 3:
                match = folder_norm in publisher_norm or publisher_norm in folder_norm
            if match and entry.path not in seen_paths:
                seen_paths.add(entry.path)
                candidates.append(entry.path)

    install_location = program.get("install_location") or ""
    if install_location and os.path.isdir(install_location) and install_location not in seen_paths:
        seen_paths.add(install_location)
        candidates.append(install_location)

    results = []
    for path in candidates:
        size, count = core.scan_dir_contents([path])
        results.append(dict(path=path, size=size, count=count))
    results.sort(key=lambda r: r["size"], reverse=True)
    return results


def delete_leftover(path, log_callback=None):
    import shutil
    try:
        size, _ = core.scan_dir_contents([path])
        shutil.rmtree(path, ignore_errors=True)
        if os.path.exists(path):
            if log_callback:
                log_callback(f"  nao foi possivel remover totalmente: {path} (arquivos em uso)")
            return 0
        return size
    except Exception as exc:
        if log_callback:
            log_callback(f"  erro ao remover '{path}': {exc}")
        return 0
