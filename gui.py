"""Interface grafica do Guaxinim (Tkinter) — com suporte a PT/EN/ES e tema claro/escuro."""

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from PIL import Image, ImageTk

import bloatware as bloatware_module
import categories as cat_module
import cleaner_core as core
import duplicates as duplicates_module
import i18n
import network_tools
import scheduler
import services_manager as svc_module
import system_info
import theme
import tweaks as tweaks_module
import uninstaller
import version
import widgets

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
ICON_ICO = os.path.join(ASSETS_DIR, "icon.ico")
LOGO_PNG = os.path.join(ASSETS_DIR, "logo.png")


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


class App:
    def __init__(self, root):
        self.root = root
        self.msg_queue = queue.Queue()
        self.worker_running = False
        self.log_lines = []

        self.categories = cat_module.get_categories()
        self.cat_state = {
            c["id"]: {"selected": c["default"], "size": None, "count": 0,
                       "scanned": False, "scanning": False}
            for c in self.categories
        }
        self.rows = {}
        self._startup_cache = None
        self._services_cache = None
        self._programs_cache = None
        self._privacy_cache = None
        self._gamer_cache = None
        self._bloatware_cache = None
        self._tweak_ui = {}
        self._active_adapter = None
        self._scanning_active = False

        self._set_app_icon()
        self._build_layout()
        self._refresh_disk_panel()
        widgets.apply_win11_window_effects(self.root, dark=(theme.get_theme_name() == "dark"))
        self.root.after(150, self._poll_queue)
        self._update_live_specs()

        if not core.is_admin():
            self._log(i18n.t("not_admin_log1"))
            self._log(i18n.t("not_admin_log2"))

    def _set_app_icon(self):
        try:
            if os.path.isfile(ICON_ICO):
                self.root.iconbitmap(default=ICON_ICO)
        except Exception:
            pass

    # ---------- (re)construcao completa da UI ----------
    def _rebuild_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self._build_layout()
        self._refresh_disk_panel()
        for line in self.log_lines:
            self._write_log_line(line)

    def on_open_language_menu(self):
        C = self.C
        menu = tk.Menu(self.root, tearoff=0, bg=C["BG_CARD"], fg=C["FG"],
                         activebackground=C["ACCENT"], activeforeground=C["ACCENT_FG"],
                         relief="flat", bd=0)
        for lang in i18n.LANGS:
            menu.add_command(label=i18n.LANG_LABELS[lang], command=lambda l=lang: self._set_language(l))
        x = self._lang_button.winfo_rootx()
        y = self._lang_button.winfo_rooty() + self._lang_button.winfo_height() + 2
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _set_language(self, lang):
        i18n.set_language(lang)
        self._rebuild_ui()

    def on_toggle_theme(self):
        theme.toggle_theme()
        self._rebuild_ui()

    # ---------- layout ----------
    NAV_ITEMS = [
        ("dashboard", "home"), ("clean", "broom"), ("privacy", "shield"), ("gamer", "gamepad"),
        ("services", "rocket"), ("bloatware", "box"), ("network", "globe"),
        ("duplicates", "copies"), ("programs", "list"),
    ]

    def _build_layout(self):
        C = theme.colors()
        self.C = C
        self.root.title(i18n.t("app_title"))
        if self.root.winfo_width() <= 1:
            self.root.geometry("1220x800")
        self.root.configure(bg=C["BG"])
        self.root.minsize(1020, 660)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("TProgressbar", troughcolor=C["BG_INPUT"], background=C["ACCENT"],
                         bordercolor=C["BG_INPUT"], lightcolor=C["ACCENT"], darkcolor=C["ACCENT"])
        # barras de uso de disco/RAM: verde com bastante espaco livre, amarelo no meio,
        # vermelho quando ta acabando — cor calculada dinamicamente por _usage_bar_style()
        for style_name, color in (("Green", C["RISK_SAFE"]), ("Yellow", C["RISK_CAUTION"]),
                                    ("Red", C["DANGER"])):
            style.configure(f"{style_name}.Horizontal.TProgressbar", troughcolor=C["BG_INPUT"],
                              background=color, bordercolor=C["BG_INPUT"], lightcolor=color, darkcolor=color)
        style.configure("Treeview", background=C["BG_CARD"], fieldbackground=C["BG_CARD"],
                         foreground=C["FG"], rowheight=24, borderwidth=0)
        style.configure("Treeview.Heading", background=C["BG_PANEL"], foreground=C["FG"])
        style.map("Treeview", background=[("selected", C["ACCENT_DARK"])])

        self._build_topbar(C)
        if not core.is_admin():
            self._build_admin_banner(C)

        # rodape com a versao, fixado na borda inferior de verdade (empacotado ANTES do
        # progresso/log pra ficar por baixo dos dois — ajuda demais quando o usuario
        # reporta um problema, pra saber exatamente qual build ele esta rodando).
        footer = tk.Frame(self.root, bg=C["BG_PANEL"], height=22)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        tk.Label(footer, text=f"{i18n.t('brand_name')} v{version.VERSION}", bg=C["BG_PANEL"],
                  fg=C["FG_MUTED"], font=("Segoe UI", 7)).pack(side="right", padx=10)

        # log + progresso fixados embaixo, ANTES do body pra sobrar espaco fixo pra eles
        self.progress = ttk.Progressbar(self.root, mode="indeterminate")
        self.progress.pack(fill="x", side="bottom", padx=14, pady=(0, 10))

        log_frame = tk.Frame(self.root, bg=C["BG"])
        log_frame.pack(fill="x", side="bottom", padx=14, pady=(0, 4))
        tk.Label(log_frame, text=i18n.t("log_label"), bg=C["BG"], fg=C["FG_MUTED"],
                  font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.log_box = ScrolledText(log_frame, height=5, bg=C["LOG_BG"], fg=C["LOG_FG"],
                                      insertbackground=C["FG"], font=("Consolas", 9), relief="flat")
        self.log_box.pack(fill="x")
        self.log_box.configure(state="disabled")

        body = tk.Frame(self.root, bg=C["BG"])
        body.pack(fill="both", expand=True, side="top")

        sidebar = tk.Frame(body, bg=C["BG_PANEL"], width=214)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        content_wrap = tk.Frame(body, bg=C["BG"])
        content_wrap.pack(side="left", fill="both", expand=True)

        self._nav_buttons = {}
        self._pages = {}
        tk.Frame(sidebar, bg=C["BG_PANEL"], height=10).pack()
        # Dashboard sempre primeiro; o resto em ordem alfabetica pelo rotulo TRADUZIDO
        # (assim continua correto em qualquer idioma, nao so em portugues).
        dashboard_item = next(item for item in self.NAV_ITEMS if item[0] == "dashboard")
        rest_items = sorted((item for item in self.NAV_ITEMS if item[0] != "dashboard"),
                              key=lambda item: self._nav_label(item[0]))
        ordered_nav_items = [dashboard_item] + rest_items
        for key, icon in ordered_nav_items:
            label = self._nav_label(key)
            item = widgets.SidebarItem(sidebar, icon, label, C, on_click=lambda k=key: self._show_page(k))
            item.pack(fill="x", padx=8, pady=1)
            self._nav_buttons[key] = item
            self._pages[key] = tk.Frame(content_wrap, bg=C["BG"])

        self._build_dashboard_page(self._pages["dashboard"], C)
        self._build_clean_tab(self._pages["clean"], C)
        self._build_generic_tweaks_tab(self._pages["privacy"], C, tweaks_module.PRIVACY_AI_TWEAKS,
                                          "_privacy_cache", i18n.t("privacy_section_title"),
                                          i18n.t("privacy_section_note"))
        self._build_generic_tweaks_tab(self._pages["gamer"], C, tweaks_module.GAMER_TWEAKS,
                                          "_gamer_cache", i18n.t("gamer_section_title"),
                                          i18n.t("gamer_section_note"))
        self._build_services_tab(self._pages["services"], C)
        self._build_bloatware_tab(self._pages["bloatware"], C)
        self._build_network_tab(self._pages["network"], C)
        self._build_duplicates_tab(self._pages["duplicates"], C)
        self._build_programs_tab(self._pages["programs"], C)

        self._show_page(getattr(self, "_current_page", "dashboard"))
        self._update_total()

    def _nav_label(self, key):
        return {
            "dashboard": i18n.t("nav_dashboard"), "clean": i18n.t("nav_clean"),
            "privacy": i18n.t("nav_privacy"), "gamer": i18n.t("nav_gamer"),
            "services": i18n.t("nav_services"), "bloatware": i18n.t("nav_bloatware"),
            "network": i18n.t("nav_network"), "duplicates": i18n.t("tab_duplicates"),
            "programs": i18n.t("nav_programs"),
        }[key]

    def _show_page(self, key):
        self._current_page = key
        for k, item in self._nav_buttons.items():
            item.set_selected(k == key)
        for k, page in self._pages.items():
            if k == key:
                page.pack(fill="both", expand=True, padx=18, pady=14)
            else:
                page.pack_forget()

    def _page_title(self, parent, C, text):
        tk.Label(parent, text=text, bg=C["BG"], fg=C["FG"],
                  font=("Segoe UI Variable Display", 16, "bold")).pack(anchor="w", pady=(0, 12))

    def _build_topbar(self, C):
        topbar = tk.Frame(self.root, bg=C["BG_PANEL"], height=60)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        brand = tk.Frame(topbar, bg=C["BG_PANEL"])
        brand.pack(side="left", padx=16)
        self._logo_img = None
        try:
            if os.path.isfile(LOGO_PNG):
                pil_logo = Image.open(LOGO_PNG).convert("RGBA").resize((34, 34), Image.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(pil_logo)
        except Exception:
            self._logo_img = None
        if self._logo_img:
            tk.Label(brand, image=self._logo_img, bg=C["BG_PANEL"]).pack(side="left", padx=(0, 8), pady=13)
        tk.Label(brand, text=i18n.t("brand_name"), bg=C["BG_PANEL"], fg=C["ACCENT"],
                  font=("Segoe UI Variable Display", 13, "bold")).pack(side="left", pady=13)

        right = tk.Frame(topbar, bg=C["BG_PANEL"])
        right.pack(side="right", padx=16, pady=10)

        self.specs_label = tk.Label(right, text="CPU … · RAM …", bg=C["BG_PANEL"], fg=C["FG_MUTED"],
                                      font=("Segoe UI", 9))
        self.specs_label.pack(side="left", padx=(0, 14))
        self.disk_chip = tk.Label(right, text="…", bg=C["BG_PANEL"], fg=C["FG_MUTED"],
                                     font=("Segoe UI", 9, "bold"))
        self.disk_chip.pack(side="left", padx=(0, 14))

        theme_icon = "sun" if theme.get_theme_name() == "dark" else "moon"
        theme_btn = tk.Frame(right, bg=C["BG_CARD"], cursor="hand2")
        theme_btn.pack(side="left", padx=(0, 6))
        icon_widget = widgets.Icon(theme_btn, theme_icon, C["FG"], C["BG_CARD"], size=16)
        icon_widget.pack(padx=11, pady=9)
        for w in (theme_btn, icon_widget):
            w.bind("<Button-1>", lambda e: self.on_toggle_theme())

        self._lang_button = widgets.RoundedButton(
            right, i18n.LANG_LABELS[i18n.get_language()], command=self.on_open_language_menu,
            bg_root=C["BG_PANEL"], fill=C["BG_CARD"], fill_hover=C["SELECT_COLOR"], fg=C["FG"],
            font=("Segoe UI", 9, "bold"), radius=8, padx=12, pady=8,
        )
        self._lang_button.pack(side="left")

    def _build_admin_banner(self, C):
        banner = tk.Frame(self.root, bg=C["DANGER_BG"])
        banner.pack(fill="x", side="top")
        warn_row = tk.Frame(banner, bg=C["DANGER_BG"])
        warn_row.pack(side="left", padx=16, pady=6)
        widgets.Icon(warn_row, "warning", C["DANGER"], C["DANGER_BG"], size=14).pack(side="left", padx=(0, 6))
        tk.Label(warn_row, text=i18n.t("not_admin_log1"), bg=C["DANGER_BG"], fg=C["DANGER"],
                  font=("Segoe UI", 8, "bold")).pack(side="left")
        widgets.RoundedButton(banner, i18n.t("restart_admin"), command=self._relaunch_admin,
                                bg_root=C["DANGER_BG"], fill=C["DANGER"], fill_hover=C["DANGER"],
                                fg="white", font=("Segoe UI", 8, "bold"), radius=6, padx=10,
                                pady=5).pack(side="right", padx=16, pady=5)

    # ---------- Dashboard ----------
    def _build_dashboard_page(self, parent, C):
        # a pagina inteira fica dentro de uma area com rolagem — sem isso, quem tem
        # varios discos (C/D/E/F...) tinha o conteudo cortado embaixo sem aviso nenhum.
        canvas = tk.Canvas(parent, bg=C["BG"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=C["BG"])
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        win_id = canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        parent = content  # tudo abaixo continua igual, so que dentro da area rolavel

        self._page_title(parent, C, i18n.t("nav_dashboard"))
        tk.Label(parent, text=i18n.t("dashboard_welcome"), bg=C["BG"], fg=C["FG_MUTED"],
                  font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 14))

        quick_row = tk.Frame(parent, bg=C["BG"])
        quick_row.pack(fill="x", pady=(0, 14))
        self._button(quick_row, i18n.t("nav_clean"), lambda: self._show_page("clean"),
                       primary=True).pack(side="left")
        self._button(quick_row, i18n.t("tab_duplicates"), lambda: self._show_page("duplicates")).pack(
            side="left", padx=6)
        self._button(quick_row, i18n.t("nav_gamer"), lambda: self._show_page("gamer")).pack(side="left")

        grid = tk.Frame(parent, bg=C["BG"])
        grid.pack(fill="x")
        grid.grid_columnconfigure(0, weight=1, uniform="dash")
        grid.grid_columnconfigure(1, weight=1, uniform="dash")

        self.dash_os_card = self._make_info_card(grid, C, "laptop", i18n.t("dashboard_os"))
        self.dash_os_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        self.dash_ram_card, self.dash_ram_bar = self._make_info_card_with_bar(grid, C, "memory", i18n.t("dashboard_ram"))
        self.dash_ram_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 8))
        self.dash_cpu_card = self._make_metric_card(grid, C, "cpu", i18n.t("dashboard_cpu"))
        self.dash_cpu_card.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        self.dash_gpu_card = self._make_metric_card(grid, C, "gpu", i18n.t("dashboard_gpu"))
        self.dash_gpu_card.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=(0, 8))

        tk.Label(parent, text=i18n.t("dashboard_storage"), bg=C["BG"], fg=C["FG"],
                  font=("Segoe UI Variable Display", 12, "bold")).pack(anchor="w", pady=(14, 8))
        self.dash_disks_container = tk.Frame(parent, bg=C["BG"])
        self.dash_disks_container.pack(fill="x")

        threading.Thread(target=self._load_dashboard_worker, daemon=True).start()

    def _make_info_card(self, parent, C, icon, title, with_bar_spacer=False):
        card = widgets.RoundedFrame(parent, bg_root=C["BG"], card_bg=C["BG_CARD"], radius=10)
        inner = card.inner
        head = tk.Frame(inner, bg=C["BG_CARD"])
        head.pack(fill="x", padx=14, pady=(12, 2), anchor="w")
        widgets.Icon(head, icon, C["ACCENT"], C["BG_CARD"], size=16).pack(side="left", padx=(0, 6))
        tk.Label(head, text=title, bg=C["BG_CARD"], fg=C["FG_MUTED"], font=("Segoe UI", 8, "bold")).pack(side="left")
        # height=2 garante que todos os cards tenham a mesma altura de texto, mesmo quando
        # o valor cabe numa linha so (ex: nome da GPU) — sem isso os cards ficavam desiguais.
        value_label = tk.Label(inner, text="…", bg=C["BG_CARD"], fg=C["FG"], font=("Segoe UI", 10, "bold"),
                                 wraplength=380, justify="left", anchor="nw", height=2)
        value_label.pack(fill="x", padx=14, pady=(0, 6 if with_bar_spacer else 12), anchor="w")
        if with_bar_spacer:
            # espaco reservado do tamanho de uma barra de progresso, so pra igualar a altura
            # do card da RAM (que tem barra de verdade) sem inventar uma barra falsa aqui.
            tk.Frame(inner, bg=C["BG_CARD"], height=18).pack(fill="x", padx=14, pady=(0, 6))
        card.value_label = value_label
        return card

    def _make_info_card_with_bar(self, parent, C, icon, title):
        card = self._make_info_card(parent, C, icon, title)
        bar = ttk.Progressbar(card.inner, mode="determinate")
        bar.pack(fill="x", padx=14, pady=(0, 12))
        return card, bar

    def _make_metric_card(self, parent, C, icon, title):
        """Card de monitoramento: nome do componente + varias linhas de metrica,
        cada uma com uma barrinha (uso/temperatura) — montado de verdade so quando os
        dados chegam (ver _fill_cpu_card / _fill_gpu_card), porque nao sabemos de
        antemao quantas metricas vao aparecer (GPU sem nvidia-smi mostra so o nome)."""
        card = widgets.RoundedFrame(parent, bg_root=C["BG"], card_bg=C["BG_CARD"], radius=10)
        inner = card.inner
        head = tk.Frame(inner, bg=C["BG_CARD"])
        head.pack(fill="x", padx=14, pady=(12, 2), anchor="w")
        widgets.Icon(head, icon, C["ACCENT"], C["BG_CARD"], size=16).pack(side="left", padx=(0, 6))
        tk.Label(head, text=title, bg=C["BG_CARD"], fg=C["FG_MUTED"], font=("Segoe UI", 8, "bold")).pack(side="left")
        name_label = tk.Label(inner, text="…", bg=C["BG_CARD"], fg=C["FG"], font=("Segoe UI", 10, "bold"),
                                wraplength=380, justify="left", anchor="w")
        name_label.pack(fill="x", padx=14, pady=(0, 6), anchor="w")
        metrics_frame = tk.Frame(inner, bg=C["BG_CARD"])
        metrics_frame.pack(fill="x", padx=0, pady=(0, 10))
        card.name_label = name_label
        card.metrics_frame = metrics_frame
        return card

    def _add_metric_row(self, metrics_frame, C, label, value_text, pct=None, colored=False):
        row = tk.Frame(metrics_frame, bg=C["BG_CARD"])
        row.pack(fill="x", padx=14, pady=(2, 0))
        tk.Label(row, text=label, bg=C["BG_CARD"], fg=C["FG_MUTED"], font=("Segoe UI", 8)).pack(side="left")
        tk.Label(row, text=value_text, bg=C["BG_CARD"], fg=C["FG"], font=("Segoe UI", 8, "bold")).pack(side="right")
        if pct is not None:
            style = self._load_bar_style(pct) if colored else "TProgressbar"
            bar = ttk.Progressbar(metrics_frame, mode="determinate", style=style, length=100)
            bar.pack(fill="x", padx=14, pady=(1, 6))
            bar["value"] = pct

    @staticmethod
    def _load_bar_style(pct, warn=60, danger=85):
        """Verde enquanto tranquilo, amarelo ficando ocupado/quente, vermelho no limite —
        usado pra uso de CPU/GPU e temperatura (aqui, quanto MAIOR o valor, mais critico —
        o oposto do _usage_bar_style, que e sobre espaco LIVRE em disco/RAM)."""
        if pct < warn:
            return "Green.Horizontal.TProgressbar"
        if pct < danger:
            return "Yellow.Horizontal.TProgressbar"
        return "Red.Horizontal.TProgressbar"

    def _fill_cpu_card(self, cpu):
        # o tick de tempo real (get_cpu_live) so traz freq/uso — nome e contagem de
        # nucleos nao mudam, entao ficam em cache do primeiro carregamento (get_cpu_info).
        if "name" in cpu:
            self._cpu_name_cache = cpu["name"]
        if "cores" in cpu:
            self._cpu_cores_cache = (cpu["cores"], cpu["threads"])
        card = self.dash_cpu_card
        card.name_label.config(text=self._cpu_name_cache)
        for w in card.metrics_frame.winfo_children():
            w.destroy()
        self._add_metric_row(card.metrics_frame, self.C, i18n.t("metric_load"),
                                f"{cpu['usage_percent']:.0f}%", pct=cpu["usage_percent"], colored=True)
        if cpu["freq_mhz"]:
            clock_pct = min(cpu["freq_mhz"] / 5000 * 100, 100)
            self._add_metric_row(card.metrics_frame, self.C, i18n.t("metric_clock"),
                                    f"{cpu['freq_mhz']:.0f} MHz", pct=clock_pct, colored=False)
        cores, threads = getattr(self, "_cpu_cores_cache", (0, 0))
        self._add_metric_row(card.metrics_frame, self.C, i18n.t("dashboard_cores_short"),
                                f"{cores} / {threads}")

    def _fill_gpu_card(self, gpu, gpu_stats):
        card = self.dash_gpu_card
        card.name_label.config(text=gpu["name"])
        for w in card.metrics_frame.winfo_children():
            w.destroy()
        if gpu_stats:
            self._add_metric_row(card.metrics_frame, self.C, i18n.t("metric_load"),
                                    f"{gpu_stats['usage_percent']:.0f}%",
                                    pct=gpu_stats["usage_percent"], colored=True)
            self._add_metric_row(card.metrics_frame, self.C, i18n.t("metric_temp"),
                                    f"{gpu_stats['temp_c']:.0f}°C", pct=gpu_stats["temp_c"], colored=True)
            self._add_metric_row(card.metrics_frame, self.C, i18n.t("metric_power"),
                                    f"{gpu_stats['power_w']:.1f} W")

    def _load_dashboard_worker(self):
        osinfo = system_info.get_os_info()
        cpu = system_info.get_cpu_info()
        ram = system_info.get_ram_info()
        gpu = system_info.get_gpu_info()
        gpu_stats = system_info.get_gpu_stats()
        disks = system_info.get_disks_info()
        self.root.after(0, self._fill_dashboard, osinfo, cpu, ram, gpu, gpu_stats, disks)

    @staticmethod
    def _usage_bar_style(used_pct):
        """Verde com >60% livre, amarelo no meio, vermelho quando o espaco livre ta acabando."""
        free_pct = 100 - used_pct
        if free_pct > 60:
            return "Green.Horizontal.TProgressbar"
        if free_pct > 20:
            return "Yellow.Horizontal.TProgressbar"
        return "Red.Horizontal.TProgressbar"

    def _safe_fill(self, fn, *args):
        """Roda um preenchimento de card isolado — se UM card falhar (ex: leitura de
        disco tropecando num drive que acabou de desconectar), os outros continuam
        atualizando normalmente, e o loop de tempo real (que e a auto-recuperacao)
        nunca fica bloqueado por causa disso. Essa era a causa raiz do Armazenamento
        sumir e nunca mais voltar: uma excecao aqui dentro impedia _update_dashboard_live
        de sequer comecar a rodar."""
        try:
            fn(*args)
        except Exception:
            pass

    def _fill_dashboard(self, osinfo, cpu, ram, gpu, gpu_stats, disks):
        if not hasattr(self, "dash_os_card"):
            return
        self._cpu_name_cache = cpu["name"]
        self._gpu_name_cache = gpu
        self._safe_fill(lambda: self.dash_os_card.value_label.config(
            text=f"{osinfo['caption']}\nBuild {osinfo['build']} · {osinfo['arch']}"))
        self._safe_fill(self._fill_cpu_card, cpu)
        self._safe_fill(self._fill_gpu_card, gpu, gpu_stats)
        self._safe_fill(self._fill_ram_card, ram)
        self._safe_fill(self._fill_disk_cards, disks)
        # so entra no loop de tempo real depois da primeira tentativa de carregamento
        # (que usa PowerShell pra pegar nome de CPU/GPU/SO — isso so precisa rodar 1x) —
        # incondicional, mesmo se algum card acima falhou, pra sempre poder se auto-corrigir.
        if not getattr(self, "_dashboard_live_started", False):
            self._dashboard_live_started = True
            self._update_dashboard_live()

    def _fill_ram_card(self, ram):
        self.dash_ram_card.value_label.config(
            text=i18n.t("dashboard_used_of", used=core.human_size(ram["used"]), total=core.human_size(ram["total"])))
        self.dash_ram_bar["value"] = ram["percent"]
        self.dash_ram_bar.configure(style=self._usage_bar_style(ram["percent"]))

    def _fill_disk_cards(self, disks):
        # se uma leitura pontual vier vazia (hiccup passageiro lendo os discos), mantem
        # os cards que ja estavam na tela em vez de apagar tudo — era essa a causa do
        # "Armazenamento" sumindo do nada: uma leitura vazia zerava os cards e, se a
        # proxima tambem falhasse ou a pagina fosse trocada antes do proximo tick, o
        # card nunca voltava.
        if not disks and getattr(self, "_dash_disk_cards", None):
            return
        # reaproveita os cards existentes em vez de destruir/recriar a cada tick —
        # destruir tudo a cada 2s deixava a rolagem da pagina "pulando" sob o mouse.
        # Compara a LISTA de letras (nao so a quantidade): mesma contagem com letras
        # diferentes (ex: pendrive trocado) tambem precisa reconstruir os cards.
        disk_letters = [d["letter"] for d in disks]
        if list(getattr(self, "_dash_disk_cards", {}).keys()) != disk_letters:
            for w in self.dash_disks_container.winfo_children():
                w.destroy()
            self._dash_disk_cards = {}
            for d in disks:
                card = widgets.RoundedFrame(self.dash_disks_container, bg_root=self.C["BG"],
                                               card_bg=self.C["BG_CARD"], radius=10)
                card.pack(fill="x", pady=4)
                inner = card.inner
                row = tk.Frame(inner, bg=self.C["BG_CARD"])
                row.pack(fill="x", padx=14, pady=(10, 0))
                widgets.Icon(row, "disk", self.C["ACCENT"], self.C["BG_CARD"], size=15).pack(side="left", padx=(0, 6))
                tk.Label(row, text=d["letter"], bg=self.C["BG_CARD"], fg=self.C["FG"],
                          font=("Segoe UI", 10, "bold")).pack(side="left")
                free_label = tk.Label(row, bg=self.C["BG_CARD"], fg=self.C["FG_MUTED"], font=("Segoe UI", 8, "bold"))
                free_label.pack(side="right")
                bar = ttk.Progressbar(inner, mode="determinate")
                bar.pack(fill="x", padx=14, pady=(6, 12))
                self._dash_disk_cards[d["letter"]] = (free_label, bar)
        for d in disks:
            pct = d["used"] / d["total"] * 100 if d["total"] else 0
            free_label, bar = self._dash_disk_cards[d["letter"]]
            free_label.config(text=i18n.t("disk_detail", free=core.human_size(d["free"]),
                                              total=core.human_size(d["total"]), pct=pct))
            bar["value"] = pct
            bar.configure(style=self._usage_bar_style(pct))

    def _update_dashboard_live(self):
        """Atualiza CPU/RAM/GPU/disco a cada 2s com dados reais (psutil/nvidia-smi/shutil),
        sem repetir as chamadas PowerShell lentas de nome — so os valores que realmente
        mudam com o tempo. So faz o trabalho pesado (nvidia-smi, disco) quando a aba
        Dashboard esta realmente visivel, pra nao gastar CPU a toa em segundo plano."""
        if not hasattr(self, "dash_os_card"):
            return
        if getattr(self, "_current_page", None) == "dashboard":
            threading.Thread(target=self._dashboard_live_worker, daemon=True).start()
        self.root.after(2000, self._update_dashboard_live)

    def _dashboard_live_worker(self):
        cpu_live = system_info.get_cpu_live()
        ram = system_info.get_ram_info()
        gpu_stats = system_info.get_gpu_stats()
        disks = system_info.get_disks_info()
        self.root.after(0, self._tick_dashboard_live, cpu_live, ram, gpu_stats, disks)

    def _tick_dashboard_live(self, cpu_live, ram, gpu_stats, disks):
        if not hasattr(self, "dash_os_card"):
            return
        self._safe_fill(self._fill_cpu_card, cpu_live)
        if hasattr(self, "_gpu_name_cache"):
            self._safe_fill(self._fill_gpu_card, self._gpu_name_cache, gpu_stats)
        self._safe_fill(self._fill_ram_card, ram)
        self._safe_fill(self._fill_disk_cards, disks)

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
        canvas.create_window((0, 0), window=self.rows_container, anchor="nw", width=960)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

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
        canvas.create_window((0, 0), window=container, anchor="nw", width=960)
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
        canvas.create_window((0, 0), window=container, anchor="nw", width=960)
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
        canvas.create_window((0, 0), window=self.bloatware_container, anchor="nw", width=960)
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
        result = [(app, bloatware_module.is_installed(app["id"])) for app in bloatware_module.CURATED_BLOATWARE]
        self._bloatware_cache = result
        self.root.after(0, self._render_bloatware_container, self.C)

    # ---------- aba de rede ----------
    def _build_network_tab(self, parent, C):
        wrapper = tk.Frame(parent, bg=C["BG"])
        wrapper.pack(fill="both", expand=True, padx=10, pady=10)

        dns_card = widgets.RoundedFrame(wrapper, bg_root=C["BG"], card_bg=C["BG_CARD"], radius=10)
        dns_card.pack(fill="x", pady=(0, 10))
        dns_content = dns_card.inner
        tk.Label(dns_content, text=i18n.t("network_dns_title"), bg=C["BG_CARD"], fg=C["FG"],
                  font=("Segoe UI Variable Display", 11, "bold")).grid(row=0, column=0, columnspan=5,
                                                                          sticky="w", padx=14, pady=(12, 2))
        tk.Label(dns_content, text=i18n.t("network_dns_note"), bg=C["BG_CARD"], fg=C["FG_MUTED"],
                  font=("Segoe UI", 8), wraplength=700, justify="left").grid(
            row=1, column=0, columnspan=5, sticky="w", padx=14, pady=(0, 8))

        self.dns_status_label = tk.Label(dns_content, text="", bg=C["BG_CARD"], fg=C["FG_MUTED"],
                                           font=("Segoe UI", 8))
        self.dns_status_label.grid(row=3, column=0, columnspan=5, sticky="w", padx=14, pady=(2, 12))

        col = 0
        for key, (label, _servers) in network_tools.DNS_PRESETS.items():
            widgets.RoundedButton(dns_content, label, command=lambda k=key: self.on_set_dns(k),
                                     bg_root=C["BG_CARD"], fill=C["BG_PANEL"], fill_hover=C["SELECT_COLOR"],
                                     fg=C["FG"], font=("Segoe UI", 9, "bold"), radius=8, padx=12,
                                     pady=7).grid(row=2, column=col, padx=(14 if col == 0 else 6, 6), pady=(0, 4))
            col += 1

        flush_card = widgets.RoundedFrame(wrapper, bg_root=C["BG"], card_bg=C["BG_CARD"], radius=10)
        flush_card.pack(fill="x", pady=(0, 10))
        flush_content = flush_card.inner
        tk.Label(flush_content, text=i18n.t("network_flush_title"), bg=C["BG_CARD"], fg=C["FG"],
                  font=("Segoe UI Variable Display", 11, "bold")).grid(row=0, column=0, sticky="w",
                                                                          padx=14, pady=(12, 8))
        self._button(flush_content, i18n.t("btn_flush_dns"), self.on_flush_dns).grid(
            row=0, column=1, padx=14, pady=(12, 8))

        ping_card = widgets.RoundedFrame(wrapper, bg_root=C["BG"], card_bg=C["BG_CARD"], radius=10)
        ping_card.pack(fill="x")
        ping_content = ping_card.inner
        tk.Label(ping_content, text=i18n.t("network_ping_title"), bg=C["BG_CARD"], fg=C["FG"],
                  font=("Segoe UI Variable Display", 11, "bold")).grid(row=0, column=0, columnspan=3,
                                                                          sticky="w", padx=14, pady=(12, 2))
        tk.Label(ping_content, text=i18n.t("network_ping_note"), bg=C["BG_CARD"], fg=C["FG_MUTED"],
                  font=("Segoe UI", 8)).grid(row=1, column=0, columnspan=3, sticky="w", padx=14, pady=(0, 8))

        self.ping_entry = tk.Entry(ping_content, bg=C["BG_PANEL"], fg=C["FG"], insertbackground=C["FG"],
                                     relief="flat", font=("Segoe UI", 9), width=28)
        self.ping_entry.insert(0, "8.8.8.8")
        self.ping_entry.grid(row=2, column=0, padx=(14, 6), pady=(0, 14), sticky="w")
        self._button(ping_content, i18n.t("btn_ping"), self.on_ping).grid(row=2, column=1, pady=(0, 14))
        self.ping_result_label = tk.Label(ping_content, text="", bg=C["BG_CARD"], fg=C["FG_MUTED"],
                                            font=("Segoe UI", 8, "bold"))
        self.ping_result_label.grid(row=2, column=2, padx=14, pady=(0, 14), sticky="w")

    def on_set_dns(self, preset_key):
        threading.Thread(target=self._set_dns_worker, args=(preset_key,), daemon=True).start()

    def _set_dns_worker(self, preset_key):
        adapter = self._active_adapter or network_tools.get_active_adapter_name()
        self._active_adapter = adapter
        if not adapter:
            self.msg_queue.put(("log", i18n.t("no_active_adapter")))
            return
        ok = network_tools.set_dns_preset(adapter, preset_key, log_callback=lambda t: self.msg_queue.put(("log", t)))
        if ok:
            servers = network_tools.get_current_dns(adapter)
            self.msg_queue.put(("log", i18n.t("dns_current", servers=", ".join(servers) or "DHCP")))
            self.root.after(0, self.dns_status_label.config,
                              {"text": i18n.t("dns_current", servers=", ".join(servers) or "DHCP")})

    def on_flush_dns(self):
        threading.Thread(target=lambda: network_tools.flush_dns(log_callback=lambda t: self.msg_queue.put(("log", t))),
                           daemon=True).start()

    def on_ping(self):
        host = self.ping_entry.get().strip() or "8.8.8.8"
        self.ping_result_label.config(text=i18n.t("scanning"))
        threading.Thread(target=self._ping_worker, args=(host,), daemon=True).start()

    def _ping_worker(self, host):
        ok, summary = network_tools.ping_host(host)
        self.msg_queue.put(("log", summary))
        self.root.after(0, self.ping_result_label.config, {"text": summary})

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
        canvas.create_window((0, 0), window=self.services_container, anchor="nw", width=960)
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

    def _button(self, parent, text, command, primary=False):
        C = self.C
        fill = C["ACCENT"] if primary else C["BG_CARD"]
        fill_hover = C["ACCENT_DARK"] if primary else C["SELECT_COLOR"]
        fg = C["ACCENT_FG"] if primary else C["FG"]
        parent_bg = parent["bg"]
        return widgets.RoundedButton(parent, text, command=command, bg_root=parent_bg,
                                       fill=fill, fill_hover=fill_hover, fg=fg,
                                       font=("Segoe UI", 9, "bold"), radius=8, padx=14, pady=8)

    # ---------- specs do PC em tempo real ----------
    def _update_live_specs(self):
        try:
            live = system_info.get_live_usage()
            ram_used = core.human_size(live["ram_used"])
            ram_total = core.human_size(live["ram_total"])
            self.specs_label.config(
                text=f"CPU {live['cpu_percent']:.0f}%  ·  RAM {ram_used} / {ram_total} ({live['ram_percent']:.0f}%)"
            )
        except Exception:
            pass
        self.root.after(2000, self._update_live_specs)

    # ---------- disco ----------
    def _refresh_disk_panel(self):
        info = core.get_disk_usage()
        pct_used = info["used"] / info["total"] * 100 if info["total"] else 0
        self.disk_chip.config(text=f"{info['drive']}  {core.human_size(info['free'])} livres ({pct_used:.0f}% usado)")
        return info

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

    def _relaunch_admin(self):
        core.relaunch_as_admin()
        self.root.destroy()

    def _show_success(self, title_text, message):
        try:
            logo_img = None
            if os.path.isfile(LOGO_PNG):
                pil_logo = Image.open(LOGO_PNG).convert("RGBA").resize((110, 110), Image.LANCZOS)
                logo_img = ImageTk.PhotoImage(pil_logo)
            dialog = SuccessDialog(self.root, self.C, logo_img, title_text, message)
            dialog._logo_ref = logo_img  # mantem referencia viva (senao o Tk descarta a imagem)
        except Exception:
            messagebox.showinfo(title_text, message)

    # ---------- log / progress ----------
    def _write_log_line(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _log(self, text):
        self.log_lines.append(text)
        self._write_log_line(text)

    def _set_busy(self, busy):
        self.worker_running = busy
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "log":
                    self._log(payload)
                elif kind == "scan_result":
                    cid, size, count = payload
                    if cid in self.rows:
                        self.rows[cid].set_size(size, count)
                    if not self._scanning_active:
                        self._update_total()
                elif kind == "scan_start":
                    if payload in self.rows:
                        self.rows[payload].set_scanning()
                elif kind == "scan_progress":
                    done, total, name, running_total = payload
                    self.progress["value"] = done
                    self.total_label.config(text=i18n.t("scanning_progress", done=done, total=total,
                                                            name=name, size=core.human_size(running_total)))
                elif kind == "duplicates_progress":
                    self.duplicates_status_label.config(text=payload)
                elif kind == "done":
                    self._scanning_active = False
                    self._set_busy(False)
                    self.progress.config(mode="indeterminate")
                    self._update_total()
                    self._refresh_disk_panel()
                    if payload:
                        self._show_success(i18n.t("success_clean_title"), payload)
        except queue.Empty:
            pass
        self.root.after(150, self._poll_queue)

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


def run():
    root = tk.Tk()
    App(root)
    root.mainloop()
