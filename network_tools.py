"""Ferramentas de rede: flush de DNS, troca de servidor DNS e teste de ping."""

import ctypes
import re
import subprocess

DNS_PRESETS = {
    "automatic": ("Automatico (DHCP)", []),
    "cloudflare": ("Cloudflare", ["1.1.1.1", "1.0.0.1"]),
    "google": ("Google", ["8.8.8.8", "8.8.4.4"]),
    "quad9": ("Quad9", ["9.9.9.9", "149.112.112.112"]),
}


def _decode_console_output(data: bytes) -> str:
    """Ferramentas de console nativas (ipconfig etc) escrevem na code page OEM do console,
    nao em UTF-8/ANSI — decodificar com o encoding padrao corrompe acentos (ex: virava
    'Configura‡Æo' em vez de 'Configuracao'). GetOEMCP() da a code page certa."""
    try:
        cp = ctypes.windll.kernel32.GetOEMCP()
        return data.decode(f"cp{cp}", errors="replace")
    except Exception:
        return data.decode("utf-8", errors="replace")


def _run_ps(script, timeout=30):
    return subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, text=True, timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW,
    )


def flush_dns(log_callback=None):
    try:
        result = subprocess.run(["ipconfig", "/flushdns"], capture_output=True,
                                  timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
        if log_callback:
            log_callback(_decode_console_output(result.stdout).strip())
        return result.returncode == 0
    except Exception as exc:
        if log_callback:
            log_callback(f"  erro: {exc}")
        return False


def get_active_adapter_name():
    try:
        result = _run_ps(
            "(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null } | "
            "Select-Object -First 1 -ExpandProperty InterfaceAlias)"
        )
        name = result.stdout.strip()
        return name or None
    except Exception:
        return None


def get_current_dns(adapter_name):
    try:
        result = _run_ps(
            f"(Get-DnsClientServerAddress -InterfaceAlias '{adapter_name}' -AddressFamily IPv4 "
            "| Select-Object -ExpandProperty ServerAddresses) -join ','"
        )
        raw = result.stdout.strip()
        return [s for s in raw.split(",") if s]
    except Exception:
        return []


def set_dns_preset(adapter_name, preset_key, log_callback=None):
    servers = DNS_PRESETS.get(preset_key, (None, []))[1]
    try:
        if servers:
            joined = ",".join(f"'{s}'" for s in servers)
            script = f"Set-DnsClientServerAddress -InterfaceAlias '{adapter_name}' -ServerAddresses ({joined})"
        else:
            script = f"Set-DnsClientServerAddress -InterfaceAlias '{adapter_name}' -ResetServerAddresses"
        result = _run_ps(script)
        if result.returncode == 0:
            return True
        if log_callback:
            log_callback(f"  erro: {result.stderr.strip()[:200]}")
        return False
    except Exception as exc:
        if log_callback:
            log_callback(f"  erro: {exc}")
        return False


_PING_LINE = re.compile(r"tempo[=<]?(\d+)ms|time[=<]?(\d+)ms", re.IGNORECASE)


def ping_host(host, count=4):
    """Faz um ping simples e retorna (sucesso, resumo_texto)."""
    try:
        result = subprocess.run(["ping", "-n", str(count), host], capture_output=True, text=True,
                                  timeout=count * 3 + 5, creationflags=subprocess.CREATE_NO_WINDOW)
        output = result.stdout
        times = []
        for line in output.splitlines():
            m = _PING_LINE.search(line)
            if m:
                times.append(int(m.group(1) or m.group(2)))
        if times:
            avg = sum(times) / len(times)
            summary = f"{host}: {len(times)}/{count} respostas — media {avg:.0f} ms (min {min(times)} / max {max(times)})"
            return True, summary
        return False, f"{host}: sem resposta (host inacessivel ou bloqueando ping)."
    except Exception as exc:
        return False, f"{host}: erro ao executar ping ({exc})"
