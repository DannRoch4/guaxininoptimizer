"""
Tweaks reversiveis de registro: Privacidade & IA e Modo Gamer.

Regra de ouro: nunca desinstala nada, so muda valores de registro (ou, no caso
do HPET, uma opcao de boot via bcdedit). O valor original e sempre gravado no
revert_log.py antes da primeira alteracao, e pode ser restaurado com um clique.

Convencao: no switch da GUI, "ligado" = tweak aplicado/otimizado.
"""

import re
import subprocess
import winreg

import revert_log

HIVES = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}


def _read_dword(hive_name, path, name):
    try:
        with winreg.OpenKey(HIVES[hive_name], path) as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value
    except OSError:
        return None


def _write_dword(hive_name, path, name, value):
    key = winreg.CreateKeyEx(HIVES[hive_name], path, 0, winreg.KEY_ALL_ACCESS)
    with key:
        winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)


def _read_string(hive_name, path, name):
    try:
        with winreg.OpenKey(HIVES[hive_name], path) as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value
    except OSError:
        return None


def _write_string(hive_name, path, name, value):
    key = winreg.CreateKeyEx(HIVES[hive_name], path, 0, winreg.KEY_ALL_ACCESS)
    with key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)


def _delete_dword(hive_name, path, name):
    try:
        key = winreg.OpenKey(HIVES[hive_name], path, 0, winreg.KEY_ALL_ACCESS)
    except OSError:
        return
    with key:
        try:
            winreg.DeleteValue(key, name)
        except OSError:
            pass


def _key_id(tweak):
    return f"{tweak['hive']}::{tweak['path']}::{tweak['value_name']}"


# ---------- motor generico (cobre a maioria dos tweaks) ----------

def get_tweak_state(tweak):
    if "get_state" in tweak:
        return tweak["get_state"]()
    current = _read_dword(tweak["hive"], tweak["path"], tweak["value_name"])
    if current is None:
        return False
    return current == tweak["on_value"]


def set_tweak_state(tweak, apply_tweak: bool, log_callback=None):
    if "set_state" in tweak:
        return tweak["set_state"](apply_tweak, log_callback)

    current = _read_dword(tweak["hive"], tweak["path"], tweak["value_name"])
    revert_log.record_if_new("registry_tweaks", _key_id(tweak), current)
    try:
        if apply_tweak:
            _write_dword(tweak["hive"], tweak["path"], tweak["value_name"], tweak["on_value"])
        else:
            _delete_dword(tweak["hive"], tweak["path"], tweak["value_name"])
        return True
    except OSError as exc:
        if log_callback:
            log_callback(f"  erro ao aplicar '{tweak['display']}': {exc}")
        return False


# ---------- Privacidade & IA ----------

