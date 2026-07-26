"""
Gerenciamento reversivel de:
  - Programas de inicializacao (chaves Run do registro) - mesmo mecanismo que o
    Gerenciador de Tarefas do Windows usa (nao apaga a entrada, so marca como
    aprovada/reprovada via StartupApproved).
  - Servicos do Windows selecionados (lista curada) - so ALTERA o tipo de
    inicializacao (Automatico/Manual/Desativado), nunca desinstala nada.

Toda alteracao feita por aqui e registrada num log local para poder reverter
com um clique.
"""

import subprocess
import winreg

import revert_log

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APPROVED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"

ENABLED_BYTE = 0x02
DISABLED_BYTE = 0x03


# ---------- programas de inicializacao ----------

def get_startup_apps():
    """Le HKCU e HKLM \\...\\Run e o estado aprovado/reprovado de cada entrada."""
    apps = []
    for hive, hive_name in ((winreg.HKEY_CURRENT_USER, "HKCU"), (winreg.HKEY_LOCAL_MACHINE, "HKLM")):
        try:
            with winreg.OpenKey(hive, RUN_KEY) as run_key:
                count = winreg.QueryInfoKey(run_key)[1]
                for i in range(count):
                    name, command, _ = winreg.EnumValue(run_key, i)
                    enabled = _is_startup_enabled(hive, hive_name, name)
                    apps.append(dict(name=name, command=command, hive=hive_name, enabled=enabled))
        except OSError:
            continue
    apps.sort(key=lambda a: a["name"].lower())
    return apps


def _is_startup_enabled(hive, hive_name, value_name):
    try:
        with winreg.OpenKey(hive, APPROVED_KEY) as key:
            data, _ = winreg.QueryValueEx(key, value_name)
            if data and len(data) > 0:
                return data[0] != DISABLED_BYTE
    except OSError:
        pass
    return True  # nunca mexido = habilitado (comportamento padrao do Windows)


def set_startup_enabled(app, enabled: bool, log_callback=None):
    """Marca a entrada de inicializacao como aprovada/reprovada (nao apaga o valor Run)."""
    hive = winreg.HKEY_CURRENT_USER if app["hive"] == "HKCU" else winreg.HKEY_LOCAL_MACHINE
    try:
        key = winreg.CreateKeyEx(hive, APPROVED_KEY, 0, winreg.KEY_ALL_ACCESS)
    except OSError as exc:
        if log_callback:
            log_callback(f"  sem permissao para alterar '{app['name']}' ({app['hive']}): {exc}")
        return False

    with key:
        try:
            current, _ = winreg.QueryValueEx(key, app["name"])
            current = bytearray(current)
        except OSError:
            current = bytearray(12)

        state_key = f"{app['hive']}::{app['name']}"
        revert_log.record_if_new("startup", state_key, bytes(current).hex())

        current[0] = ENABLED_BYTE if enabled else DISABLED_BYTE
        try:
            winreg.SetValueEx(key, app["name"], 0, winreg.REG_BINARY, bytes(current))
            return True
        except OSError as exc:
            if log_callback:
                log_callback(f"  erro ao alterar '{app['name']}': {exc}")
            return False


# ---------- servicos do Windows (lista curada) ----------

# risk: "safe" (a grande maioria dos usuarios nao usa essa funcao) ou
#       "cuidado" (depende muito do seu uso, leia a descricao antes)
CURATED_SERVICES = [
    dict(id="Fax", display="Fax", risk="safe",
          desc="Envio/recebimento de fax por modem. Praticamente ninguem usa isso hoje."),
    dict(id="bthserv", display="Suporte a Bluetooth", risk="cuidado",
          desc="Necessario para usar mouse/teclado/fones Bluetooth. So desative se seu PC nao tem Bluetooth."),
    dict(id="XblAuthManager", display="Xbox Live - Autenticacao", risk="cuidado",
          desc="Login de conta Xbox/Game Bar. Desative se nao usa Xbox app, Game Pass ou Game Bar."),
    dict(id="XblGameSave", display="Xbox Live - Salvamento na nuvem", risk="cuidado",
          desc="Sincroniza saves de jogos com a nuvem Xbox. Desative se nao usa esse recurso."),
    dict(id="XboxNetApiSvc", display="Xbox Live - Rede", risk="cuidado",
          desc="Recursos de rede do Xbox (multiplayer via app Xbox). Desative se nao usa o app Xbox."),
    dict(id="XboxGipSvc", display="Xbox Accessory Management", risk="safe",
          desc="Gerencia acessorios Xbox (controles). Seguro desativar se nao usa controle Xbox."),
    dict(id="DiagTrack", display="Telemetria (Connected User Experiences)", risk="safe",
          desc="Coleta e envia dados de diagnostico/uso para a Microsoft. Desativar aumenta privacidade "
               "e nao quebra nenhuma funcao do dia a dia."),
    dict(id="dmwappushsvc", display="WAP Push Message Routing", risk="safe",
          desc="Servico de mensageria ligado a telemetria/provisionamento. Seguro desativar no uso domestico."),
    dict(id="RetailDemo", display="Retail Demo Service", risk="safe",
          desc="Modo demonstracao usado em lojas. Inutil fora de vitrines de loja."),
    dict(id="WMPNetworkSvc", display="Compartilhamento de midia do Windows Media Player", risk="safe",
          desc="Compartilha sua biblioteca de midia na rede local. Desative se nao usa isso."),
    dict(id="RemoteRegistry", display="Registro Remoto", risk="safe",
          desc="Permite editar o registro deste PC remotamente por outro PC. Ja vem desativado por "
               "padrao na maioria dos sistemas; manter desativado e mais seguro."),
    dict(id="MapsBroker", display="Gerenciador de Mapas Baixados", risk="safe",
          desc="Atualiza mapas offline do app Mapas. Desative se nao usa mapas offline."),
    dict(id="PhoneSvc", display="Servico de Telefone (Vincular ao Celular)", risk="cuidado",
          desc="Usado pelo recurso 'Seu Celular / Phone Link'. Desative so se nao usa esse recurso."),
    dict(id="SysMain", display="SysMain (Superfetch)", risk="cuidado",
          desc="Pre-carrega apps usados com frequencia na memoria. Em HDD costuma ajudar; em SSD/NVMe "
               "muita gente desativa para reduzir uso de disco em segundo plano. Avalie seu caso."),
    dict(id="WSearch", display="Windows Search (indexacao)", risk="cuidado",
          desc="Indexa arquivos para a busca do Windows ser instantanea. Desativar deixa a busca mais "
               "lenta (varre pasta por pasta). So desative se dificilmente usa a busca do Windows."),
]


