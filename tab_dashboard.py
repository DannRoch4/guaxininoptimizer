"""Mixin da aba Dashboard — extraido de gui.py (metodos rodam com self ligado a App)."""

import threading
import tkinter as tk
from tkinter import ttk

import cleaner_core as core
import i18n
import system_info
import widgets


class DashboardMixin:
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
        # placeholder ate a primeira leitura de disco chegar — sem isso, o titulo
        # "Armazenamento" ficava sozinho com um vazio enorme embaixo por alguns segundos,
        # parecendo quebrado.
        tk.Label(self.dash_disks_container, text=i18n.t("scanning"), bg=C["BG"], fg=C["FG_MUTED"],
                  font=("Segoe UI", 9)).pack(anchor="w", pady=10)

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
        if not hasattr(self, "_dash_disk_cards") or list(self._dash_disk_cards.keys()) != disk_letters:
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
