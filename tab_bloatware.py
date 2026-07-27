"""Mixin da aba Bloatware — extraido de gui.py."""

import threading
import tkinter as tk
from tkinter import ttk

import bloatware as bloatware_module
import i18n
from gui_shared import build_switch_card


class BloatwareMixin:
    # ---------- aba de bloatware ----------
    def _build_bloatware_tab(self, parent, C):
        toolbar = tk.Frame(parent, bg=C["BG"])
        toolbar.pack(fill="x", pady=(8, 4))
        self._button(toolbar, i18n.t("btn_refresh_startup"), self.on_refresh_bloatware).pack(side="left")

        self.bloatware_canvas = tk.Canvas(parent, bg=C["BG"], highlightthickness=0)
        canvas = self.bloatware_canvas
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        self.bloatware_container = tk.Frame(canvas, bg=C["BG"])
        self.bloatware_container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        win_id = canvas.create_window((0, 0), window=self.bloatware_container, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        self._render_bloatware_container(C)
        if self._bloatware_cache is None:
            self.on_refresh_bloatware()

    def _render_bloatware_container(self, C):
        for w in self.bloatware_container.winfo_children():
            w.destroy()
        self.bloatware_canvas.yview_moveto(0)
        tk.Label(self.bloatware_container, text=i18n.t("bloatware_section_title"), bg=C["BG"], fg=C["FG"],
                  font=("Segoe UI Variable Display", 12, "bold")).pack(anchor="w", padx=10, pady=(6, 0))
        tk.Label(self.bloatware_container, text=i18n.t("bloatware_section_note"), bg=C["BG"],
                  fg=C["FG_MUTED"], font=("Segoe UI", 8), wraplength=900, justify="left").pack(
            anchor="w", padx=10, pady=(0, 8))

        if self._bloatware_cache is None:
            # sem isso, a primeira visita a aba (agora que ela carrega sob demanda) mostrava
            # so o titulo com um vazio enorme embaixo enquanto o scan rodava — parecia quebrado.
            tk.Label(self.bloatware_container, text=i18n.t("scanning"), bg=C["BG"], fg=C["FG_MUTED"],
                      font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=20)
            return

        for app, installed in (self._bloatware_cache or []):
            status_text = i18n.t("bloatware_installed") if installed else i18n.t("bloatware_removed")
            tag_text = i18n.t("risk_safe") if app["risk"] == "safe" else i18n.t("risk_caution")
            tag_color = C["RISK_SAFE"] if app["risk"] == "safe" else C["RISK_CAUTION"]

            def _on_toggle(new_value, app=app):
                if new_value:
                    ok = bloatware_module.reinstall_package(app["id"], log_callback=self._log)
                    self._log(f"tentativa de reinstalar: {app['display']}")
                else:
                    ok = bloatware_module.remove_package(app["id"], log_callback=self._log)
                    if ok:
                        self._log(f"removido: {app['display']}")
                for i, (a, _inst) in enumerate(self._bloatware_cache):
                    if a["id"] == app["id"]:
                        self._bloatware_cache[i] = (a, bloatware_module.is_installed(app["id"]))
                        break
                self._render_bloatware_container(self.C)

            build_switch_card(self.bloatware_container, C, app["display"], app["desc"], tag_text, tag_color,
                                installed, on_toggle=_on_toggle, right_text=status_text)

    def on_refresh_bloatware(self):
        threading.Thread(target=self._scan_bloatware_worker, daemon=True).start()

    def _scan_bloatware_worker(self):
        # uma unica chamada de PowerShell pra listar tudo instalado, em vez de uma chamada
        # isolada por item (47x mais lento) — ver bloatware.list_installed_appx_names().
        installed_names = bloatware_module.list_installed_appx_names()
        result = [(app, bloatware_module.is_installed(app["id"], installed_names))
                   for app in bloatware_module.CURATED_BLOATWARE]
        self._bloatware_cache = result
        self.root.after(0, self._render_bloatware_container, self.C)
