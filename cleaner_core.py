"""Motor de escaneamento e limpeza: nada de interface aqui, so logica."""

import ctypes
import os
import re
import shutil
import string
import subprocess
import sys


def human_size(num_bytes: float) -> str:
    step = 1024.0
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num_bytes) < step:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= step
    return f"{num_bytes:.2f} PB"


def get_disk_usage(drive: str = None):
    drive = drive or os.environ.get("SYSTEMDRIVE", "C:") + "\\"
    total, used, free = shutil.disk_usage(drive)
    return dict(drive=drive, total=total, used=used, free=free)


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> bool:
    """Reabre o proprio programa elevado via UAC. Retorna True so se o Windows aceitou
    disparar o pedido (nao garante que o usuario clicou "Sim" no prompt — se ele recusar,
    o processo elevado simplesmente nao chega a abrir e quem chamou deve seguir sem admin)."""
    if getattr(sys, "frozen", False):
        # .exe empacotado: sys.executable JA e o proprio programa, sys.argv[0] tambem
        # aponta pra ele — incluir os dois duplicaria o caminho como argumento.
        args = sys.argv[1:]
    else:
        args = [sys.argv[0]] + sys.argv[1:]
    params = " ".join(f'"{a}"' for a in args)
    try:
        result = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        return result > 32
    except Exception:
        return False


def _iter_files_safe(root):
    """Percorre recursivamente ignorando entradas inacessiveis."""
    try:
        with os.scandir(root) as it:
            entries = list(it)
    except OSError:
        return
    for entry in entries:
        try:
            if entry.is_dir(follow_symlinks=False):
                yield from _iter_files_safe(entry.path)
            else:
                yield entry
        except OSError:
            continue


def scan_dir_contents(paths):
    total_size = 0
    total_files = 0
    for path in paths:
        if not path or not os.path.isdir(path):
            continue
        for entry in _iter_files_safe(path):
            try:
                total_size += entry.stat(follow_symlinks=False).st_size
                total_files += 1
            except OSError:
                continue
    return total_size, total_files


def scan_file_glob(paths, pattern):
    import fnmatch
    total_size = 0
    total_files = 0
    for path in paths:
        if not path or not os.path.isdir(path):
            continue
        try:
            with os.scandir(path) as it:
                for entry in it:
                    if entry.is_file(follow_symlinks=False) and fnmatch.fnmatch(entry.name, pattern):
                        try:
                            total_size += entry.stat().st_size
                            total_files += 1
                        except OSError:
                            continue
        except OSError:
            continue
    return total_size, total_files


def _recycle_bin_paths():
    """Pasta $Recycle.Bin de cada unidade que existir de fato no PC."""
    paths = []
    for letter in string.ascii_uppercase:
        candidate = f"{letter}:\\$Recycle.Bin"
        if os.path.isdir(candidate):
            paths.append(candidate)
    return paths


def scan_recycle_bin():
    """Soma o tamanho real dos arquivos dentro de $Recycle.Bin em todas as unidades.
    Mais preciso que a propriedade Size do COM Shell.Application, que costuma
    reportar valores incorretos/zerados para muitos tipos de item."""
    return scan_dir_contents(_recycle_bin_paths())


def _parse_size_from_text(text, keyword):
    """Acha a primeira linha com `keyword` e extrai um tamanho tipo '7,91 GB' / '7.91 GB'."""
    for line in text.splitlines():
        if keyword.lower() in line.lower():
            m = re.search(r"([\d.,]+)\s*(GB|MB|KB|bytes)", line, re.IGNORECASE)
            if m:
                value = float(m.group(1).replace(",", "."))
                unit = m.group(2).upper()
                mult = {"GB": 1024 ** 3, "MB": 1024 ** 2, "KB": 1024, "BYTES": 1}[unit]
                return int(value * mult)
    return None


