"""Interface grafica do Guaxinim (Tkinter) — com suporte a PT/EN/ES e tema claro/escuro."""

import os
import queue
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from PIL import Image, ImageTk

import categories as cat_module
import cleaner_core as core
import i18n
import system_info
import theme
import tweaks as tweaks_module
import version
import widgets
from gui_shared import CategoryRow, LeftoversDialog, SuccessDialog, build_switch_card
from tab_bloatware import BloatwareMixin
from tab_clean import CleanMixin
from tab_dashboard import DashboardMixin
from tab_duplicates import DuplicatesMixin
from tab_network import NetworkMixin
from tab_programs import ProgramsMixin
from tab_services import ServicesMixin
from tab_tweaks import TweaksMixin

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
ICON_ICO = os.path.join(ASSETS_DIR, "icon.ico")
LOGO_PNG = os.path.join(ASSETS_DIR, "logo.png")


class App(DashboardMixin, CleanMixin, TweaksMixin, ServicesMixin, BloatwareMixin,
           NetworkMixin, DuplicatesMixin, ProgramsMixin):
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

        # Servicos/Bloatware/Programas ficam de fora daqui de proposito: sao construidas sob
        # demanda na primeira visita (ver _show_page), pra nao gastar 3 varreduras de
        # registro/WMI na abertura do app se o usuario nunca chegar a visitar essas abas.
        self._pages_built = set()
        for key, builder in (
            ("dashboard", lambda p, c: self._build_dashboard_page(p, c)),
            ("clean", lambda p, c: self._build_clean_tab(p, c)),
            ("privacy", lambda p, c: self._build_generic_tweaks_tab(
                p, c, tweaks_module.PRIVACY_AI_TWEAKS, "_privacy_cache",
                i18n.t("privacy_section_title"), i18n.t("privacy_section_note"))),
            ("gamer", lambda p, c: self._build_generic_tweaks_tab(
                p, c, tweaks_module.GAMER_TWEAKS, "_gamer_cache",
                i18n.t("gamer_section_title"), i18n.t("gamer_section_note"))),
            ("network", lambda p, c: self._build_network_tab(p, c)),
            ("duplicates", lambda p, c: self._build_duplicates_tab(p, c)),
        ):
            builder(self._pages[key], C)
            self._pages_built.add(key)

        self._show_page(getattr(self, "_current_page", "dashboard"), initial=True)
        self._update_total()

    def _nav_label(self, key):
        return {
            "dashboard": i18n.t("nav_dashboard"), "clean": i18n.t("nav_clean"),
            "privacy": i18n.t("nav_privacy"), "gamer": i18n.t("nav_gamer"),
            "services": i18n.t("nav_services"), "bloatware": i18n.t("nav_bloatware"),
            "network": i18n.t("nav_network"), "duplicates": i18n.t("tab_duplicates"),
            "programs": i18n.t("nav_programs"),
        }[key]

    # abas construidas sob demanda, so na primeira vez que o usuario entra nelas (ver uso
    # de self._pages_built em _build_layout/_show_page).
    _LAZY_TAB_BUILDERS = {
        "services": "_build_services_tab",
        "bloatware": "_build_bloatware_tab",
        "programs": "_build_programs_tab",
    }

    # abas cujos dados podem mudar "por fora" (desinstalou um programa, um servico foi
    # parado por outro app etc) — recarregam sozinhas sempre que o usuario entra nelas,
    # em vez de ficar com o cache parado ate ele clicar em "atualizar" manualmente.
    _AUTO_REFRESH_ON_SHOW = {
        "services": "on_refresh_services",
        "bloatware": "on_refresh_bloatware",
        "programs": "on_list_programs",
    }

    def _show_page(self, key, initial=False):
        self._current_page = key
        for k, item in self._nav_buttons.items():
            item.set_selected(k == key)
        for k, page in self._pages.items():
            if k == key:
                page.pack(fill="both", expand=True, padx=18, pady=14)
            else:
                page.pack_forget()

        if key not in self._pages_built:
            # primeira visita: constroi agora (o proprio builder ja dispara seu scan
            # inicial sozinho, entao nao precisa tambem chamar o refresh logo em seguida).
            builder_name = self._LAZY_TAB_BUILDERS.get(key)
            if builder_name:
                getattr(self, builder_name)(self._pages[key], self.C)
            self._pages_built.add(key)
            return

        # so na entrada de verdade do usuario, nao na primeira montagem da UI.
        if not initial:
            method_name = self._AUTO_REFRESH_ON_SHOW.get(key)
            if method_name:
                getattr(self, method_name)()

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


def run():
    root = tk.Tk()
    App(root)
    root.mainloop()
