"""Mixin da aba Limpeza (+ agendamento automatico) — extraido de gui.py."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

import cleaner_core as core
import i18n
import scheduler
import widgets
from gui_shared import CategoryRow


class CleanMixin:
    def _build_clean_tab(self, parent, C):
        self._page_title(parent, C, i18n.t("tab_clean"))

        toolbar = tk.Frame(parent, bg=C["BG"])
        toolbar.pack(fill="x", pady=(0, 8))
        self._button(toolbar, i18n.t("btn_scan"), self.on_scan).pack(side="left")
        self._button(toolbar, i18n.t("btn_select_safe"), self.on_select_safe).pack(side="left", padx=6)
        self._button(toolbar, i18n.t("btn_select_all"), self.on_select_all).pack(side="left")
        self._button(toolbar, i18n.t("btn_select_none"), self.on_select_none).pack(side="left", padx=6)
        self.clean_btn = self._button(toolbar, i18n.t("btn_clean"), self.on_clean, primary=True)
        self.clean_btn.pack(side="right")
        self.total_label = tk.Label(toolbar, text="", bg=C["BG"], fg=C["ACCENT"],
                                      font=("Segoe UI", 10, "bold"))
        self.total_label.pack(side="right", padx=14)

        self._build_scheduler_card(parent, C)

        canvas = tk.Canvas(parent, bg=C["BG"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        self.rows_container = tk.Frame(canvas, bg=C["BG"])

        self.rows_container.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        win_id = canvas.create_window((0, 0), window=self.rows_container, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        # so enquanto o mouse esta sobre esta aba — "bind_all" permanente vazava o scroll
        # pra outras abas mesmo depois de trocar de tela.
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        self.rows = {}
        for c in self.categories:
            row = CategoryRow(self.rows_container, c, self.cat_state[c["id"]], C,
                                on_toggle=self._update_total)
            self.rows[c["id"]] = row

    # ---------- agendamento automatico ----------
    def _build_scheduler_card(self, parent, C):
        card = widgets.RoundedFrame(parent, bg_root=C["BG"], card_bg=C["BG_CARD"], radius=10)
        card.pack(fill="x", padx=10, pady=(6, 10))
        inner = card.inner

        tk.Label(inner, text=i18n.t("scheduler_section_title"), bg=C["BG_CARD"], fg=C["FG"],
                  font=("Segoe UI Variable Display", 11, "bold")).grid(
            row=0, column=0, columnspan=6, sticky="w", padx=14, pady=(12, 2))
        tk.Label(inner, text=i18n.t("scheduler_section_note"), bg=C["BG_CARD"], fg=C["FG_MUTED"],
                  font=("Segoe UI", 8), wraplength=760, justify="left").grid(
            row=1, column=0, columnspan=6, sticky="w", padx=14, pady=(0, 10))

        existing = scheduler.get_task_status()
        self.scheduler_enable_var = tk.BooleanVar(value=bool(existing))

        widgets.ToggleSwitch(inner, self.scheduler_enable_var, bg_root=C["BG_CARD"],
                               on_color=C["RISK_SAFE"], off_color=C["SELECT_COLOR"]).grid(
            row=2, column=0, padx=(14, 6), pady=(0, 12))
        tk.Label(inner, text=i18n.t("scheduler_enable_label"), bg=C["BG_CARD"], fg=C["FG"],
                  font=("Segoe UI", 9)).grid(row=2, column=1, sticky="w", pady=(0, 12))

        tk.Label(inner, text=i18n.t("scheduler_day_label"), bg=C["BG_CARD"], fg=C["FG_MUTED"],
                  font=("Segoe UI", 8)).grid(row=2, column=2, padx=(16, 4), pady=(0, 12))
        # o codigo interno (pro schtasks) fica sempre em ingles — so o texto mostrado muda
        # de idioma. Testado: schtasks aceita SUN/MON/... independente do idioma do Windows.
        day_codes = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
        self._scheduler_day_labels = {i18n.t(f"day_{code.lower()}"): code for code in day_codes}
        day_display_values = list(self._scheduler_day_labels.keys())
        self.scheduler_day_display_var = tk.StringVar(value=day_display_values[0])
        ttk.Combobox(inner, textvariable=self.scheduler_day_display_var, values=day_display_values,
                      width=10, state="readonly").grid(row=2, column=3, pady=(0, 12))

        tk.Label(inner, text=i18n.t("scheduler_time_label"), bg=C["BG_CARD"], fg=C["FG_MUTED"],
                  font=("Segoe UI", 8)).grid(row=2, column=4, padx=(16, 4), pady=(0, 12))
        self.scheduler_time_var = tk.StringVar(value="10:00")
        tk.Entry(inner, textvariable=self.scheduler_time_var, width=7, bg=C["BG_PANEL"], fg=C["FG"],
                  insertbackground=C["FG"], relief="flat", font=("Segoe UI", 9)).grid(
            row=2, column=5, pady=(0, 12))

        self._button(inner, i18n.t("btn_scheduler_save"), self.on_save_schedule).grid(
            row=2, column=6, padx=14, pady=(0, 12))

        self.scheduler_status_label = tk.Label(inner, text="", bg=C["BG_CARD"], fg=C["FG_MUTED"],
                                                 font=("Segoe UI", 8, "bold"))
        self.scheduler_status_label.grid(row=3, column=0, columnspan=7, sticky="w", padx=14, pady=(0, 12))
        self._refresh_scheduler_status()

    def _refresh_scheduler_status(self):
        status = scheduler.get_task_status()
        if status:
            self.scheduler_status_label.config(
                text=i18n.t("scheduler_status_active", next_run=status.get("next_run") or "?"))
        else:
            self.scheduler_status_label.config(text=i18n.t("scheduler_status_inactive"))

    def on_save_schedule(self):
        enable = self.scheduler_enable_var.get()
        if enable:
            day_label = self.scheduler_day_display_var.get()
            day = self._scheduler_day_labels.get(day_label, "SUN")
            time_str = self.scheduler_time_var.get().strip() or "10:00"
            ok = scheduler.create_weekly_task(day=day, time_str=time_str, log_callback=self._log)
            if ok:
                self._log(i18n.t("scheduler_saved"))
            else:
                messagebox.showerror(i18n.t("brand_name"), i18n.t("scheduler_error"))
        else:
            scheduler.remove_task(log_callback=self._log)
            self._log(i18n.t("scheduler_removed"))
        self._refresh_scheduler_status()

    # ---------- selecao / total ----------
    def _update_total(self):
        if getattr(self, "_scanning_active", False):
            return
        selected_states = [s for s in self.cat_state.values() if s["selected"]]
        n_selected = len(selected_states)
        if n_selected == 0:
            self.total_label.config(text=i18n.t("total_selected", n=0, size=core.human_size(0)))
            return
        if any(not s["scanned"] for s in selected_states):
            self.total_label.config(text=i18n.t("pending_analysis", n=n_selected))
            return
        total = sum(s["size"] or 0 for s in selected_states)
        self.total_label.config(text=i18n.t("total_selected", n=n_selected, size=core.human_size(total)))

    def on_select_safe(self):
        for c in self.categories:
            self.rows[c["id"]].set_selected(c["risk"] == "safe")
        self._update_total()

    def on_select_all(self):
        for c in self.categories:
            self.rows[c["id"]].set_selected(True)
        self._update_total()

    def on_select_none(self):
        for c in self.categories:
            self.rows[c["id"]].set_selected(False)
        self._update_total()

    # ---------- acoes ----------
    def on_scan(self):
        if self.worker_running:
            return
        self.worker_running = True
        self._scanning_active = True
        self.progress.config(mode="determinate", maximum=max(len(self.categories), 1))
        self.progress["value"] = 0
        self._log(i18n.t("scan_start_log"))
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        total = len(self.categories)
        running_total = 0
        for i, c in enumerate(self.categories):
            cid = c["id"]
            self.msg_queue.put(("scan_start", cid))
            try:
                size, count = core.scan_category(c)
            except Exception as exc:
                self.msg_queue.put(("log", i18n.t("scan_error_log", name=c["name"], error=exc)))
                size, count = 0, 0
            if size:
                running_total += size
            self.msg_queue.put(("scan_result", (cid, size, count)))
            self.msg_queue.put(("scan_progress", (i + 1, total, i18n.cat_text(c, "name"), running_total)))
        self.msg_queue.put(("log", i18n.t("scan_done_log")))
        self.msg_queue.put(("done", None))

    def on_clean(self):
        if self.worker_running:
            return
        selected = [c for c in self.categories if self.cat_state[c["id"]]["selected"]]
        if not selected:
            messagebox.showwarning(i18n.t("no_selection_title"), i18n.t("no_selection_body"))
            return

        unscanned = [c for c in selected if not self.cat_state[c["id"]]["scanned"]]
        if unscanned:
            if not messagebox.askyesno(i18n.t("brand_name"), i18n.t("confirm_unscanned_body")):
                return

        total_estimate = sum(self.cat_state[c["id"]]["size"] or 0 for c in selected
                               if self.cat_state[c["id"]]["scanned"])
        risky = [c for c in selected if c["risk"] == "cuidado"]
        body = i18n.t("confirm_clean_body", n=len(selected), size=core.human_size(total_estimate))
        if risky:
            body += i18n.t("confirm_clean_risky_header") + "\n".join(
                f"  • {i18n.cat_text(c, 'name')}" for c in risky
            )
        body += i18n.t("confirm_clean_continue")

        if not messagebox.askyesno(i18n.t("confirm_clean_title"), body):
            return

        self.disk_before = core.get_disk_usage()
        self._set_busy(True)
        self._log(i18n.t("log_free_before", size=core.human_size(self.disk_before["free"])))
        self._log(i18n.t("log_cleaning_start", n=len(selected), size=core.human_size(total_estimate)))
        threading.Thread(target=self._clean_worker, args=(selected,), daemon=True).start()

    def _clean_worker(self, selected_categories):
        total_freed = 0
        for c in selected_categories:
            name = i18n.cat_text(c, "name")
            self.msg_queue.put(("log", i18n.t("log_cleaning_item", name=name)))
            try:
                freed = core.clean_category(c, log=lambda t: self.msg_queue.put(("log", t)))
                if freed and freed > 0:
                    total_freed += freed
                    self.msg_queue.put(("log", i18n.t("log_freed", size=core.human_size(freed))))
                elif freed == -1:
                    self.msg_queue.put(("log", i18n.t("log_freed_unknown")))
                else:
                    self.msg_queue.put(("log", i18n.t("log_nothing")))
            except Exception as exc:
                self.msg_queue.put(("log", i18n.t("log_error", error=exc)))
            self.msg_queue.put(("scan_start", c["id"]))
            try:
                size, count = core.scan_category(c)
                self.msg_queue.put(("scan_result", (c["id"], size, count)))
            except Exception:
                pass

        disk_after = core.get_disk_usage()
        gained = disk_after["free"] - self.disk_before["free"]
        summary = "\n".join([
            i18n.t("summary_title"), "",
            i18n.t("summary_before", size=core.human_size(self.disk_before["free"])),
            i18n.t("summary_after", size=core.human_size(disk_after["free"])),
            i18n.t("summary_gain", size=core.human_size(gained)), "",
            i18n.t("summary_estimate", size=core.human_size(total_freed)),
        ])
        self.msg_queue.put(("log", "----"))
        self.msg_queue.put(("log", summary.replace("\n\n", "\n")))
        self.msg_queue.put(("done", summary))