def scan_winsxs_reclaimable():
    """Roda o DISM AnalyzeComponentStore e le quanto e reclamavel (backups de updates antigos).
    Isso e o que realmente pode ser liberado — nao o tamanho total do WinSxS."""
    try:
        proc = subprocess.run(
            ["Dism", "/Online", "/Cleanup-Image", "/AnalyzeComponentStore"],
            capture_output=True, text=True, timeout=300, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        return None, None
    size = _parse_size_from_text(proc.stdout, "backup")
    return size, None


def scan_system_restore():
    """Soma o espaco atualmente usado por pontos de restauracao (Shadow Copy) em todas as unidades."""
    script = "(Get-CimInstance Win32_ShadowStorage | Measure-Object -Property UsedSpace -Sum).Sum"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        raw = result.stdout.strip()
        return (int(float(raw)) if raw else 0), None
    except Exception:
        return 0, None


def scan_category(cat):
    """Retorna (size_bytes, file_count) sem apagar nada."""
    kind = cat["kind"]
    if kind == "dir_contents":
        return scan_dir_contents(cat["paths"])
    if kind == "file_glob":
        return scan_file_glob(cat["paths"], cat["pattern"])
    if kind == "recycle_bin":
        return scan_recycle_bin()
    if kind == "wu_cache":
        return scan_dir_contents(cat["paths"])
    if kind == "windows_old":
        return scan_dir_contents(cat["paths"])
    if kind == "font_cache":
        return scan_dir_contents(cat["paths"])
    if kind == "dism_cleanup":
        return scan_winsxs_reclaimable()
    if kind == "system_restore":
        return scan_system_restore()
    return 0, 0


def _delete_dir_contents(paths, log=None):
    freed = 0
    for path in paths:
        if not path or not os.path.isdir(path):
            continue
        try:
            with os.scandir(path) as it:
                entries = list(it)
        except OSError:
            continue
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    size = sum(e.stat(follow_symlinks=False).st_size for e in _iter_files_safe(entry.path))
                    shutil.rmtree(entry.path, ignore_errors=True)
                    if not os.path.exists(entry.path):
                        freed += size
                else:
                    size = entry.stat().st_size
                    os.remove(entry.path)
                    freed += size
            except OSError as exc:
                if log:
                    log(f"  ignorado (em uso): {entry.name}")
    return freed


def _delete_file_glob(paths, pattern, log=None):
    import fnmatch
    freed = 0
    for path in paths:
        if not path or not os.path.isdir(path):
            continue
        try:
            with os.scandir(path) as it:
                entries = [e for e in it if e.is_file(follow_symlinks=False) and fnmatch.fnmatch(e.name, pattern)]
        except OSError:
            continue
        for entry in entries:
            try:
                size = entry.stat().st_size
                os.remove(entry.path)
                freed += size
            except OSError:
                if log:
                    log(f"  ignorado (em uso): {entry.name}")
    return freed


def _empty_recycle_bin(log=None):
    size_before, _ = scan_recycle_bin()
    SHERB_NOCONFIRMATION = 0x00000001
    SHERB_NOPROGRESSUI = 0x00000002
    SHERB_NOSOUND = 0x00000004
    flags = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
    try:
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
    except Exception as exc:
        if log:
            log(f"  erro ao esvaziar lixeira: {exc}")
        return 0
    return size_before


def _clean_wu_cache(paths, log=None):
    """Para wuauserv/bits, limpa a pasta, e reinicia os servicos."""
    services = ["wuauserv", "bits"]
    stopped = []
    for svc in services:
        try:
            subprocess.run(["net", "stop", svc], capture_output=True, timeout=30,
                            creationflags=subprocess.CREATE_NO_WINDOW)
            stopped.append(svc)
        except Exception as exc:
            if log:
                log(f"  nao consegui parar {svc}: {exc}")
    try:
        freed = _delete_dir_contents(paths, log=log)
    finally:
        for svc in stopped:
            try:
                subprocess.run(["net", "start", svc], capture_output=True, timeout=30,
                                creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception as exc:
                if log:
                    log(f"  nao consegui reiniciar {svc}: {exc}")
    return freed


def _clean_font_cache(paths, log=None):
    """Para o servico FontCache, limpa a pasta, e reinicia o servico (mesmo padrao do cache
    do Windows Update — o arquivo fica em uso enquanto o servico esta rodando)."""
    stopped = False
    try:
        subprocess.run(["net", "stop", "FontCache"], capture_output=True, timeout=30,
                        creationflags=subprocess.CREATE_NO_WINDOW)
        stopped = True
    except Exception as exc:
        if log:
            log(f"  nao consegui parar o servico FontCache: {exc}")
    try:
        freed = _delete_dir_contents(paths, log=log)
    finally:
        if stopped:
            try:
                subprocess.run(["net", "start", "FontCache"], capture_output=True, timeout=30,
                                creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception as exc:
                if log:
                    log(f"  nao consegui reiniciar o servico FontCache: {exc}")
    return freed


def _dism_cleanup(log=None):
    """Roda o DISM StartComponentCleanup e devolve stdout para log (tamanho exato so se sabe depois)."""
    try:
        proc = subprocess.run(
            ["Dism", "/Online", "/Cleanup-Image", "/StartComponentCleanup"],
            capture_output=True, text=True, timeout=1800,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if log:
            for line in proc.stdout.splitlines():
                if line.strip():
                    log(f"  DISM: {line.strip()}")
        return proc.returncode == 0
    except Exception as exc:
        if log:
            log(f"  erro no DISM: {exc}")
        return False


def _remove_windows_old(paths, log=None):
    """Remove Windows.old usando o utilitario de limpeza do proprio Windows (cleanmgr)."""
    for path in paths:
        if not os.path.isdir(path):
            continue
        try:
            size, _ = scan_dir_contents([path])
        except Exception:
            size = 0
        try:
            subprocess.run(
                ["takeown", "/F", path, "/R", "/D", "Y"],
                capture_output=True, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            subprocess.run(
                ["icacls", path, "/grant", "*S-1-5-32-544:F", "/T", "/C", "/Q"],
                capture_output=True, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            shutil.rmtree(path, ignore_errors=True)
            if not os.path.exists(path):
                return size
            if log:
                log("  nao foi possivel remover totalmente Windows.old (arquivos protegidos).")
        except Exception as exc:
            if log:
                log(f"  erro removendo Windows.old: {exc}")
    return 0


def _reduce_system_restore(log=None):
    """Reduz a cota maxima de armazenamento de pontos de restauracao, forcando o Windows a apagar
    os pontos mais antigos pra caber no novo teto. Restauracao do sistema continua ativa."""
    touched = False
    for letter in string.ascii_uppercase:
        drive = f"{letter}:"
        if not os.path.isdir(drive + "\\"):
            continue
        try:
            result = subprocess.run(
                ["vssadmin", "resize", "shadowstorage", f"/for={drive}", f"/on={drive}", "/maxsize=5GB"],
                capture_output=True, text=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                touched = True
                if log:
                    log(f"  cota de restauracao reduzida em {drive}")
        except Exception as exc:
            if log:
                log(f"  erro ao ajustar restauracao em {drive}: {exc}")
    return -1 if touched else 0  # -1 = sucesso, tamanho exato só aparece na comparacao real de disco


def clean_category(cat, log=None):
    """Executa a limpeza da categoria e retorna bytes liberados (estimativa quando aplicavel)."""
    kind = cat["kind"]
    if kind == "dir_contents":
        return _delete_dir_contents(cat["paths"], log=log)
    if kind == "file_glob":
        return _delete_file_glob(cat["paths"], cat["pattern"], log=log)
    if kind == "recycle_bin":
        return _empty_recycle_bin(log=log)
    if kind == "wu_cache":
        return _clean_wu_cache(cat["paths"], log=log)
    if kind == "windows_old":
        return _remove_windows_old(cat["paths"], log=log)
    if kind == "font_cache":
        return _clean_font_cache(cat["paths"], log=log)
    if kind == "dism_cleanup":
        ok = _dism_cleanup(log=log)
        return 0 if not ok else -1  # -1 sinaliza "sucesso mas tamanho so sera visto pela diferenca real de disco"
    if kind == "system_restore":
        return _reduce_system_restore(log=log)
    return 0
