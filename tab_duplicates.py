"""Mixin da aba Duplicados — extraido de gui.py."""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cleaner_core as core
import duplicates as duplicates_module
import i18n
import widgets


class DuplicatesMixin:
    # ---------- aba de duplicados ----------
    def _build_duplicates_tab(self, parent, C):
        self._duplicate_folders = []  # list of (label, path, BooleanVar)
        self._duplicate_groups = []   # ultimo resultado da busca

        header = tk.Frame(parent, bg=C["BG"])
        header.pack(fill="x", pady=(4, 4))
        tk.Label(header, text=i18n.t("duplicates_section_title"), bg=C["BG"], fg=C["FG"],
                  font=("Segoe UI Variable Display", 12, "bold")).pack(anchor="w")
        tk.Label(header, text=i18n.t("duplicates_section_note"), bg=C["BG"], fg=C["FG_MUTED"],
                  font=("Segoe UI", 8), wraplength=900, justify="left").pack(anchor="w", pady=(2, 8))

        folders_card = widgets.RoundedFrame(parent, bg_root=C["BG"], card_bg=C["BG_CARD"], radius=10)
        folders_card.pack(fill="x", pady=(0, 8))
        self._duplicates_folders_inner = folders_card.inner
        tk.Label(self._duplicates_folders_inner, text=i18n.t("duplicates_folders_label"),
                  bg=C["BG_CARD"], fg=C["FG"], font=("Segoe UI", 9, "bold")).pack(
            anchor="w", padx=14, pady=(12, 4))
        self._duplicates_checks_row = tk.Frame(self._duplicates_folders_inner, bg=C["BG_CARD"])
        self._duplicates_checks_row.pack(fill="x", padx=14, pady=(0, 12))

        for label, path in duplicates_module.get_common_folders():
            self._add_duplicate_folder(label, path, C)

        toolbar = tk.Frame(parent, bg=C["BG"])
        toolbar.pack(fill="x", pady=(0, 8))
        self._button(toolbar, i18n.t("btn_add_folder"), self.on_add_duplicate_folder).pack(side="left")
        self._button(toolbar, i18n.t("btn_search_duplicates"), self.on_search_duplicates,
                       primary=True).pack(side="left", padx=6)
        self.duplicates_cancel_btn = self._button(toolbar, i18n.t("btn_cancel_duplicates"),
                                                     self.on_cancel_duplicates)
        # so aparece durante uma busca (ver on_search_duplicates / _search_duplicates_worker)
        self.duplicates_delete_btn = self._button(toolbar, i18n.t("btn_delete_duplicates"),
                                                     self.on_delete_duplicates)
        self.duplicates_delete_btn.pack(side="right")
        self.duplicates_status_label = tk.Label(toolbar, text="", bg=C["BG"], fg=C["ACCENT"],
                                                   font=("Segoe UI", 9, "bold"))
        self.duplicates_status_label.pack(side="right", padx=14)

        self.duplicates_canvas, self.duplicates_container = self._make_dup_scroll_area(parent, C)

    def _make_dup_scroll_area(self, parent, C):
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
        return canvas, container

    def _add_duplicate_folder(self, label, path, C):
        var = tk.BooleanVar(value=True)
        self._duplicate_folders.append((label, path, var))
        row = tk.Frame(self._duplicates_checks_row, bg=C["BG_CARD"])
        row.pack(side="left", padx=(0, 14))
        tk.Checkbutton(row, variable=var, bg=C["BG_CARD"], activebackground=C["BG_CARD"],
                        selectcolor=C["SELECT_COLOR"], fg=C["FG"], cursor="hand2").pack(side="left")
        tk.Label(row, text=label, bg=C["BG_CARD"], fg=C["FG"], font=("Segoe UI", 9)).pack(side="left")

    def on_add_duplicate_folder(self):
        path = filedialog.askdirectory()
        if not path:
            return
        label = os.path.basename(path.rstrip("\\/")) or path
        self._add_duplicate_folder(label, path, self.C)

    def on_search_duplicates(self):
        if self.worker_running:
            return
        roots = [path for _label, path, var in self._duplicate_folders if var.get()]
        if not roots:
            messagebox.showwarning(i18n.t("brand_name"), i18n.t("duplicates_no_folders"))
            return
        self.worker_running = True
        self._set_busy(True)
        self._duplicates_cancelled = False
        self.duplicates_cancel_btn.pack(side="left", padx=6)
        for w in self.duplicates_container.winfo_children():
            w.destroy()
        self.duplicates_canvas.yview_moveto(0)
        self.duplicates_status_label.config(text="")
        threading.Thread(target=self._search_duplicates_worker, args=(roots,), daemon=True).start()

    def on_cancel_duplicates(self):
        self._duplicates_cancelled = True

    def _search_duplicates_worker(self, roots):
        def progress(stage, done, total):
            if stage == "scan":
                text = i18n.t("duplicates_scanning", count=done)
            elif stage == "compare":
                text = i18n.t("duplicates_comparing", done=done, total=total)
            else:
                text = i18n.t("duplicates_confirming", done=done, total=total)
            self.msg_queue.put(("duplicates_progress", text))

        def should_cancel():
            return getattr(self, "_duplicates_cancelled", False)

        cancelled = False
        try:
            groups = duplicates_module.find_duplicates(roots, progress_callback=progress,
                                                          should_cancel=should_cancel)
        except duplicates_module.SearchCancelled:
            groups = []
            cancelled = True
        except Exception as exc:
            self.msg_queue.put(("log", f"erro na busca de duplicados: {exc}"))
            groups = []
        self.root.after(0, self.duplicates_cancel_btn.pack_forget)
        if cancelled:
            self.msg_queue.put(("log", i18n.t("duplicates_cancelled")))
            self.root.after(0, self.duplicates_status_label.config, {"text": i18n.t("duplicates_cancelled")})
        else:
            self.root.after(0, self._show_duplicate_results, groups)
        self.msg_queue.put(("done", None))

    def _show_duplicate_results(self, groups):
        self._duplicate_groups = groups
        C = self.C
        for w in self.duplicates_container.winfo_children():
            w.destroy()
        # reseta a rolagem pro topo — sem isso, se o usuario tivesse rolado pra baixo antes,
        # a visualizacao ficava "presa" numa posicao que nao existe mais no conteudo novo
        # (parecia que tudo tinha sumido ao rolar rapido durante o carregamento).
        self.duplicates_canvas.yview_moveto(0)

        if not groups:
            tk.Label(self.duplicates_container, text=i18n.t("duplicates_none_found"), bg=C["BG"],
                      fg=C["FG_MUTED"], font=("Segoe UI", 9)).pack(anchor="w", pady=20)
            self.duplicates_status_label.config(text="")
            return

        total_reclaimable = sum(g[0]["size"] * (len(g) - 1) for g in groups)
        self.duplicates_status_label.config(
            text=i18n.t("duplicates_total_found", n=len(groups), size=core.human_size(total_reclaimable)))

        self._duplicate_vars = []
        for group in groups:
            card = widgets.RoundedFrame(self.duplicates_container, bg_root=C["BG"], card_bg=C["BG_CARD"],
                                           radius=10)
            card.pack(fill="x", padx=4, pady=4)
            inner = card.inner
            tk.Label(inner, text=i18n.t("duplicates_group_label", n=len(group),
                                            size=core.human_size(group[0]["size"])),
                      bg=C["BG_CARD"], fg=C["FG"], font=("Segoe UI", 9, "bold")).pack(
                anchor="w", padx=14, pady=(10, 4))
            for i, item in enumerate(group):
                var = tk.BooleanVar(value=(i > 0))  # mantem o primeiro, marca os outros pra apagar
                self._duplicate_vars.append((var, item["path"]))
                row = tk.Frame(inner, bg=C["BG_CARD"])
                row.pack(fill="x", padx=14, pady=2, anchor="w")
                tk.Checkbutton(row, variable=var, bg=C["BG_CARD"], activebackground=C["BG_CARD"],
                                selectcolor=C["SELECT_COLOR"], fg=C["FG"], cursor="hand2").pack(side="left")
                tk.Label(row, text=item["path"], bg=C["BG_CARD"], fg=C["FG_MUTED"], font=("Segoe UI", 8),
                          wraplength=820, justify="left", anchor="w").pack(side="left", fill="x", expand=True)
            tk.Frame(inner, bg=C["BG_CARD"], height=8).pack()

    def on_delete_duplicates(self):
        selected = [path for var, path in getattr(self, "_duplicate_vars", []) if var.get()]
        if not selected:
            return
        if not messagebox.askyesno(i18n.t("brand_name"), i18n.t("duplicates_confirm_body", n=len(selected))):
            return
        threading.Thread(target=self._delete_duplicates_worker, args=(selected,), daemon=True).start()

    def _delete_duplicates_worker(self, paths):
        deleted_set = set(paths)
        freed = duplicates_module.delete_files(paths, log_callback=lambda t: self.msg_queue.put(("log", t)))
        self.msg_queue.put(("log", i18n.t("duplicates_done", n=len(paths), size=core.human_size(freed))))
        remaining_groups = []
        for group in self._duplicate_groups:
            kept = [item for item in group if item["path"] not in deleted_set]
            if len(kept) > 1:
                remaining_groups.append(kept)
        self.root.after(0, self._show_duplicate_results, remaining_groups)
        self.msg_queue.put(("done", None))
