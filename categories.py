"""
Definicao de todas as categorias de limpeza.

Cada categoria e um dicionario com:
    id            -> identificador unico
    name          -> nome exibido na GUI
    description   -> texto curto explicando o que e
    risk          -> "safe" (seguro, regenaravel) ou "cuidado" (risco/efeito colateral)
    admin         -> True se normalmente precisa de admin para limpar tudo
    default       -> True se vem marcado por padrao no scan
    kind          -> tipo de acao (ver cleaner_core.py):
                     "dir_contents"  -> apaga tudo dentro da pasta (mantem a pasta)
                     "file_glob"     -> apaga so arquivos que casam com um padrao
                     "recycle_bin"   -> esvazia a lixeira
                     "wu_cache"      -> cache do Windows Update (para/inicia servicos)
                     "dism_cleanup"  -> limpeza do WinSxS via DISM
                     "windows_old"   -> remove C:\\Windows.old via DISM/rmdir
    paths         -> lista de caminhos (ja expandidos) usados pela acao
    pattern       -> padrao de arquivo (usado em "file_glob"), opcional
"""

import os
import winreg


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


WINDIR = _env("WINDIR", r"C:\Windows")
LOCALAPPDATA = _env("LOCALAPPDATA")
APPDATA = _env("APPDATA")
PROGRAMDATA = _env("PROGRAMDATA", r"C:\ProgramData")
USERPROFILE = _env("USERPROFILE")
SYSTEMDRIVE = _env("SYSTEMDRIVE", "C:") + "\\"
TEMP = _env("TEMP") or os.path.join(LOCALAPPDATA, "Temp")


def _exists(path: str) -> bool:
    try:
        return os.path.exists(path)
    except OSError:
        return False


def _read_reg_value(hive, subkey, value_name):
    try:
        with winreg.OpenKey(hive, subkey) as key:
            value, _ = winreg.QueryValueEx(key, value_name)
            return value
    except OSError:
        return None


