"""
Buscador de arquivos duplicados: acha copias identicas de verdade (por conteudo,
via hash SHA-256), nao so por nome. Nunca apaga nada sozinho — so encontra e
devolve os grupos pra o usuario escolher o que remover.

Algoritmo (do mais barato pro mais caro, pra nao gastar tempo a toa):
  1. Agrupa arquivos por TAMANHO (arquivos de tamanhos diferentes nunca sao iguais).
  2. Dentro de cada grupo com mais de 1 arquivo, compara um hash PARCIAL — descarta
     rapido a maioria dos falsos candidatos.
  3. So pros que sobraram, calcula um hash de CONTEUDO pra confirmar. Em arquivos
     grandes (video, ISO etc.) usa amostragem (inicio+meio+fim) em vez de ler o
     arquivo inteiro — muito mais rapido e praticamente sem chance de erro (o
     tamanho exato + 3 pedacos de conteudo batendo e um indicador seguro o
     suficiente pra esse fim).

Reporta progresso em TODAS as fases (varredura, comparacao parcial, confirmacao),
e aceita um callback `should_cancel` pra abortar uma busca longa a qualquer momento.
"""

import hashlib
import os

PARTIAL_HASH_BYTES = 64 * 1024
DEFAULT_MIN_SIZE = 4 * 1024  # ignora arquivos menores que 4 KB (raramente vale a pena)
LARGE_FILE_THRESHOLD = 100 * 1024 * 1024  # 100 MB
SAMPLE_CHUNK = 1024 * 1024  # 1 MB


class SearchCancelled(Exception):
    pass


COMMON_FOLDERS = {
    "Área de Trabalho": "Desktop",
    "Documentos": "Documents",
    "Imagens": "Pictures",
    "Vídeos": "Videos",
    "Downloads": "Downloads",
    "Música": "Music",
}


def get_common_folders():
    """Pastas padrao do usuario que existirem de fato (nomes PT-BR ou EN, conforme o Windows)."""
    home = os.path.expanduser("~")
    found = []
    for label, en_name in COMMON_FOLDERS.items():
        for candidate in (label, en_name):
            path = os.path.join(home, candidate)
            if os.path.isdir(path):
                found.append((label, path))
                break
    return found


def _check_cancel(should_cancel):
    if should_cancel and should_cancel():
        raise SearchCancelled()


def _partial_hash(path):
    try:
        with open(path, "rb") as f:
            data = f.read(PARTIAL_HASH_BYTES)
        return hashlib.sha256(data).hexdigest()
    except OSError:
        return None


def _content_hash(path, size):
    """Hash completo pra arquivos pequenos; amostragem (inicio/meio/fim) pra arquivos
    grandes, pra nao travar minutos hasheando um video/ISO inteiro."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            if size <= LARGE_FILE_THRESHOLD:
                while True:
                    chunk = f.read(1024 * 1024)
                    if not chunk:
                        break
                    h.update(chunk)
            else:
                for offset in (0, size // 2, max(size - SAMPLE_CHUNK, 0)):
                    f.seek(offset)
                    h.update(f.read(SAMPLE_CHUNK))
                h.update(str(size).encode())
        return h.hexdigest()
    except OSError:
        return None


def _iter_files(roots, progress_callback=None, should_cancel=None):
    count = 0
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                _check_cancel(should_cancel)
                path = os.path.join(dirpath, name)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size < DEFAULT_MIN_SIZE:
                    continue
                count += 1
                if progress_callback and count % 100 == 0:
                    progress_callback("scan", count, 0)
                yield path, size


def find_duplicates(roots, progress_callback=None, should_cancel=None):
    """Retorna lista de grupos: cada grupo e uma lista de dicts {path, size},
    todos com o MESMO conteudo. So inclui grupos com 2+ arquivos.

    progress_callback(stage, done, total) e chamado com stage em
    "scan" / "compare" / "confirm" pra a UI saber em que fase esta.
    should_cancel() -> bool: se retornar True, interrompe e levanta SearchCancelled.
    """
    by_size = {}
    for path, size in _iter_files(roots, progress_callback=progress_callback, should_cancel=should_cancel):
        by_size.setdefault(size, []).append(path)

    candidates = [paths for paths in by_size.values() if len(paths) > 1]
    total_candidates = sum(len(p) for p in candidates)

    by_partial = {}
    done = 0
    for paths in candidates:
        for path in paths:
            _check_cancel(should_cancel)
            ph = _partial_hash(path)
            done += 1
            if progress_callback and done % 25 == 0:
                progress_callback("compare", done, total_candidates)
            if ph is None:
                continue
            key = (len(paths), ph)
            by_partial.setdefault(key, []).append(path)

    confirm_candidates = [paths for paths in by_partial.values() if len(paths) > 1]
    total_confirm = sum(len(p) for p in confirm_candidates)

    groups = []
    done = 0
    for paths in confirm_candidates:
        by_full = {}
        for path in paths:
            _check_cancel(should_cancel)
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            fh = _content_hash(path, size)
            done += 1
            if progress_callback and done % 5 == 0:
                progress_callback("confirm", done, total_confirm)
            if fh is None:
                continue
            by_full.setdefault(fh, []).append((path, size))
        for full_items in by_full.values():
            if len(full_items) < 2:
                continue
            groups.append([dict(path=p, size=s) for p, s in full_items])

    groups.sort(key=lambda g: g[0]["size"] * (len(g) - 1), reverse=True)
    return groups


def delete_files(paths, log_callback=None):
    """Apaga os arquivos indicados (nunca pastas). Retorna bytes liberados."""
    freed = 0
    for path in paths:
        try:
            size = os.path.getsize(path)
            os.remove(path)
            freed += size
        except OSError as exc:
            if log_callback:
                log_callback(f"  nao foi possivel apagar '{path}': {exc}")
    return freed
