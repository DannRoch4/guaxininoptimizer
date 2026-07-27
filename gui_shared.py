"""Pecas reutilizadas por varias abas da GUI (CategoryRow, build_switch_card, dialogos) —
extraidas de gui.py pra evitar duplicacao entre os modulos tab_*.py."""

import tkinter as tk
from tkinter import messagebox, ttk

import cleaner_core as core
import i18n
import widgets


class CategoryRow:
    def __init__(self, parent, category, state, colors, on_toggle):
        self.category = category
        self.state = state
        C = colors

        self.var = tk.BooleanVar(value=state["selected"])

        self.card = widgets.RoundedFrame(parent, bg_root=C["BG"], card_bg=C["BG_CARD"], radius=10)
        self.card.pack(fill="x", padx=10, pady=4)
        content = self.card.inner

        def _toggle():
            self.state["selected"] = self.var.get()
            on_toggle()

        self.switch = widgets.Checkbox(
            content, self.var, bg_root=C["BG_CARD"], on_color=C["ACCENT"],
            off_color=C["SELECT_COLOR"], command=_toggle,
        )
        self.switch.grid(row=0, column=0, rowspan=2, padx=(14, 10), pady=14, sticky="n")

        risk_color = C["RISK_SAFE"] if category["risk"] == "safe" else C["RISK_CAUTION"]
        risk_text = i18n.t("risk_safe") if category["risk"] == "safe" else i18n.t("risk_caution")
        admin_text = i18n.t("needs_admin") if category["admin"] else ""

        name_row = tk.Frame(content, bg=C["BG_CARD"])
        name_row.grid(row=0, column=1, sticky="w", pady=(12, 0))
        name_label = tk.Label(name_row, text=i18n.cat_text(category, "name"), bg=C["BG_CARD"], fg=C["FG"],
                                font=("Segoe UI Variable Display", 10, "bold"))
        name_label.pack(side="left")
        tk.Label(name_row, text=f"  {risk_text}", bg=C["BG_CARD"], fg=risk_color,
                  font=("Segoe UI", 8, "bold")).pack(side="left")
        tk.Label(name_row, text=admin_text, bg=C["BG_CARD"], fg=C["FG_MUTED"],
                  font=("Segoe UI", 8)).pack(side="left")

        tk.Label(content, text=i18n.cat_text(category, "description"), bg=C["BG_CARD"],
                  fg=C["FG_MUTED"], font=("Segoe UI", 8), wraplength=540, justify="left").grid(
            row=1, column=1, sticky="w", pady=(2, 12))
        widgets.add_tooltip(name_label, i18n.cat_text(category, "description"), C)

        self.size_label = tk.Label(content, text="—", bg=C["BG_CARD"], fg=C["FG"],
                                     font=("Segoe UI", 10, "bold"), width=14, anchor="e")
        self.size_label.grid(row=0, column=2, rowspan=2, padx=16, sticky="e")

        content.grid_columnconfigure(1, weight=1)

        if state["scanning"]:
            self.set_scanning()
        elif state["scanned"]:
            self._render_size()

    def set_scanning(self):
        self.state["scanning"] = True
        self.size_label.config(text=i18n.t("scanning"), font=("Segoe UI", 9))

    def set_size(self, size_bytes, file_count):
        self.state["scanning"] = False
        self.state["size"] = size_bytes
        self.state["count"] = file_count or 0
        self.state["scanned"] = True
        self._render_size()

    def _render_size(self):
        size_bytes = self.state["size"]
        if size_bytes is None:
            self.size_label.config(text=i18n.t("see_log"), font=("Segoe UI", 9))
        else:
            self.size_label.config(text=core.human_size(size_bytes), font=("Segoe UI", 10, "bold"))

    def is_selected(self):
        return self.var.get()

    def set_selected(self, value):
        self.var.set(value)
        self.state["selected"] = value
        self.switch.refresh()

    @property
    def size_bytes(self):
        return self.state["size"] or 0

    @property
    def scanned(self):
        return self.state["scanned"]


def build_switch_card(parent, C, title, subtitle, tag_text, tag_color, initial_value,
                        on_toggle, right_text=""):
    """Card reutilizavel: toggle + titulo + tag colorida + subtitulo + texto opcional a direita."""
    card = widgets.RoundedFrame(parent, bg_root=C["BG"], card_bg=C["BG_CARD"], radius=10)
    card.pack(fill="x", padx=10, pady=4)
    content = card.inner

    var = tk.BooleanVar(value=initial_value)

    def _toggle():
        on_toggle(var.get())

    switch = widgets.ToggleSwitch(content, var, bg_root=C["BG_CARD"], on_color=C["RISK_SAFE"],
                                    off_color=C["SELECT_COLOR"], command=_toggle)
    switch.grid(row=0, column=0, rowspan=2, padx=(14, 10), pady=14, sticky="n")

    name_row = tk.Frame(content, bg=C["BG_CARD"])
    name_row.grid(row=0, column=1, sticky="w", pady=(12, 0))
    name_label = tk.Label(name_row, text=title, bg=C["BG_CARD"], fg=C["FG"],
                            font=("Segoe UI Variable Display", 10, "bold"))
    name_label.pack(side="left")
    if tag_text:
        tk.Label(name_row, text=f"  {tag_text}", bg=C["BG_CARD"], fg=tag_color,
                  font=("Segoe UI", 8, "bold")).pack(side="left")

    tk.Label(content, text=subtitle, bg=C["BG_CARD"], fg=C["FG_MUTED"], font=("Segoe UI", 8),
              wraplength=540, justify="left").grid(row=1, column=1, sticky="w", pady=(2, 12))
    widgets.add_tooltip(name_label, subtitle, C)

    right_label = tk.Label(content, text=right_text, bg=C["BG_CARD"], fg=C["FG_MUTED"],
                             font=("Segoe UI", 8, "bold"), width=14, anchor="e")
    right_label.grid(row=0, column=2, rowspan=2, padx=16, sticky="e")

    content.grid_columnconfigure(1, weight=1)
    return card, switch, var, right_label


