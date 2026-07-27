"""Mixin da aba Rede (adaptador, DNS, ping/tracert, IP publico, reset) — extraido de gui.py."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

import i18n
import network_tools
import widgets

_DNS_COLS = 3


class NetworkMixin:
    # ---------- aba de rede ----------
    def _build_network_tab(self, parent, C):
        # area com rolagem (igual as outras abas) — sem isso, com adaptador + DNS + cache +
        # ping/tracert + reset de rede, o conteudo nao cabia na tela e nao tinha como rolar
        # pra ver o resto.
        canvas = tk.Canvas(parent, bg=C["BG"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        wrapper = tk.Frame(canvas, bg=C["BG"])
        wrapper.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        win_id = canvas.create_window((0, 0), window=wrapper, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        # ---- adaptador ativo + IP publico ----
        adapter_card = widgets.RoundedFrame(wrapper, bg_root=C["BG"], card_bg=C["BG_CARD"], radius=10)
        adapter_card.pack(fill="x", padx=10, pady=(10, 10))
        adapter_content = adapter_card.inner
        tk.Label(adapter_content, text=i18n.t("network_adapter_title"), bg=C["BG_CARD"], fg=C["FG"],
                  font=("Segoe UI Variable Display", 11, "bold")).grid(row=0, column=0, columnspan=2,
                                                                          sticky="w", padx=14, pady=(12, 2))
        self.network_adapter_label = tk.Label(adapter_content, text="…", bg=C["BG_CARD"], fg=C["FG_MUTED"],
                                                 font=("Segoe UI", 8), wraplength=700, justify="left")
        self.network_adapter_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=14, pady=(0, 10))

        self.public_ip_label = tk.Label(adapter_content, text="", bg=C["BG_CARD"], fg=C["FG_MUTED"],
                                          font=("Segoe UI", 8, "bold"))
        self.public_ip_label.grid(row=2, column=1, sticky="w", padx=(6, 14), pady=(0, 12))
        self._button(adapter_content, i18n.t("btn_check_public_ip"), self.on_check_public_ip).grid(
            row=2, column=0, sticky="w", padx=(14, 6), pady=(0, 12))

        self._refresh_adapter_info()

        # ---- DNS ----
        dns_card = widgets.RoundedFrame(wrapper, bg_root=C["BG"], card_bg=C["BG_CARD"], radius=10)
        dns_card.pack(fill="x", padx=10, pady=(0, 10))
        dns_content = dns_card.inner
        tk.Label(dns_content, text=i18n.t("network_dns_title"), bg=C["BG_CARD"], fg=C["FG"],
                  font=("Segoe UI Variable Display", 11, "bold")).grid(row=0, column=0, columnspan=_DNS_COLS,
                                                                          sticky="w", padx=14, pady=(12, 2))
        tk.Label(dns_content, text=i18n.t("network_dns_note"), bg=C["BG_CARD"], fg=C["FG_MUTED"],
                  font=("Segoe UI", 8), wraplength=700, justify="left").grid(
            row=1, column=0, columnspan=_DNS_COLS, sticky="w", padx=14, pady=(0, 8))

        for i, (key, (label, _servers)) in enumerate(network_tools.DNS_PRESETS.items()):
            row, col = divmod(i, _DNS_COLS)
            widgets.RoundedButton(dns_content, label, command=lambda k=key: self.on_set_dns(k),
                                     bg_root=C["BG_CARD"], fill=C["BG_PANEL"], fill_hover=C["SELECT_COLOR"],
                                     fg=C["FG"], font=("Segoe UI", 9, "bold"), radius=8, padx=12,
                                     pady=7).grid(row=2 + row, column=col, padx=(14 if col == 0 else 6, 6),
                                                    pady=(0, 6), sticky="w")

        dns_rows = -(-len(network_tools.DNS_PRESETS) // _DNS_COLS)
        self.dns_status_label = tk.Label(dns_content, text="", bg=C["BG_CARD"], fg=C["FG_MUTED"],
                                           font=("Segoe UI", 8))
        self.dns_status_label.grid(row=2 + dns_rows, column=0, columnspan=_DNS_COLS, sticky="w",
                                     padx=14, pady=(2, 12))

        # ---- cache de DNS ----
        flush_card = widgets.RoundedFrame(wrapper, bg_root=C["BG"], card_bg=C["BG_CARD"], radius=10)
        flush_card.pack(fill="x", padx=10, pady=(0, 10))
        flush_content = flush_card.inner
        tk.Label(flush_content, text=i18n.t("network_flush_title"), bg=C["BG_CARD"], fg=C["FG"],
                  font=("Segoe UI Variable Display", 11, "bold")).grid(row=0, column=0, sticky="w",
                                                                          padx=14, pady=(12, 8))
        self._button(flush_content, i18n.t("btn_flush_dns"), self.on_flush_dns).grid(
            row=0, column=1, padx=14, pady=(12, 8))

        # ---- ping + tracert ----
        ping_card = widgets.RoundedFrame(wrapper, bg_root=C["BG"], card_bg=C["BG_CARD"], radius=10)
        ping_card.pack(fill="x", padx=10, pady=(0, 10))
        ping_content = ping_card.inner
        tk.Label(ping_content, text=i18n.t("network_ping_title"), bg=C["BG_CARD"], fg=C["FG"],
                  font=("Segoe UI Variable Display", 11, "bold")).grid(row=0, column=0, columnspan=4,
                                                                          sticky="w", padx=14, pady=(12, 2))
        tk.Label(ping_content, text=i18n.t("network_ping_note"), bg=C["BG_CARD"], fg=C["FG_MUTED"],
                  font=("Segoe UI", 8)).grid(row=1, column=0, columnspan=4, sticky="w", padx=14, pady=(0, 8))

        self.ping_entry = tk.Entry(ping_content, bg=C["BG_PANEL"], fg=C["FG"], insertbackground=C["FG"],
                                     relief="flat", font=("Segoe UI", 9), width=28)
        self.ping_entry.insert(0, "8.8.8.8")
        self.ping_entry.grid(row=2, column=0, padx=(14, 6), pady=(0, 6), sticky="w")
        self._button(ping_content, i18n.t("btn_ping"), self.on_ping).grid(row=2, column=1, padx=6, pady=(0, 6))
        self._button(ping_content, i18n.t("btn_traceroute"), self.on_traceroute).grid(
            row=2, column=2, padx=6, pady=(0, 6))
        self.ping_result_label = tk.Label(ping_content, text="", bg=C["BG_CARD"], fg=C["FG_MUTED"],
                                            font=("Segoe UI", 8, "bold"))
        self.ping_result_label.grid(row=2, column=3, padx=14, pady=(0, 6), sticky="w")

        self.traceroute_box = tk.Text(ping_content, height=8, bg=C["LOG_BG"], fg=C["LOG_FG"],
                                        font=("Consolas", 8), relief="flat", wrap="none")
        self.traceroute_box.grid(row=3, column=0, columnspan=4, sticky="ew", padx=14, pady=(0, 14))
        self.traceroute_box.configure(state="disabled")

        # ---- reset da pilha de rede (risco: apaga config personalizada) ----
        reset_card = widgets.RoundedFrame(wrapper, bg_root=C["BG"], card_bg=C["BG_CARD"], radius=10)
        reset_card.pack(fill="x", padx=10, pady=(0, 10))
        reset_content = reset_card.inner
        tk.Label(reset_content, text=i18n.t("network_reset_title"), bg=C["BG_CARD"], fg=C["FG"],
                  font=("Segoe UI Variable Display", 11, "bold")).grid(row=0, column=0, sticky="w",
                                                                          padx=14, pady=(12, 2))
        widgets.make_risk_badge(reset_content, "cuidado", C, i18n.t("risk_safe"),
                                   i18n.t("risk_caution")).grid(row=0, column=1, sticky="w", padx=(0, 14))
        tk.Label(reset_content, text=i18n.t("network_reset_note"), bg=C["BG_CARD"], fg=C["FG_MUTED"],
                  font=("Segoe UI", 8), wraplength=700, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=14, pady=(0, 8))
        self._button(reset_content, i18n.t("btn_reset_network"), self.on_reset_network).grid(
            row=2, column=0, sticky="w", padx=14, pady=(0, 12))

    def _refresh_adapter_info(self):
        threading.Thread(target=self._adapter_info_worker, daemon=True).start()

    def _adapter_info_worker(self):
        adapter = self._active_adapter or network_tools.get_active_adapter_name()
        self._active_adapter = adapter
        details = network_tools.get_adapter_details(adapter) if adapter else None
        self.root.after(0, self._fill_adapter_info, adapter, details)

    def _fill_adapter_info(self, adapter, details):
        if not hasattr(self, "network_adapter_label"):
            return
        if not adapter or not details:
            self.network_adapter_label.config(text=i18n.t("network_adapter_unknown"))
            return
        self.network_adapter_label.config(
            text=f"{adapter} — " + i18n.t("network_adapter_details", ip=details["ip"] or "—",
                                             gateway=details["gateway"] or "—", mac=details["mac"] or "—"))

    def on_check_public_ip(self):
        self.public_ip_label.config(text=i18n.t("scanning"))
        threading.Thread(target=self._public_ip_worker, daemon=True).start()

    def _public_ip_worker(self):
        ip = network_tools.get_public_ip()
        text = i18n.t("network_public_ip_result", ip=ip) if ip else i18n.t("network_public_ip_error")
        self.root.after(0, self.public_ip_label.config, {"text": text})

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

    def on_traceroute(self):
        host = self.ping_entry.get().strip() or "8.8.8.8"
        self._clear_traceroute_text()
        self._append_traceroute_line(i18n.t("network_traceroute_running"))
        threading.Thread(target=self._traceroute_worker, args=(host,), daemon=True).start()

    def _traceroute_worker(self, host):
        network_tools.traceroute_host_stream(
            host, line_callback=lambda line: self.root.after(0, self._append_traceroute_line, line))

    def _clear_traceroute_text(self):
        if not hasattr(self, "traceroute_box"):
            return
        self.traceroute_box.configure(state="normal")
        self.traceroute_box.delete("1.0", "end")
        self.traceroute_box.configure(state="disabled")

    def _append_traceroute_line(self, line):
        if not hasattr(self, "traceroute_box"):
            return
        self.traceroute_box.configure(state="normal")
        self.traceroute_box.insert("end", line + "\n")
        self.traceroute_box.see("end")
        self.traceroute_box.configure(state="disabled")

    def on_reset_network(self):
        if not messagebox.askyesno(i18n.t("confirm_reset_network_title"), i18n.t("confirm_reset_network_body")):
            return
        threading.Thread(target=self._reset_network_worker, daemon=True).start()

    def _reset_network_worker(self):
        network_tools.reset_network_stack(log_callback=lambda t: self.msg_queue.put(("log", t)))
        self.msg_queue.put(("log", i18n.t("network_reset_done")))
