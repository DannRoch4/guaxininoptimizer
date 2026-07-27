"""Mixin das abas genericas de tweaks (Privacidade & IA / Modo Gamer) — extraido de gui.py."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

import cleaner_core as core
import i18n
import tweaks as tweaks_module
from gui_shared import build_switch_card


class TweaksMixin:
    # ---------- abas genericas de tweaks (Privacidade & IA / Modo Gamer) ----------
    def _build_generic_tweaks_tab(self, parent, C, tweak_list, cache_attr, title, note):
        toolbar = tk.Frame(parent, bg=C["BG"])
        toolbar.pack(fill="x", pady=(8, 4))
        self._button(toolbar, i18n.t("btn_refresh_startup"),
                       lambda: self._scan_tweaks_async(tweak_list, cache_attr)).pack(side="left")
        self._button(toolbar, i18n.t("btn_revert_all"), self.on_revert_all).pack(side="left", padx=6)
        if not core.is_admin():
            tk.Label(toolbar, text=i18n.t("services_admin_note"), bg=C["BG"], fg=C["DANGER"],
                      font=("Segoe UI", 8, "bold")).pack(side="left", padx=10)

        canvas = tk.Canvas(parent, bg=C["BG"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        container = tk.Frame(canvas, bg=C["BG"])
        container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        win_id = canvas.create_window((0, 0), window=container, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        self._tweak_ui[cache_attr] = dict(container=container, canvas=canvas, title=title, note=note,
                                            tweaks=tweak_list, colors=C)
        self._render_tweaks_container(cache_attr)
        if getattr(self, cache_attr) is None:
            self._scan_tweaks_async(tweak_list, cache_attr)

    def _render_tweaks_container(self, cache_attr):
        info = self._tweak_ui[cache_attr]
        container, C = info["container"], info["colors"]
        for w in container.winfo_children():
            w.destroy()
        # reseta a rolagem pro topo (senao a tela pode ficar "presa" numa posicao vazia
        # depois que o conteudo e reconstruido, se o usuario tiver rolado pra baixo antes)
        info["canvas"].yview_moveto(0)

        tk.Label(container, text=info["title"], bg=C["BG"], fg=C["FG"],
                  font=("Segoe UI Variable Display", 12, "bold")).pack(anchor="w", padx=10, pady=(6, 0))
        tk.Label(container, text=info["note"], bg=C["BG"], fg=C["FG_MUTED"], font=("Segoe UI", 8),
                  wraplength=900, justify="left").pack(anchor="w", padx=10, pady=(0, 8))

        for tweak, state in (getattr(self, cache_attr) or []):
            self._add_tweak_row(C, cache_attr, tweak, state)

    def _add_tweak_row(self, C, cache_attr, tweak, state):
        tag_text = i18n.t("risk_safe") if tweak["risk"] == "safe" else i18n.t("risk_caution")
        tag_color = C["RISK_SAFE"] if tweak["risk"] == "safe" else C["RISK_CAUTION"]

        def _on_toggle(new_value, tweak=tweak, cache_attr=cache_attr):
            if tweak.get("hive") == "HKLM" and not core.is_admin():
                messagebox.showwarning(i18n.t("brand_name"), i18n.t("services_admin_note"))
                self._render_tweaks_container(cache_attr)
                return
            ok = tweaks_module.set_tweak_state(tweak, new_value, log_callback=self._log)
            # nao confia no "ok" sozinho — relê o valor real do registro pra garantir que o
            # switch sempre mostra o estado de verdade, nunca so o que foi tentado.
            real_state = tweaks_module.get_tweak_state(tweak)
            if ok and real_state == new_value:
                self._log(f"{'aplicado' if new_value else 'revertido'}: {tweak['display']}")
            else:
                self._log(f"aviso: '{tweak['display']}' pode nao ter aplicado — mostrando estado real do sistema.")
            cache = getattr(self, cache_attr)
            for i, (t, _s) in enumerate(cache):
                if t["id"] == tweak["id"]:
                    cache[i] = (t, real_state)
                    break
            self._render_tweaks_container(cache_attr)

        build_switch_card(self._tweak_ui[cache_attr]["container"], C, tweak["display"], tweak["desc"],
                            tag_text, tag_color, state, on_toggle=_on_toggle)

    def _scan_tweaks_async(self, tweak_list, cache_attr):
        threading.Thread(target=self._scan_tweaks_worker, args=(tweak_list, cache_attr), daemon=True).start()

    def _scan_tweaks_worker(self, tweak_list, cache_attr):
        result = [(t, tweaks_module.get_tweak_state(t)) for t in tweak_list]
        setattr(self, cache_attr, result)
        self.root.after(0, self._render_tweaks_container, cache_attr)