def _detect_steam_path():
    path = _read_reg_value(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath")
    if path:
        return os.path.normpath(path)
    default = os.path.join(_env("PROGRAMFILES(X86)", r"C:\Program Files (x86)"), "Steam")
    return default if _exists(default) else None


def _detect_epic_installed():
    return _exists(os.path.join(LOCALAPPDATA, "EpicGamesLauncher"))


def _detect_discord_installed():
    return _exists(os.path.join(APPDATA, "discord"))


def _detect_spotify_installed():
    return _exists(os.path.join(LOCALAPPDATA, "Spotify"))


def _detect_nvidia_installed():
    return _exists(os.path.join(PROGRAMDATA, "NVIDIA Corporation")) or _exists(
        r"C:\Program Files\NVIDIA Corporation"
    )


def _detect_amd_installed():
    return _exists(os.path.join(LOCALAPPDATA, "AMD")) or _exists(r"C:\Program Files\AMD")


def _browser_cache_paths():
    """Retorna (nome_navegador, [pastas de cache]) so para navegadores detectados."""
    candidates = {
        "Google Chrome": [
            os.path.join(LOCALAPPDATA, r"Google\Chrome\User Data\Default\Cache"),
            os.path.join(LOCALAPPDATA, r"Google\Chrome\User Data\Default\Code Cache"),
            os.path.join(LOCALAPPDATA, r"Google\Chrome\User Data\Default\GPUCache"),
        ],
        "Microsoft Edge": [
            os.path.join(LOCALAPPDATA, r"Microsoft\Edge\User Data\Default\Cache"),
            os.path.join(LOCALAPPDATA, r"Microsoft\Edge\User Data\Default\Code Cache"),
            os.path.join(LOCALAPPDATA, r"Microsoft\Edge\User Data\Default\GPUCache"),
        ],
        "Mozilla Firefox": [
            os.path.join(LOCALAPPDATA, r"Mozilla\Firefox\Profiles"),
        ],
        "Brave": [
            os.path.join(LOCALAPPDATA, r"BraveSoftware\Brave-Browser\User Data\Default\Cache"),
            os.path.join(LOCALAPPDATA, r"BraveSoftware\Brave-Browser\User Data\Default\Code Cache"),
        ],
    }
    found = {}
    for name, paths in candidates.items():
        existing = [p for p in paths if _exists(p)]
        if existing:
            found[name] = existing
    return found


def get_categories():
    """Monta a lista de categorias, adaptando ao que esta de fato instalado."""
    cats = [
        dict(
            id="temp_user", group="basico",
            name="Temporarios do usuario",
            description="Arquivos temporarios gerados por programas para o usuario atual.",
            risk="safe", admin=False, default=True,
            kind="dir_contents", paths=[TEMP],
        ),
        dict(
            id="temp_windows", group="basico",
            name="Temporarios do Windows",
            description="Pasta de temporarios do sistema (C:\\Windows\\Temp).",
            risk="safe", admin=True, default=True,
            kind="dir_contents", paths=[os.path.join(WINDIR, "Temp")],
        ),
        dict(
            id="prefetch", group="basico",
            name="Prefetch",
            description="Cache de prelancamento do Windows. E regenerado automaticamente.",
            risk="safe", admin=True, default=True,
            kind="file_glob", paths=[os.path.join(WINDIR, "Prefetch")], pattern="*.pf",
        ),
        dict(
            id="thumbcache", group="basico",
            name="Cache de miniaturas e icones",
            description="Miniaturas de imagens/videos e icones em cache no Explorer.",
            risk="safe", admin=False, default=True,
            kind="file_glob",
            paths=[os.path.join(LOCALAPPDATA, r"Microsoft\Windows\Explorer")],
            pattern="*cache*.db",
        ),
        dict(
            id="recycle_bin", group="basico",
            name="Lixeira",
            description="Esvazia a Lixeira de todas as unidades.",
            risk="safe", admin=False, default=True,
            kind="recycle_bin", paths=[],
        ),
        dict(
            id="wu_cache", group="sistema",
            name="Cache do Windows Update",
            description="Instaladores baixados de atualizacoes ja aplicadas.",
            risk="safe", admin=True, default=True,
            kind="wu_cache",
            paths=[os.path.join(WINDIR, r"SoftwareDistribution\Download")],
        ),
        dict(
            id="delivery_optimization", group="sistema",
            name="Cache de Otimizacao de Entrega",
            description="Cache de download P2P de atualizacoes/apps da Microsoft.",
            risk="safe", admin=True, default=True,
            kind="dir_contents",
            paths=[os.path.join(PROGRAMDATA, r"Microsoft\Network\Downloader")],
        ),
        dict(
            id="error_reports", group="sistema",
            name="Relatorios de erro do Windows (WER)",
            description="Dumps e relatorios de falhas de programas.",
            risk="safe", admin=False, default=True,
            kind="dir_contents",
            paths=[
                os.path.join(LOCALAPPDATA, r"Microsoft\Windows\WER"),
                os.path.join(PROGRAMDATA, r"Microsoft\Windows\WER"),
            ],
        ),
        dict(
            id="crash_dumps", group="sistema",
            name="Crash dumps do usuario",
            description="Dumps de travamentos de aplicativos do usuario atual.",
            risk="safe", admin=False, default=True,
            kind="dir_contents", paths=[os.path.join(LOCALAPPDATA, "CrashDumps")],
        ),
        dict(
            id="minidump", group="sistema",
            name="Minidumps do sistema (BSOD)",
            description="Dumps de tela azul salvos pelo Windows.",
            risk="safe", admin=True, default=True,
            kind="dir_contents", paths=[os.path.join(WINDIR, "Minidump")],
        ),
        dict(
            id="recent_items", group="basico",
            name="Itens recentes / Jump Lists",
            description="Atalhos de arquivos e pastas acessados recentemente.",
            risk="safe", admin=False, default=True,
            kind="dir_contents",
            paths=[os.path.join(APPDATA, r"Microsoft\Windows\Recent")],
        ),
        dict(
            id="dx_shader_cache", group="jogos_drivers",
            name="Cache de shaders DirectX",
            description="Cache de compilacao de shaders (D3DSCache). Recriado ao usar jogos/apps 3D.",
            risk="safe", admin=False, default=True,
            kind="dir_contents", paths=[os.path.join(LOCALAPPDATA, "D3DSCache")],
        ),
        dict(
            id="cbs_logs", group="sistema",
            name="Logs do CBS (Component Based Servicing)",
            description="Logs internos de instalacao de atualizacoes do Windows.",
            risk="cuidado", admin=True, default=False,
            kind="dir_contents", paths=[os.path.join(WINDIR, r"Logs\CBS")],
        ),
        dict(
            id="package_cache", group="sistema",
            name="Package Cache (instaladores MSI)",
            description="Copia de instaladores usada para reparo/desinstalacao de programas. "
                         "Apagar pode impedir reparo/desinstalacao limpa de alguns apps.",
            risk="cuidado", admin=True, default=False,
            kind="dir_contents", paths=[os.path.join(PROGRAMDATA, "Package Cache")],
        ),
        dict(
            id="winsxs_cleanup", group="sistema",
            name="Componentes do Windows (WinSxS - backup de atualizacoes)",
            description="Remove versoes antigas de componentes guardadas para poder desinstalar "
                         "atualizacoes recentes. Depois de limpar, nao da mais pra reverter updates.",
            risk="cuidado", admin=True, default=False,
            kind="dism_cleanup", paths=[],
        ),
        dict(
            id="system_restore", group="sistema",
            name="Pontos de Restauracao do Sistema (reduzir espaco reservado)",
            description="Reduz o espaco maximo reservado pros pontos de restauracao, forcando o "
                         "Windows a apagar os pontos mais antigos. A Restauracao do Sistema continua "
                         "ativa, so com menos historico. Costuma liberar bastante espaco.",
            risk="cuidado", admin=True, default=False,
            kind="system_restore", paths=[],
        ),
        dict(
            id="windows_old", group="sistema",
            name="Windows.old e pastas de backup de upgrade",
            description="Copia da instalacao anterior do Windows apos upgrade, mais as pastas "
                         "temporarias que o instalador deixa para tras ($WINDOWS.~BT/$WINDOWS.~WS). "
                         "So existem por um tempo limitado. Depois de apagar nao da mais pra voltar "
                         "a versao anterior.",
            risk="cuidado", admin=True, default=False,
            kind="windows_old",
            paths=[
                os.path.join(SYSTEMDRIVE, "Windows.old"),
                os.path.join(SYSTEMDRIVE, "$WINDOWS.~BT"),
                os.path.join(SYSTEMDRIVE, "$WINDOWS.~WS"),
            ],
        ),
        dict(
            id="font_cache", group="sistema",
            name="Cache de fontes do Windows",
            description="Cache do servico de fontes (FontCache). E reconstruido automaticamente "
                         "na proxima vez que o Windows precisar renderizar fontes.",
            risk="safe", admin=True, default=True,
            kind="font_cache",
            paths=[os.path.join(WINDIR, r"ServiceProfiles\LocalService\AppData\Local\FontCache")],
        ),
    ]

    if _detect_nvidia_installed():
        cats.append(dict(
            id="nvidia_cache", group="jogos_drivers",
            name="Cache e instaladores residuais da NVIDIA (DXCache/GLCache/NV_Cache)",
            description="Cache de compilacao de shaders do driver NVIDIA (recriado automaticamente) "
                         "mais arquivos extraidos de instaladores de driver que ja foram aplicados "
                         "(pasta C:\\NVIDIA) e o cache de downloads do GeForce Experience.",
            risk="safe", admin=False, default=True,
            kind="dir_contents",
            paths=[
                os.path.join(LOCALAPPDATA, r"NVIDIA\DXCache"),
                os.path.join(LOCALAPPDATA, r"NVIDIA\GLCache"),
                os.path.join(PROGRAMDATA, r"NVIDIA Corporation\NV_Cache"),
                os.path.join(TEMP, "NVIDIA Corporation"),
                os.path.join(PROGRAMDATA, r"NVIDIA Corporation\Downloader"),
                os.path.join(SYSTEMDRIVE, "NVIDIA"),
            ],
        ))

    if _detect_amd_installed():
        cats.append(dict(
            id="amd_cache", group="jogos_drivers",
            name="Cache de drivers AMD (DxCache/DxcCache)",
            description="Cache de compilacao de shaders do driver AMD. Recriado automaticamente.",
            risk="safe", admin=False, default=True,
            kind="dir_contents",
            paths=[
                os.path.join(LOCALAPPDATA, r"AMD\DxCache"),
                os.path.join(LOCALAPPDATA, r"AMD\DxcCache"),
            ],
        ))

    steam_path = _detect_steam_path()
    if steam_path and _exists(steam_path):
        cats.append(dict(
            id="steam_cache", group="jogos_drivers",
            name="Cache do Steam (httpcache)",
            description="Cache de rede/loja do cliente Steam. Nao mexe em jogos instalados.",
            risk="safe", admin=False, default=True,
            kind="dir_contents",
            paths=[os.path.join(steam_path, r"appcache\httpcache")],
        ))

    if _detect_epic_installed():
        cats.append(dict(
            id="epic_cache", group="jogos_drivers",
            name="Cache do Epic Games Launcher",
            description="Cache web e logs do launcher da Epic. Nao mexe em jogos instalados.",
            risk="safe", admin=False, default=True,
            kind="dir_contents",
            paths=[
                os.path.join(LOCALAPPDATA, r"EpicGamesLauncher\Saved\webcache"),
                os.path.join(LOCALAPPDATA, r"EpicGamesLauncher\Saved\Logs"),
            ],
        ))

    if _detect_discord_installed():
        cats.append(dict(
            id="discord_cache", group="jogos_drivers",
            name="Cache do Discord",
            description="Cache web/imagens do Discord. Nao mexe em configuracoes ou historico de conversas.",
            risk="safe", admin=False, default=True,
            kind="dir_contents",
            paths=[
                os.path.join(APPDATA, r"discord\Cache"),
                os.path.join(APPDATA, r"discord\Code Cache"),
                os.path.join(APPDATA, r"discord\GPUCache"),
            ],
        ))

    if _detect_spotify_installed():
        cats.append(dict(
            id="spotify_cache", group="jogos_drivers",
            name="Cache do Spotify",
            description="Cache de musicas/dados offline do Spotify. Nao mexe na conta ou playlists.",
            risk="safe", admin=False, default=True,
            kind="dir_contents",
            paths=[
                os.path.join(LOCALAPPDATA, r"Spotify\Storage"),
                os.path.join(LOCALAPPDATA, r"Spotify\Data"),
            ],
        ))

    for browser_name, paths in _browser_cache_paths().items():
        safe_id = "browser_" + "".join(c.lower() for c in browser_name if c.isalnum())
        cats.append(dict(
            id=safe_id, group="navegadores",
            name=f"Cache do navegador: {browser_name}",
            description="Cache de paginas/imagens/scripts. Nao apaga senhas, historico ou favoritos.",
            risk="safe", admin=False, default=False,
            kind="dir_contents", paths=paths,
        ))

    return cats


def list_installed_programs():
    """Le o registro do Windows e retorna a lista de programas instalados (somente leitura/informativo)."""
    uninstall_keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    programs = []
    seen = set()

    for hive, subkey in uninstall_keys:
        try:
            with winreg.OpenKey(hive, subkey) as base_key:
                count = winreg.QueryInfoKey(base_key)[0]
                for i in range(count):
                    try:
                        sub_name = winreg.EnumKey(base_key, i)
                        with winreg.OpenKey(base_key, sub_name) as sub:
                            name = _reg_str(sub, "DisplayName")
                            if not name or name in seen:
                                continue
                            seen.add(name)
                            programs.append(dict(
                                name=name,
                                version=_reg_str(sub, "DisplayVersion") or "",
                                publisher=_reg_str(sub, "Publisher") or "",
                                size_kb=_reg_int(sub, "EstimatedSize") or 0,
                                install_date=_reg_str(sub, "InstallDate") or "",
                                uninstall_string=_reg_str(sub, "UninstallString") or "",
                                quiet_uninstall_string=_reg_str(sub, "QuietUninstallString") or "",
                                install_location=_reg_str(sub, "InstallLocation") or "",
                            ))
                    except OSError:
                        continue
        except OSError:
            continue

    programs.sort(key=lambda p: p["size_kb"], reverse=True)
    return programs


def _reg_str(key, name):
    try:
        value, _ = winreg.QueryValueEx(key, name)
        return str(value) if value is not None else None
    except OSError:
        return None


def _reg_int(key, name):
    try:
        value, _ = winreg.QueryValueEx(key, name)
        return int(value)
    except (OSError, ValueError, TypeError):
        return None
