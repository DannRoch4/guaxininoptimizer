"""Ponto de entrada do Guaxinim Optimizer.

Uso normal:        python main.py
Modo silencioso:    python main.py --auto   (limpa apenas categorias seguras, sem GUI,
                                              pensado para agendar no Agendador de Tarefas do Windows)
"""

import sys
from datetime import datetime

import categories as cat_module
import cleaner_core as core


def _fix_dpi_awareness():
    """Sem isso, o Windows escala a janela via bitmap em telas com escala >100%,
    deixando tudo borrado e desalinhado. Precisa rodar antes de criar qualquer janela Tk."""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI Aware
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def run_auto():
    """Limpa as categorias 'seguras' sem abrir GUI e grava um log em arquivo."""
    log_path = "guaxinim_auto.log"

    def log(msg):
        line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        print(line)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    log("=== Guaxinim Optimizer --auto: iniciando limpeza silenciosa ===")
    if not core.is_admin():
        log("AVISO: rodando sem administrador — itens que exigem admin serao pulados.")

    disk_before = core.get_disk_usage()
    log(f"Espaco livre antes: {core.human_size(disk_before['free'])}")

    cats = [c for c in cat_module.get_categories() if c["risk"] == "safe" and c["default"]]
    total_freed = 0
    for c in cats:
        if c["admin"] and not core.is_admin():
            log(f"pulado (precisa admin): {c['name']}")
            continue
        try:
            freed = core.clean_category(c, log=log)
            if freed and freed > 0:
                total_freed += freed
                log(f"{c['name']}: liberado {core.human_size(freed)}")
            else:
                log(f"{c['name']}: nada a limpar")
        except Exception as exc:
            log(f"{c['name']}: erro - {exc}")

    disk_after = core.get_disk_usage()
    gained = disk_after["free"] - disk_before["free"]
    log(f"Espaco livre depois: {core.human_size(disk_after['free'])}")
    log(f"Ganho real de espaco: {core.human_size(gained)}")
    log("=== Guaxinim Optimizer --auto: concluido ===")


def main():
    if "--auto" in sys.argv:
        run_auto()
        return
    if not core.is_admin() and core.relaunch_as_admin():
        # a instancia elevada ja esta subindo (ou o usuario ainda vai decidir no UAC) —
        # essa instancia sem privilegios encerra aqui pra nao rodar em duplicidade.
        return
    _fix_dpi_awareness()
    import gui
    gui.run()


if __name__ == "__main__":
    main()