PRIVACY_AI_TWEAKS = [
    dict(id="disable_copilot", display="Desativar Copilot", risk="safe",
          desc="Remove o icone e a funcao do Copilot no Windows 11.",
          hive="HKLM", path=r"SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot",
          value_name="TurnOffWindowsCopilot", on_value=1),
    dict(id="disable_recall", display="Desativar Recall (capturas de tela por IA)", risk="safe",
          desc="Impede o Windows de tirar 'fotos' periodicas da tela usadas pelo recurso Recall.",
          hive="HKLM", path=r"SOFTWARE\Policies\Microsoft\Windows\WindowsAI",
          value_name="DisableAIDataAnalysis", on_value=1),
    dict(id="disable_cortana", display="Desativar Cortana", risk="safe",
          desc="Desativa a assistente Cortana (recurso legado, praticamente em desuso).",
          hive="HKLM", path=r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
          value_name="AllowCortana", on_value=0),
    dict(id="reduce_telemetry", display="Reduzir telemetria do Windows", risk="safe",
          desc="Define a telemetria para o minimo permitido pela sua edicao do Windows. "
               "(No Windows Home/Pro nao da pra zerar 100% — isso so e possivel em Enterprise/Educacao.)",
          hive="HKLM", path=r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
          value_name="AllowTelemetry", on_value=1),
    dict(id="disable_office_telemetry", display="Desativar telemetria do Office", risk="safe",
          desc="Impede o Microsoft Office (2016+) de enviar dados de uso e diagnostico. "
               "Nao tem efeito se voce nao usa Office.",
          hive="HKCU", path=r"SOFTWARE\Policies\Microsoft\office\common\clienttelemetry",
          value_name="DisableTelemetry", on_value=1),
    dict(id="disable_edge_sidebar", display="Desativar barra lateral Copilot/Discover do Edge", risk="cuidado",
          desc="Remove o icone lateral do Copilot e do Discover no Microsoft Edge.",
          hive="HKLM", path=r"SOFTWARE\Policies\Microsoft\Edge",
          value_name="HubsSidebarEnabled", on_value=0),
    dict(id="disable_start_ads", display="Remover sugestoes/anuncios do Menu Iniciar", risk="safe",
          desc="Remove apps sugeridos e dicas patrocinadas no Menu Iniciar e na tela de bloqueio.",
          hive="HKCU", path=r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
          value_name="SubscribedContent-338388Enabled", on_value=0),
    dict(id="disable_widgets", display="Desativar Widgets na barra de tarefas", risk="safe",
          desc="Remove o icone de Widgets / Noticias e Interesses da barra de tarefas.",
          hive="HKLM", path=r"SOFTWARE\Policies\Microsoft\Dsh",
          value_name="AllowNewsAndInterests", on_value=0),
]


# ---------- Modo Gamer ----------

def _find_active_interface_path():
    base = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as base_key:
            n = winreg.QueryInfoKey(base_key)[0]
            for i in range(n):
                sub = winreg.EnumKey(base_key, i)
                sub_path = base + "\\" + sub
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_path) as sub_key:
                        for value_name in ("DhcpIPAddress", "IPAddress"):
                            try:
                                val, _ = winreg.QueryValueEx(sub_key, value_name)
                                if isinstance(val, str) and val not in ("", "0.0.0.0"):
                                    return sub_path
                                if isinstance(val, (list, tuple)) and val and val[0] not in ("", "0.0.0.0"):
                                    return sub_path
                            except OSError:
                                continue
                except OSError:
                    continue
    except OSError:
        pass
    return None


def _nagle_get_state():
    path = _find_active_interface_path()
    if not path:
        return False
    return _read_dword("HKLM", path, "TcpAckFrequency") == 1


def _nagle_set_state(apply_tweak, log_callback=None):
    path = _find_active_interface_path()
    if not path:
        if log_callback:
            log_callback("  nao foi possivel identificar o adaptador de rede ativo.")
        return False
    ok = True
    for value_name in ("TcpAckFrequency", "TCPNoDelay"):
        key_id = f"HKLM::{path}::{value_name}"
        current = _read_dword("HKLM", path, value_name)
        revert_log.record_if_new("registry_tweaks", key_id, current)
        try:
            if apply_tweak:
                _write_dword("HKLM", path, value_name, 1)
            else:
                _delete_dword("HKLM", path, value_name)
        except OSError as exc:
            ok = False
            if log_callback:
                log_callback(f"  erro ao alterar {value_name}: {exc}")
    return ok