def get_service_status(service_id):
    """Le o tipo de inicializacao (Start) e se o servico esta rodando, via registro + sc query."""
    key_path = rf"SYSTEM\CurrentControlSet\Services\{service_id}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            start_value, _ = winreg.QueryValueEx(key, "Start")
    except OSError:
        return None  # servico nao existe nesta maquina (ex: nao instalado)

    running = False
    try:
        result = subprocess.run(["sc", "query", service_id], capture_output=True, text=True,
                                  timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
        running = "RUNNING" in result.stdout
    except Exception:
        pass

    # Start: 2=Automatico, 3=Manual, 4=Desativado
    disabled = start_value == 4
    return dict(start_value=start_value, disabled=disabled, running=running)


def set_service_disabled(service_id, disable: bool, log_callback=None):
    """Desativa (Start=4) ou restaura Manual (Start=3) um servico. Sempre registra o valor original."""
    key_path = rf"SYSTEM\CurrentControlSet\Services\{service_id}"
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_ALL_ACCESS)
    except OSError as exc:
        if log_callback:
            log_callback(f"  sem permissao para alterar servico '{service_id}': {exc}")
        return False

    with key:
        try:
            current_start, _ = winreg.QueryValueEx(key, "Start")
        except OSError:
            current_start = 3

        revert_log.record_if_new("services", service_id, current_start)

        new_start = 4 if disable else 3
        try:
            winreg.SetValueEx(key, "Start", 0, winreg.REG_DWORD, new_start)
        except OSError as exc:
            if log_callback:
                log_callback(f"  erro ao alterar servico '{service_id}': {exc}")
            return False

    try:
        if disable:
            subprocess.run(["sc", "stop", service_id], capture_output=True, timeout=15,
                             creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        pass
    return True


def revert_all(log_callback=None):
    """Restaura tudo que o Guaxinim ja alterou (startup + servicos) para o estado original."""
    log_data = revert_log.load()
    restored = 0

    for state_key, hex_value in list(log_data.get("startup", {}).items()):
        hive_name, _, value_name = state_key.partition("::")
        hive = winreg.HKEY_CURRENT_USER if hive_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE
        try:
            with winreg.OpenKey(hive, APPROVED_KEY, 0, winreg.KEY_ALL_ACCESS) as key:
                winreg.SetValueEx(key, value_name, 0, winreg.REG_BINARY, bytes.fromhex(hex_value))
            restored += 1
            if log_callback:
                log_callback(f"  revertido (inicializacao): {value_name}")
        except OSError as exc:
            if log_callback:
                log_callback(f"  falha ao reverter '{value_name}': {exc}")

    for service_id, original_start in list(log_data.get("services", {}).items()):
        key_path = rf"SYSTEM\CurrentControlSet\Services\{service_id}"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
                winreg.SetValueEx(key, "Start", 0, winreg.REG_DWORD, original_start)
            if original_start != 4:
                try:
                    subprocess.run(["sc", "start", service_id], capture_output=True, timeout=15,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
                except Exception:
                    pass
            restored += 1
            if log_callback:
                log_callback(f"  revertido (servico): {service_id}")
        except OSError as exc:
            if log_callback:
                log_callback(f"  falha ao reverter servico '{service_id}': {exc}")

    log_data["startup"] = {}
    log_data["services"] = {}
    revert_log.save(log_data)
    return restored
