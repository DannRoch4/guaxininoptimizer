"""Coleta informacoes do sistema (CPU, RAM, GPU, SO, discos) para o Dashboard."""

import ctypes
import os
import platform
import shutil
import string
import subprocess

import psutil


def _run_ps(script, timeout=15):
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_os_info():
    caption = _run_ps("(Get-CimInstance Win32_OperatingSystem).Caption") or platform.system()
    build = _run_ps("(Get-CimInstance Win32_OperatingSystem).BuildNumber") or platform.version()
    arch = "64-bit" if platform.machine().endswith("64") else platform.machine()
    return dict(caption=caption, build=build, arch=arch)


def get_cpu_info():
    name = _run_ps("(Get-CimInstance Win32_Processor).Name") or platform.processor() or "CPU desconhecida"
    freq = psutil.cpu_freq()
    return dict(
        name=name.strip(),
        cores=psutil.cpu_count(logical=False) or 0,
        threads=psutil.cpu_count(logical=True) or 0,
        freq_mhz=round(freq.current) if freq else 0,
        usage_percent=psutil.cpu_percent(interval=0.2),
    )


def get_cpu_live():
    """So os valores que mudam a cada instante (uso/clock), sem chamar PowerShell —
    pra poder ser chamada em loop de tempo real (a cada 2s) sem travar nada."""
    freq = psutil.cpu_freq()
    return dict(
        freq_mhz=round(freq.current) if freq else 0,
        usage_percent=psutil.cpu_percent(interval=0.2),
    )


def get_ram_info():
    vm = psutil.virtual_memory()
    return dict(total=vm.total, used=vm.used, percent=vm.percent)


def get_gpu_info():
    name = _run_ps("(Get-CimInstance Win32_VideoController | Select-Object -First 1 -ExpandProperty Name)")
    return dict(name=name.strip() or "Nao detectada")


def get_gpu_stats():
    """Temperatura/uso/clock/consumo reais via nvidia-smi. So funciona com GPU NVIDIA com
    driver instalado — em qualquer outro caso (AMD/Intel/sem nvidia-smi) retorna None,
    e quem chama deve mostrar so o nome da GPU sem esses detalhes."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu,power.draw,clocks.gr",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        parts = [p.strip() for p in result.stdout.strip().split(",")]
        if len(parts) < 4:
            return None
        return dict(
            temp_c=float(parts[0]),
            usage_percent=float(parts[1]),
            power_w=float(parts[2]),
            clock_mhz=float(parts[3]),
        )
    except (FileNotFoundError, subprocess.SubprocessError, ValueError, OSError):
        return None


def get_live_usage():
    """So dados que dao pra ler instantaneamente (sem chamar PowerShell), pra atualizar em tempo real."""
    vm = psutil.virtual_memory()
    return dict(
        cpu_percent=psutil.cpu_percent(interval=None),
        ram_used=vm.used,
        ram_total=vm.total,
        ram_percent=vm.percent,
    )


_DRIVE_FIXED = 3


def _is_fixed_drive(drive):
    """So discos internos fixos (HD/SSD) — sem isso, unidade de CD/DVD sem midia, cartao
    de memoria ou drive de rede mapeado apareciam e somiam entre uma checagem e outra
    (device not ready / timeout), fazendo o card de Armazenamento piscar/sumir no Dashboard."""
    try:
        return ctypes.windll.kernel32.GetDriveTypeW(drive) == _DRIVE_FIXED
    except Exception:
        return True


def get_disks_info():
    disks = []
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if not os.path.exists(drive) or not _is_fixed_drive(drive):
            continue
        try:
            usage = shutil.disk_usage(drive)
            disks.append(dict(letter=f"{letter}:", total=usage.total, used=usage.used, free=usage.free))
        except OSError:
            continue
    return disks