def _hpet_raw_state():
    """True=desativado explicitamente, False=ativado explicitamente, None=padrao (auto)."""
    try:
        result = subprocess.run(["bcdedit", "/enum"], capture_output=True, text=True, timeout=10,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        return None
    for line in result.stdout.splitlines():
        if "useplatformclock" in line.lower():
            return "no" in line.lower()
    return None


def _hpet_get_state():
    return _hpet_raw_state() is True


def _hpet_set_state(apply_tweak, log_callback=None):
    raw = _hpet_raw_state()
    original = "unset" if raw is None else ("no" if raw is True else "yes")
    revert_log.record_if_new("registry_tweaks", "special::hpet", original)
    try:
        if apply_tweak:
            subprocess.run(["bcdedit", "/set", "useplatformclock", "false"], capture_output=True,
                             timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            subprocess.run(["bcdedit", "/deletevalue", "useplatformclock"], capture_output=True,
                             timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
        return True
    except Exception as exc:
        if log_callback:
            log_callback(f"  erro no bcdedit: {exc}")
        return False


def _mouse_precision_get_state():
    speed = _read_string("HKCU", r"Control Panel\Mouse", "MouseSpeed")
    t1 = _read_string("HKCU", r"Control Panel\Mouse", "MouseThreshold1")
    t2 = _read_string("HKCU", r"Control Panel\Mouse", "MouseThreshold2")
    return speed == "0" and t1 == "0" and t2 == "0"


_MOUSE_PRECISION_DEFAULTS = {"MouseSpeed": "1", "MouseThreshold1": "6", "MouseThreshold2": "10"}


def _mouse_precision_set_state(apply_tweak, log_callback=None):
    path = r"Control Panel\Mouse"
    ok = True
    for name, default in _MOUSE_PRECISION_DEFAULTS.items():
        key_id = f"HKCU::{path}::{name}"
        current = _read_string("HKCU", path, name)
        revert_log.record_if_new("registry_tweaks", key_id, current)
        try:
            _write_string("HKCU", path, name, "0" if apply_tweak else default)
        except OSError as exc:
            ok = False
            if log_callback:
                log_callback(f"  erro ao alterar {name}: {exc}")
    return ok


_MMCSS_GAMES_PATH = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games"
_MMCSS_GAMES_VALUES = {
    "GPU Priority": ("dword", 8),
    "Priority": ("dword", 6),
    "Scheduling Category": ("string", "High"),
    "SFIO Priority": ("string", "High"),
}


def _mmcss_games_get_state():
    for name, (kind, target) in _MMCSS_GAMES_VALUES.items():
        current = _read_dword("HKLM", _MMCSS_GAMES_PATH, name) if kind == "dword" \
            else _read_string("HKLM", _MMCSS_GAMES_PATH, name)
        if current != target:
            return False
    return True


def _mmcss_games_set_state(apply_tweak, log_callback=None):
    ok = True
    for name, (kind, target) in _MMCSS_GAMES_VALUES.items():
        key_id = f"HKLM::{_MMCSS_GAMES_PATH}::{name}"
        current = _read_dword("HKLM", _MMCSS_GAMES_PATH, name) if kind == "dword" \
            else _read_string("HKLM", _MMCSS_GAMES_PATH, name)
        revert_log.record_if_new("registry_tweaks", key_id, current)
        try:
            if apply_tweak:
                if kind == "dword":
                    _write_dword("HKLM", _MMCSS_GAMES_PATH, name, target)
                else:
                    _write_string("HKLM", _MMCSS_GAMES_PATH, name, target)
            else:
                _delete_dword("HKLM", _MMCSS_GAMES_PATH, name)
        except OSError as exc:
            ok = False
            if log_callback:
                log_callback(f"  erro ao alterar '{name}': {exc}")
    return ok


ULTIMATE_PERFORMANCE_TEMPLATE_GUID = "e9a42b02-d5df-448d-aa00-03f14749eb61"
BALANCED_SCHEME_GUID = "381b4222-f694-41f0-9685-ff5bb260df2e"


def _powercfg(args, timeout=20):
    try:
        return subprocess.run(["powercfg"] + args, capture_output=True, text=True, timeout=timeout,
                                creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        return None


def _power_active_scheme_guid():
    result = _powercfg(["/getactivescheme"])
    if not result or result.returncode != 0:
        return None
    m = re.search(r"([0-9a-fA-F-]{36})", result.stdout)
    return m.group(1) if m else None


def _power_find_ultimate_guid():
    result = _powercfg(["/list"])
    if not result or result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        low = line.lower()
        is_en = "ultimate" in low and "performance" in low
        is_pt = "desempenho" in low and ("maximo" in low or "máximo" in low)
        is_es = "rendimiento" in low and ("maximo" in low or "máximo" in low or "extremo" in low)
        if is_en or is_pt or is_es:
            m = re.search(r"([0-9a-fA-F-]{36})", line)
            if m:
                return m.group(1)
    return None


def _power_plan_get_state():
    active = _power_active_scheme_guid()
    ultimate = _power_find_ultimate_guid()
    return bool(active and ultimate and active.lower() == ultimate.lower())


def _power_plan_set_state(apply_tweak, log_callback=None):
    original = _power_active_scheme_guid()
    revert_log.record_if_new("registry_tweaks", "special::power_plan", original or BALANCED_SCHEME_GUID)
    if apply_tweak:
        guid = _power_find_ultimate_guid()
        if not guid:
            result = _powercfg(["/duplicatescheme", ULTIMATE_PERFORMANCE_TEMPLATE_GUID])
            if result and result.returncode == 0:
                m = re.search(r"([0-9a-fA-F-]{36})", result.stdout)
                guid = m.group(1) if m else None
        if not guid:
            if log_callback:
                log_callback("  nao foi possivel criar/achar o plano Desempenho Maximo.")
            return False
        result = _powercfg(["/setactive", guid])
        return bool(result and result.returncode == 0)
    else:
        result = _powercfg(["/setactive", BALANCED_SCHEME_GUID])
        return bool(result and result.returncode == 0)


GAMER_TWEAKS = [
    dict(id="disable_gamedvr", display="Desativar Game Bar / Game DVR", risk="safe",
          desc="Impede a gravacao em segundo plano do Xbox Game Bar, que consome CPU/GPU/disco.",
          hive="HKCU", path=r"System\GameConfigStore", value_name="GameDVR_Enabled", on_value=0),
    dict(id="disable_fse_opt", display="Desativar Otimizacoes de Tela Cheia (global)", risk="cuidado",
          desc="Desliga a camada de compatibilidade de tela cheia do Windows. Pode reduzir input lag "
               "em jogos DX9/DX11 mais antigos, mas pode causar tearing em outros — teste antes de decidir.",
          hive="HKCU", path=r"System\GameConfigStore",
          value_name="GameDVR_DXGIHonorFSEWindowsCompatible", on_value=1),
    dict(id="enable_hags", display="Ativar GPU Scheduling por Hardware (HAGS)", risk="cuidado",
          desc="Deixa a GPU gerenciar sua propria fila de agendamento, podendo reduzir latencia em "
               "alguns jogos. Exige GPU/driver com suporte (NVIDIA serie 10+/AMD recente) e reiniciar o PC.",
          hive="HKLM", path=r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers",
          value_name="HwSchMode", on_value=2),
    dict(id="disable_nagle", display="Desativar Algoritmo de Nagle (rede)", risk="cuidado",
          desc="Reduz o atraso de pacotes pequenos de rede no adaptador ativo — tweak classico de "
               "jogos competitivos. Efeito real varia bastante conforme sua internet e roteador.",
          hive="HKLM", get_state=_nagle_get_state, set_state=_nagle_set_state),
    dict(id="disable_hpet", display="Desativar HPET (High Precision Event Timer)", risk="cuidado",
          desc="Alguns jogos ganham FPS mais estavel com o HPET desativado, outros pioram. "
               "Precisa reiniciar o PC para o efeito valer. Reversivel a qualquer momento.",
          hive="HKLM", get_state=_hpet_get_state, set_state=_hpet_set_state),
    dict(id="enable_utc_time", display="Usar UTC no relogio do sistema (dual boot Linux)", risk="cuidado",
          desc="Corrige o relogio ficar errado ao alternar entre Windows e Linux em dual boot. "
               "So ative se voce realmente usa dual boot — em PC so-Windows nao faz diferenca.",
          hive="HKLM", path=r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation",
          value_name="RealTimeIsUniversal", on_value=1),
    dict(id="power_plan_ultimate", display="Plano de energia Desempenho Maximo", risk="cuidado",
          desc="Ativa o plano de energia 'Desempenho Maximo', escondido por padrao no Windows. "
               "Remove varios limitadores de economia de energia — mais performance sustentada, "
               "mais consumo de energia (evite em notebook na bateria).",
          hive="HKLM", get_state=_power_plan_get_state, set_state=_power_plan_set_state),
    dict(id="mmcss_games", display="Priorizar jogos no agendador do Windows (MMCSS)", risk="safe",
          desc="Configura o MMCSS (Multimedia Class Scheduler) pra dar prioridade de CPU/GPU mais "
               "alta a jogos em primeiro plano, reduzindo engasgos.",
          hive="HKLM", get_state=_mmcss_games_get_state, set_state=_mmcss_games_set_state),
    dict(id="network_throttling_off", display="Remover limite de rede do Windows (Network Throttling)",
          risk="safe",
          desc="Remove o limite que o Windows aplica no throughput de rede pra multimidia/jogos "
               "(MMCSS Network Throttling Index). Ajuda em jogos online e streaming.",
          hive="HKLM", path=r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
          value_name="NetworkThrottlingIndex", on_value=0xffffffff),
    dict(id="win32_priority_foreground", display="Priorizar app em primeiro plano (o jogo)", risk="cuidado",
          desc="Ajusta o Windows pra dar fatias de tempo de CPU maiores e fixas pro programa em "
               "primeiro plano (o jogo que voce esta jogando), em vez de dividir igual com o fundo.",
          hive="HKLM", path=r"SYSTEM\CurrentControlSet\Control\PriorityControl",
          value_name="Win32PrioritySeparation", on_value=38),
    dict(id="power_throttling_off", display="Desativar Power Throttling (limite de CPU por economia)",
          risk="cuidado",
          desc="Impede o Windows de reduzir a performance de processos pra economizar energia. "
               "Pode ajudar em jogos/apps pesados, mas reduz autonomia de bateria em notebook.",
          hive="HKLM", path=r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling",
          value_name="PowerThrottlingOff", on_value=1),
    dict(id="mouse_precision_off", display="Desativar precisao de ponteiro do mouse (mira sem aceleracao)",
          risk="safe",
          desc="Remove a aceleracao do ponteiro do mouse do Windows, deixando o movimento 1:1 — "
               "tweak classico pra jogos competitivos de mira (FPS). So afeta o seu usuario.",
          hive="HKCU", get_state=_mouse_precision_get_state, set_state=_mouse_precision_set_state),
]


# ---------- reversao ----------

def revert_all(log_callback=None):
    log_data = revert_log.load()
    restored = 0

    for key_id, original in list(log_data.get("registry_tweaks", {}).items()):
        try:
            if key_id == "special::hpet":
                if original == "unset":
                    subprocess.run(["bcdedit", "/deletevalue", "useplatformclock"], capture_output=True,
                                     timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    subprocess.run(["bcdedit", "/set", "useplatformclock", original], capture_output=True,
                                     timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
            elif key_id == "special::power_plan":
                _powercfg(["/setactive", original])
            else:
                hive, path, name = key_id.split("::", 2)
                if original is None:
                    _delete_dword(hive, path, name)
                elif isinstance(original, str):
                    _write_string(hive, path, name, original)
                else:
                    _write_dword(hive, path, name, original)
            restored += 1
            if log_callback:
                log_callback(f"  revertido (tweak): {key_id}")
        except Exception as exc:
            if log_callback:
                log_callback(f"  falha ao reverter '{key_id}': {exc}")

    log_data["registry_tweaks"] = {}
    revert_log.save(log_data)
    return restored
