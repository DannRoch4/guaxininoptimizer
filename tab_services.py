"""Mixin da aba Servicos (inicializacao + servicos do Windows) — extraido de gui.py."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

import cleaner_core as core
import i18n
import services_manager as svc_module
import tweaks as tweaks_module
from gui_shared import build_switch_card


class ServicesMixin:
    def _build_services_tab(self, parent, C):
        toolbar = tk.Frame(parent, bg=C["BG"])
        toolbar.pack(fill="x", pady=(8, 4))
        self._button(toolbar, i18n.t("btn_refresh_startup"), self.on_refresh_services).pack(side="left")
        self._button(toolbar, i18n.t("btn_revert_all"), self.on_revert_all).pack(side="left", padx=6)
        if not core.is_admin():
            tk.Label(toolbar, text=i18n.t("services_admin_note"), bg=C["BG"], fg=C["DANGER"],
                      font=("Segoe UI", 8, "bold")).pack(side="left", padx=10)

        self.services_canvas = tk.Canvas(parent, bg=C["BG"], highlightthickness=0)
        canvas = self.services_canvas
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        self.services_container = tk.Frame(canvas, bg=C["BG"])
        self.services_container.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        win_id = canvas.create_window((0, 0), window=self.services_container, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        self._render_services_container(C)
        if self._startup_cache is None or self._services_cache is None:
            self.on_refresh_services()

    def _render_services_container(self, C):
        for w in self.services_container.winfo_children():
            w.destroy()
        self.services_canvas.yview_moveto(0)

        tk.Label(self.services_container, text=i18n.t("startup_section_title"), bg=C["BG"], fg=C["FG"],
                  font=("Segoe UI Variable Display", 12, "bold")).pack(anchor="w", padx=10, pady=(6, 0))
        tk.Label(self.services_container, text=i18n.t("startup_section_note"), bg=C["BG"],
                  fg=C["FG_MUTED"], font=("Segoe UI", 8), wraplength=900, justify="left").pack(
            anchor="w", padx=10, pady=(0, 8))

        if self._startup_cache is None or self._services_cache is None:
            # primeira visita a aba (carregamento sob demanda) — sem isso ficava so o
            # titulo com um vazio enorme embaixo enquanto o scan de registro/WMI rodava.
            tk.Label(self.services_container, text=i18n.t("scanning"), bg=C["BG"], fg=C["FG_MUTED"],
                      font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=20)
            return

        for app in (self._startup_cache or []):
            self._add_startup_row(C, app)

        tk.Label(self.services_container, text=i18n.t("services_section_title"), bg=C["BG"], fg=C["FG"],
                  font=("Segoe UI Variable Display", 12, "bold")).pack(anchor="w", padx=10, pady=(16, 0))
        tk.Label(self.services_container, text=i18n.t("services_section_note"), bg=C["BG"],
                  fg=C["FG_MUTED"], font=("Segoe UI", 8), wraplength=900, justify="left").pack(
            anchor="w", padx=10, pady=(0, 8))

        for svc, status in (self._services_cache or []):
            self._add_service_row(C, svc, status)

    def _add_startup_row(self, C, app):
        hive_note = i18n.t("startup_hive_note", hive=app["hive"])
        _card, switch, var, _label = build_switch_card(
            self.services_container, C, app["name"], app["command"], hive_note, C["FG_MUTED"],
            app["enabled"], on_toggle=lambda v, a=app, sw=None: self._on_toggle_startup(a, v),
        )

    def _on_toggle_startup(self, app, new_value):
        ok = svc_module.set_startup_enabled(app, new_value, log_callback=self._log)
        if ok:
            app["enabled"] = new_value
            self._log(f"{'habilitado' if new_value else 'desabilitado'}: {app['name']} ({app['hive']})")

    def _add_service_row(self, C, svc, status):
        tag_text = i18n.t("risk_safe") if svc["risk"] == "safe" else i18n.t("risk_caution")
        tag_color = C["RISK_SAFE"] if svc["risk"] == "safe" else C["RISK_CAUTION"]
        status_text = i18n.t("status_running") if status["running"] else i18n.t("status_stopped")
        enabled_now = not status["disabled"]

        def _on_toggle(new_value, svc=svc):
            if not core.is_admin():
                messagebox.showwarning(i18n.t("brand_name"), i18n.t("services_admin_note"))
                self._render_services_container(self.C)
                return
            disable = not new_value
            ok = svc_module.set_service_disabled(svc["id"], disable, log_callback=self._log)
            if ok:
                self._log(f"servico {'desativado' if disable else 'reativado'}: {svc['display']}")
                new_status = svc_module.get_service_status(svc["id"])
                if new_status:
                    for i, (s, _st) in enumerate(self._services_cache):
                        if s["id"] == svc["id"]:
                            self._services_cache[i] = (s, new_status)
                            break
                self._render_services_container(self.C)

        build_switch_card(self.services_container, C, svc["display"], svc["desc"], tag_text, tag_color,
                            enabled_now, on_toggle=_on_toggle, right_text=status_text)

    def on_refresh_services(self):
        threading.Thread(target=self._scan_services_worker, daemon=True).start()

    def _scan_services_worker(self):
        startup_apps = svc_module.get_startup_apps()
        services = []
        for svc in svc_module.CURATED_SERVICES:
            status = svc_module.get_service_status(svc["id"])
            if status is not None:
                services.append((svc, status))
        self._startup_cache = startup_apps
        self._services_cache = services
        self.root.after(0, self._render_services_container, self.C)

    def on_revert_all(self):
        if not messagebox.askyesno(i18n.t("revert_confirm_title"), i18n.t("revert_confirm_body")):
            return
        n = svc_module.revert_all(log_callback=self._log) + tweaks_module.revert_all(log_callback=self._log)
        self._startup_cache = None
        self._services_cache = None
        self._privacy_cache = None
        self._gamer_cache = None
        self._rebuild_ui()
        # mostra o popup DEPOIS do rebuild, senao o rebuild destruiria o dialogo (Toplevel e
        # filho da janela principal, e o rebuild apaga todos os filhos)
        if n:
            self._show_success(i18n.t("success_revert_title"), i18n.t("revert_done", n=n))
        else:
            messagebox.showinfo(i18n.t("brand_name"), i18n.t("revert_none"))
