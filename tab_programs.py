"""Mixin da aba Programas (lista instalados + desinstalador) — extraido de gui.py."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

import categories as cat_module
import cleaner_core as core
import i18n
import uninstaller
from gui_shared import LeftoversDialog


class ProgramsMixin:
    def _build_programs_tab(self, parent, C):
        toolbar = tk.Frame(parent, bg=C["BG"])
        toolbar.pack(fill="x", pady=(8, 4))
        self._button(toolbar, i18n.t("btn_refresh_programs"), self.on_list_programs).pack(side="left")
        self._button(toolbar, i18n.t("btn_uninstall_selected"), self.on_uninstall_selected).pack(
            side="left", padx=6)

        search_row = tk.Frame(parent, bg=C["BG"])
        search_row.pack(fill="x", pady=(4, 4))
        tk.Label(search_row, text=i18n.t("search_placeholder"), bg=C["BG"], fg=C["FG_MUTED"],
                  font=("Segoe UI", 8)).pack(side="left", padx=(0, 6))
        self.programs_search_var = tk.StringVar()
        search_entry = tk.Entry(search_row, textvariable=self.programs_search_var, bg=C["BG_CARD"],
                                  fg=C["FG"], insertbackground=C["FG"], relief="flat",
                                  font=("Segoe UI", 9), width=40)
        search_entry.pack(side="left", ipady=3)
        self.programs_search_var.trace_add(
            "write", lambda *_: self._fill_programs_tree(self._programs_cache or [])
        )

        tk.Label(parent, text=i18n.t("programs_readonly_note"), bg=C["BG"], fg=C["FG_MUTED"],
                  font=("Segoe UI", 8), wraplength=940, justify="left").pack(anchor="w", pady=(0, 6))

        tree_frame = tk.Frame(parent, bg=C["BG"])
        tree_frame.pack(fill="both", expand=True, pady=6)

        columns = ("name", "version", "publisher", "size", "date")
        self.programs_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)
        headers = {"name": i18n.t("col_program"), "version": i18n.t("col_version"),
                    "publisher": i18n.t("col_publisher"), "size": i18n.t("col_size"),
                    "date": i18n.t("col_installed")}
        widths = {"name": 320, "version": 100, "publisher": 200, "size": 100, "date": 100}
        for col in columns:
            self.programs_tree.heading(col, text=headers[col])
            self.programs_tree.column(col, width=widths[col], anchor="w")

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.programs_tree.yview)
        self.programs_tree.configure(yscrollcommand=tree_scroll.set)
        self.programs_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")

        if getattr(self, "_programs_cache", None):
            self._fill_programs_tree(self._programs_cache)
        else:
            self.on_list_programs()

    def on_list_programs(self):
        for item in self.programs_tree.get_children():
            self.programs_tree.delete(item)
        threading.Thread(target=self._list_programs_worker, daemon=True).start()

    def _list_programs_worker(self):
        programs = cat_module.list_installed_programs()
        self._programs_cache = programs
        self.root.after(0, self._fill_programs_tree, programs)

    def _fill_programs_tree(self, programs):
        for item in self.programs_tree.get_children():
            self.programs_tree.delete(item)
        self.programs_tree.yview_moveto(0)
        query = self.programs_search_var.get().strip().lower() if hasattr(self, "programs_search_var") else ""
        for i, p in enumerate(programs):
            if query and query not in p["name"].lower():
                continue
            size_txt = core.human_size(p["size_kb"] * 1024) if p["size_kb"] else "—"
            date_txt = p["install_date"]
            if len(date_txt) == 8:
                date_txt = f"{date_txt[6:8]}/{date_txt[4:6]}/{date_txt[0:4]}"
            self.programs_tree.insert("", "end", iid=str(i), values=(p["name"], p["version"],
                                                                        p["publisher"], size_txt, date_txt))

    def on_uninstall_selected(self):
        selection = self.programs_tree.selection()
        if not selection or not self._programs_cache:
            messagebox.showwarning(i18n.t("brand_name"), i18n.t("uninstall_none_selected"))
            return
        program = self._programs_cache[int(selection[0])]

        if not (program.get("uninstall_string") or program.get("quiet_uninstall_string")):
            messagebox.showwarning(i18n.t("brand_name"), i18n.t("uninstall_no_command", name=program["name"]))
            return

        if not messagebox.askyesno(i18n.t("uninstall_confirm_title"),
                                     i18n.t("uninstall_confirm_body", name=program["name"])):
            return

        threading.Thread(target=self._uninstall_worker, args=(program,), daemon=True).start()

    def _uninstall_worker(self, program):
        name = program["name"]
        proc = uninstaller.launch_uninstaller(program, log_callback=lambda t: self.msg_queue.put(("log", t)))
        if proc is None:
            return
        self.msg_queue.put(("log", i18n.t("uninstall_launched", name=name)))
        try:
            proc.wait()
        except Exception:
            pass
        self.msg_queue.put(("log", i18n.t("uninstall_finished_scanning", name=name)))
        leftovers = uninstaller.find_leftovers(program)
        if not leftovers:
            self.msg_queue.put(("log", i18n.t("leftovers_none", name=name)))
            self.msg_queue.put(("done", None))
            return
        self.root.after(0, self._open_leftovers_dialog, name, leftovers)
        self.msg_queue.put(("done", None))
        self.on_list_programs()

    def _open_leftovers_dialog(self, name, leftovers):
        def _on_confirm(selected_items):
            threading.Thread(target=self._delete_leftovers_worker, args=(selected_items,), daemon=True).start()
        LeftoversDialog(self.root, self.C, name, leftovers, _on_confirm)

    def _delete_leftovers_worker(self, items):
        total_freed = 0
        removed = 0
        for item in items:
            freed = uninstaller.delete_leftover(item["path"], log_callback=lambda t: self.msg_queue.put(("log", t)))
            if freed:
                total_freed += freed
                removed += 1
                self.msg_queue.put(("log", f"  removido: {item['path']} ({core.human_size(freed)})"))
        self.msg_queue.put(("log", i18n.t("leftovers_done", n=removed, size=core.human_size(total_freed))))
        self.msg_queue.put(("done", None))