class SuccessDialog(tk.Toplevel):
    """Popup de conclusao com a carinha do guaxinim — usado depois de uma limpeza real ou
    de reverter alteracoes, pra fechar a acao com uma sensacao positiva."""

    def __init__(self, root, C, logo_img, title_text, message):
        super().__init__(root)
        self.configure(bg=C["BG"])
        self.title(title_text)
        self.resizable(False, False)
        self.transient(root)
        self.grab_set()

        if logo_img:
            tk.Label(self, image=logo_img, bg=C["BG"]).pack(pady=(28, 12))
        tk.Label(self, text=title_text, bg=C["BG"], fg=C["ACCENT"],
                  font=("Segoe UI Variable Display", 14, "bold")).pack(padx=24)
        tk.Label(self, text=message, bg=C["BG"], fg=C["FG"], font=("Segoe UI", 9),
                  wraplength=360, justify="center").pack(pady=(10, 22), padx=24)
        widgets.RoundedButton(self, "OK", command=self.destroy, bg_root=C["BG"], fill=C["ACCENT"],
                                fill_hover=C["ACCENT_DARK"], fg=C["ACCENT_FG"],
                                font=("Segoe UI", 9, "bold"), radius=8, padx=32, pady=9).pack(pady=(0, 24))

        self.update_idletasks()
        rw, rh = root.winfo_width(), root.winfo_height()
        rx, ry = root.winfo_x(), root.winfo_y()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{rx + (rw - w) // 2}+{ry + (rh - h) // 2}")


class LeftoversDialog(tk.Toplevel):
    """Janela pra escolher, uma por uma, quais pastas residuais apagar apos desinstalar um programa."""

    def __init__(self, root, C, program_name, leftovers, on_delete_confirmed):
        super().__init__(root)
        self.C = C
        self.on_delete_confirmed = on_delete_confirmed
        self.title(i18n.t("leftovers_title", name=program_name))
        self.configure(bg=C["BG"])
        self.geometry("720x460")
        self.transient(root)

        tk.Label(self, text=i18n.t("leftovers_title", name=program_name), bg=C["BG"], fg=C["FG"],
                  font=("Segoe UI Variable Display", 13, "bold")).pack(anchor="w", padx=16, pady=(14, 2))
        tk.Label(self, text=i18n.t("leftovers_note"), bg=C["BG"], fg=C["FG_MUTED"], font=("Segoe UI", 8),
                  wraplength=680, justify="left").pack(anchor="w", padx=16, pady=(0, 10))

        canvas = tk.Canvas(self, bg=C["BG"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        container = tk.Frame(canvas, bg=C["BG"])
        container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=container, anchor="nw", width=680)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(16, 0))
        scrollbar.pack(side="right", fill="y")

        self._vars = []
        for item in leftovers:
            card = widgets.RoundedFrame(container, bg_root=C["BG"], card_bg=C["BG_CARD"], radius=8)
            card.pack(fill="x", padx=6, pady=3)
            content = card.inner
            var = tk.BooleanVar(value=False)
            self._vars.append((var, item))
            widgets.ToggleSwitch(content, var, bg_root=C["BG_CARD"], on_color=C["RISK_SAFE"],
                                    off_color=C["SELECT_COLOR"]).grid(row=0, column=0, rowspan=2,
                                                                        padx=(12, 10), pady=10, sticky="n")
            tk.Label(content, text=item["path"], bg=C["BG_CARD"], fg=C["FG"], font=("Segoe UI", 9, "bold"),
                      wraplength=520, justify="left").grid(row=0, column=1, sticky="w", pady=(10, 0))
            tk.Label(content, text=core.human_size(item["size"]), bg=C["BG_CARD"], fg=C["FG_MUTED"],
                      font=("Segoe UI", 8)).grid(row=1, column=1, sticky="w", pady=(0, 10))
            content.grid_columnconfigure(1, weight=1)

        footer = tk.Frame(self, bg=C["BG"])
        footer.pack(fill="x", padx=16, pady=12)
        widgets.RoundedButton(footer, i18n.t("leftovers_close_btn"), command=self.destroy,
                                bg_root=C["BG"], fill=C["BG_CARD"], fill_hover=C["SELECT_COLOR"],
                                fg=C["FG"], font=("Segoe UI", 9, "bold"), radius=8, padx=14,
                                pady=8).pack(side="left")
        widgets.RoundedButton(footer, i18n.t("leftovers_delete_btn"), command=self._on_delete_clicked,
                                bg_root=C["BG"], fill=C["DANGER"], fill_hover=C["DANGER"], fg="white",
                                font=("Segoe UI", 9, "bold"), radius=8, padx=14, pady=8).pack(side="right")

    def _on_delete_clicked(self):
        selected = [item for var, item in self._vars if var.get()]
        if not selected:
            return
        if not messagebox.askyesno(i18n.t("leftovers_title", name=""), i18n.t("leftovers_confirm_body", n=len(selected))):
            return
        self.on_delete_confirmed(selected)
        self.destroy()
