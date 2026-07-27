"""Ferramentas de rede: flush de DNS, troca de servidor DNS, ping/traceroute, IP publico
e reset da pilha de rede."""

import ctypes
import re
import subprocess
import urllib.request

# Nomes e IPs conferidos com a documentacao oficial de cada provedor (jul/2026). Cloudflare
# nao tem uma variante "sem anuncios" propria — quem bloqueia anuncio de verdade e o AdGuard;
# o que a Cloudflare oferece de extra e bloqueio de malware e, numa segunda opcao, +conteudo adulto.
DNS_PRESETS = {
    "automatic": ("Automatico (DHCP)", []),
    "cloudflare": ("Cloudflare", ["1.1.1.1", "1.0.0.1"]),
    "cloudflare_malware": ("Cloudflare Familia — sem malware", ["1.1.1.2", "1.0.0.2"]),
    "cloudflare_family": ("Cloudflare Familia — sem malware e +18", ["1.1.1.3", "1.0.0.3"]),
    "google": ("Google", ["8.8.8.8", "8.8.4.4"]),
    "quad9": ("Quad9", ["9.9.9.9", "149.112.112.112"]),
    "adguard": ("AdGuard — sem anuncios", ["94.140.14.14", "94.140.15.15"]),
    "adguard_family": ("AdGuard Familia — sem anuncios e +18", ["94.140.14.15", "94.140.15.16"]),
    "opendns_family": ("OpenDNS FamilyShield — +18", ["208.67.222.123", "208.67.220.123"]),
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


def get_adapter_details(adapter_name):
    """IP local, gateway e MAC do adaptador ativo, pra mostrar num card informativo."""
    if not adapter_name:
        return None
    try:
        script = (
            f"$c = Get-NetIPConfiguration -InterfaceAlias '{adapter_name}'; "
            f"$a = Get-NetAdapter -InterfaceAlias '{adapter_name}'; "
            "[PSCustomObject]@{"
            "IP=($c.IPv4Address.IPAddress -join ','); "
            "Gateway=($c.IPv4DefaultGateway.NextHop -join ','); "
            "MAC=$a.MacAddress"
            "} | ConvertTo-Json -Compress"
        )
        result = _run_ps(script)
        raw = result.stdout.strip()
        if not raw:
            return None
        import json
        data = json.loads(raw)
        return dict(ip=data.get("IP") or "", gateway=data.get("Gateway") or "", mac=data.get("MAC") or "")
    except Exception:
        return None


def get_public_ip():
    """IP publico visto pela internet (pede pra um servico externo — precisa de conexao)."""
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as resp:
            ip = resp.read().decode("ascii", errors="ignore").strip()
            return ip or None
    except Exception:
        return None


def traceroute_host_stream(host, line_callback, max_hops=15):
    """Roda tracert e chama line_callback(str) a cada linha que sai, em tempo real —
    esperar o comando inteiro terminar (pode levar quase um minuto com saltos que nao
    respondem) deixava a tela parada sem nenhum feedback, parecendo travada."""
    try:
        cp = ctypes.windll.kernel32.GetOEMCP()
        encoding = f"cp{cp}"
    except Exception:
        encoding = "utf-8"
    try:
        proc = subprocess.Popen(
            ["tracert", "-h", str(max_hops), "-w", "800", host],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as exc:
        line_callback(f"erro ao executar tracert: {exc}")
        return False
    try:
        for raw_line in iter(proc.stdout.readline, b""):
            text = raw_line.decode(encoding, errors="replace").strip()
            if text:
                line_callback(text)
        proc.wait(timeout=10)
        return proc.returncode == 0
    except Exception as exc:
        line_callback(f"erro ao executar tracert: {exc}")
        return False
    finally:
        if proc.poll() is None:
            proc.kill()


def reset_network_stack(log_callback=None):
    """Reseta Winsock e a pilha TCP/IP pro estado padrao — resolve muitos problemas de rede
    'do nada', mas apaga configuracoes de rede customizadas (IP fixo, VPN, proxy) e exige
    reiniciar o PC pra valer. Por isso fica marcado como 'cuidado' na interface."""
    ok = True
    for cmd in (["netsh", "winsock", "reset"], ["netsh", "int", "ip", "reset"]):
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=30,
                                      creationflags=subprocess.CREATE_NO_WINDOW)
            if log_callback:
                log_callback("  " + _decode_console_output(result.stdout).strip().splitlines()[0]
                               if result.stdout else f"  {' '.join(cmd)}: ok")
            if result.returncode != 0:
                ok = False
        except Exception as exc:
            ok = False
            if log_callback:
                log_callback(f"  erro em '{' '.join(cmd)}': {exc}")
    return ok


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
