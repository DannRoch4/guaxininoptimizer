"""Agendamento de limpeza automatica via Agendador de Tarefas do Windows (schtasks).

Cria uma tarefa que roda o proprio Guaxinim Optimizer com a flag --auto (limpeza
silenciosa, so categorias seguras — ver main.py:run_auto). Nao inventa nenhum
mecanismo proprio de agendamento: usa o agendador nativo do Windows, que e
confiavel e sobrevive a reinicializacoes."""

import re
import subprocess
import sys

TASK_NAME = "GuaxinimOptimizer_LimpezaAutomatica"


def _get_run_command():
    """Descobre o comando certo pra rodar o --auto, tanto no .exe quanto no script."""
    if getattr(sys, "frozen", False):
        # Rodando como .exe empacotado (PyInstaller): o proprio executavel aceita --auto
        return f'"{sys.executable}" --auto'
    # Rodando como script Python (modo desenvolvimento)
    main_script = sys.argv[0]
    return f'"{sys.executable}" "{main_script}" --auto'


def is_task_scheduling_supported():
    try:
        result = subprocess.run(["schtasks", "/?"], capture_output=True, timeout=10,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
        return result.returncode == 0
    except Exception:
        return False


def get_task_status():
    """Retorna dict(exists, next_run) ou None se a tarefa nao existir."""
    try:
        result = subprocess.run(
            ["schtasks", "/query", "/tn", TASK_NAME, "/fo", "LIST"],
            capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            return None
        # Nao confia no texto do rotulo (varia por idioma do Windows e pode vir com
        # acentuacao corrompida no console) — procura direto por um padrao de data,
        # que e a mesma coisa em qualquer idioma.
        next_run = ""
        date_pattern = re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}.*\d{1,2}:\d{2}(:\d{2})?")
        for line in result.stdout.splitlines():
            m = date_pattern.search(line)
            if m and "status" not in line.lower():
                next_run = m.group(0).strip()
                break
        return dict(exists=True, next_run=next_run)
    except Exception:
        return None


def create_weekly_task(day="SUN", time_str="10:00", log_callback=None):
    """Cria (ou substitui) a tarefa semanal. day: MON/TUE/WED/THU/FRI/SAT/SUN."""
    command = _get_run_command()
    try:
        result = subprocess.run(
            ["schtasks", "/create", "/tn", TASK_NAME, "/tr", command, "/sc", "WEEKLY",
             "/d", day, "/st", time_str, "/rl", "HIGHEST", "/f"],
            capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return True
        if log_callback:
            log_callback(f"  erro ao criar tarefa agendada: {result.stderr.strip() or result.stdout.strip()}")
        return False
    except Exception as exc:
        if log_callback:
            log_callback(f"  erro ao criar tarefa agendada: {exc}")
        return False


def remove_task(log_callback=None):
    try:
        result = subprocess.run(
            ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
            capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.returncode == 0
    except Exception as exc:
        if log_callback:
            log_callback(f"  erro ao remover tarefa agendada: {exc}")
        return False
