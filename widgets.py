"""Widgets customizados com estetica Fluent/WinUI3 (Windows 11) construidos em Tkinter puro."""

import ctypes
import tkinter as tk
import tkinter.font as tkfont


def rounded_rect(canvas, x1, y1, x2, y2, radius=12, **kwargs):
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class RoundedButton(tk.Canvas):
    """Botao Fluent: cantos arredondados, hover suave, sem borda de foco quadrada."""

    def __init__(self, parent, text, command=None, bg_root="#101418", fill="#1d232b",
                  fill_hover="#262d36", fg="#e7edf3", font=("Segoe UI", 9, "bold"),
                  radius=8, padx=16, pady=8, min_width=0):
        super().__init__(parent, bg=bg_root, highlightthickness=0, bd=0, cursor="hand2")
        self.command = command
        self.fill = fill
        self.fill_hover = fill_hover
        self.fg = fg
        self.radius = radius
        self.text = text
        self.font = font
        self.padx = padx
        self.pady = pady
        self.min_width = min_width
        self._hover = False
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _draw(self):
        self.delete("all")
        f = tkfont.Font(font=self.font)
        tw = f.measure(self.text)
        th = f.metrics("linespace")
        w = max(tw + self.padx * 2, self.min_width)
        h = th + self.pady * 2
        self.config(width=w, height=h)
        color = self.fill_hover if self._hover else self.fill
        rounded_rect(self, 1, 1, w - 1, h - 1, radius=self.radius, fill=color, outline=color)
        self.create_text(w / 2, h / 2, text=self.text, fill=self.fg, font=self.font)

    def set_text(self, text):
        self.text = text
        self._draw()

    def _on_enter(self, _event):
        self._hover = True
        self._draw()

    def _on_leave(self, _event):
        self._hover = False
        self._draw()

    def _on_click(self, _event):
        if self.command:
            self.command()


class ToggleSwitch(tk.Canvas):
    """Toggle pill no estilo Windows 11 (Configuracoes > Toggle switch), substitui checkbox."""

    def __init__(self, parent, variable, bg_root="#101418", on_color="#35c99a",
                  off_color="#3a4048", knob_color="#ffffff", command=None, width=40, height=22):
        super().__init__(parent, width=width, height=height, bg=bg_root,
                          highlightthickness=0, bd=0, cursor="hand2")
        self.variable = variable
        self.on_color = on_color
        self.off_color = off_color
        self.knob_color = knob_color
        self.command = command
        self.w = width
        self.h = height
        self._draw()
        self.bind("<Button-1>", self._toggle)

    def _draw(self):
        self.delete("all")
        on = self.variable.get()
        track = self.on_color if on else self.off_color
        rounded_rect(self, 1, 1, self.w - 1, self.h - 1, radius=(self.h - 2) / 2,
                      fill=track, outline=track)
        r = self.h / 2 - 4
        cx = self.w - self.h / 2 if on else self.h / 2
        cy = self.h / 2
        self.create_oval(cx - r, cy - r, cx + r, cy + r, fill=self.knob_color, outline=self.knob_color)

    def _toggle(self, _event):
        self.variable.set(not self.variable.get())
        self._draw()
        if self.command:
            self.command()

    def refresh(self):
        self._draw()


class Checkbox(tk.Canvas):
    """Caixa de selecao — diferente do ToggleSwitch: comunica 'marcar para incluir numa acao em
    lote depois' (usado na Limpeza, junto do botao 'Limpar selecionados'), e nao 'aplicar agora'
    (usado nos outros tweaks, que sao instantaneos)."""

    def __init__(self, parent, variable, bg_root="#101418", on_color="#4cc2ff",
                  off_color=None, border_color="#4a5560", check_color="#ffffff",
                  command=None, size=20, width=None, height=None):
        super().__init__(parent, width=size, height=size, bg=bg_root, highlightthickness=0,
                          bd=0, cursor="hand2")
        self.variable = variable
        self.on_color = on_color
        self.border_color = border_color
        self.check_color = check_color
        self.command = command
        self.size = size
        self._draw()
        self.bind("<Button-1>", self._toggle)

    def _draw(self):
        self.delete("all")
        s = self.size
        if self.variable.get():
            rounded_rect(self, 1, 1, s - 1, s - 1, radius=4, fill=self.on_color, outline=self.on_color)
            self.create_line(s * 0.26, s * 0.52, s * 0.42, s * 0.7, s * 0.76, s * 0.3,
                               fill=self.check_color, width=2, capstyle="round", joinstyle="round")
        else:
            rounded_rect(self, 1, 1, s - 1, s - 1, radius=4, fill="", outline=self.border_color, width=2)

    def _toggle(self, _event):
        self.variable.set(not self.variable.get())
        self._draw()
        if self.command:
            self.command()

    def refresh(self):
        self._draw()


class RoundedFrame(tk.Frame):
    """Frame com fundo em canto arredondado (card estilo Fluent). Use `.inner` para conteudo.

    A LARGURA e ditada por quem chama (grid/pack do pai, via sticky/fill) — o canvas
    acompanha o tamanho que o proprio layout externo alocar. A ALTURA e ditada pelo
    conteudo interno (cresce conforme o texto/widgets dentro precisam). Sem essa
    separacao, o card fica sempre do tamanho minimo do conteudo e ignora o espaco
    que um grid com weight=1 alocou, deixando vaos vazios enormes ao lado."""

    def __init__(self, parent, bg_root, card_bg, radius=12, **inner_kwargs):
        super().__init__(parent, bg=bg_root, highlightthickness=0)
        self.card_bg = card_bg
        self.radius = radius
        self.canvas = tk.Canvas(self, bg=bg_root, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=card_bg, **inner_kwargs)
        self._win_id = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.inner.bind("<Configure>", self._on_inner_configure)

    def _on_canvas_configure(self, event):
        w = event.width
        if w <= 1:
            return
        self.canvas.itemconfig(self._win_id, width=w)
        self._redraw(w, self.canvas.winfo_height())

    def _on_inner_configure(self, event):
        h = event.height
        if h <= 1:
            return
        w = self.canvas.winfo_width()
        if w <= 1:
            w = event.width
        self.canvas.config(height=h)
        self._redraw(max(w, 1), h)

    def _redraw(self, w, h):
        if w <= 1 or h <= 1:
            return
        self.canvas.delete("bg")
        rounded_rect(self.canvas, 0, 0, w, h, radius=self.radius, fill=self.card_bg,
                      outline=self.card_bg, tags="bg")
        self.canvas.tag_lower("bg")
        self.canvas.coords(self._win_id, 0, 0)


def _draw_icon(canvas, name, size, color):
    canvas.delete("all")
    s = size
    lw = max(1, round(s * 0.1))
    if name == "home":
        canvas.create_polygon(s * 0.5, s * 0.12, s * 0.88, s * 0.45, s * 0.74, s * 0.45, s * 0.74, s * 0.85,
                                 s * 0.26, s * 0.85, s * 0.26, s * 0.45, s * 0.12, s * 0.45,
                                 outline=color, fill="", width=lw, joinstyle="round")
    elif name == "broom":
        canvas.create_line(s * 0.78, s * 0.14, s * 0.4, s * 0.58, fill=color, width=lw, capstyle="round")
        canvas.create_polygon(s * 0.4, s * 0.5, s * 0.62, s * 0.72, s * 0.46, s * 0.88, s * 0.18, s * 0.88,
                                 s * 0.16, s * 0.7, outline=color, fill="", width=lw, joinstyle="round")
    elif name == "shield":
        canvas.create_polygon(s * 0.5, s * 0.1, s * 0.85, s * 0.25, s * 0.85, s * 0.52, s * 0.5, s * 0.9,
                                 s * 0.15, s * 0.52, s * 0.15, s * 0.25, outline=color, fill="", width=lw,
                                 joinstyle="round")
    elif name == "gamepad":
        canvas.create_rectangle(s * 0.13, s * 0.36, s * 0.87, s * 0.68, outline=color, width=lw)
        canvas.create_oval(s * 0.6, s * 0.4, s * 0.7, s * 0.5, outline=color, width=lw)
        canvas.create_oval(s * 0.7, s * 0.5, s * 0.8, s * 0.6, outline=color, width=lw)
        canvas.create_line(s * 0.24, s * 0.52, s * 0.4, s * 0.52, fill=color, width=lw, capstyle="round")
        canvas.create_line(s * 0.32, s * 0.44, s * 0.32, s * 0.6, fill=color, width=lw, capstyle="round")
    elif name == "rocket":
        canvas.create_polygon(s * 0.5, s * 0.1, s * 0.68, s * 0.55, s * 0.5, s * 0.68, s * 0.32, s * 0.55,
                                 outline=color, fill="", width=lw, joinstyle="round")
        canvas.create_line(s * 0.4, s * 0.6, s * 0.28, s * 0.86, fill=color, width=lw, capstyle="round")
        canvas.create_line(s * 0.6, s * 0.6, s * 0.72, s * 0.86, fill=color, width=lw, capstyle="round")
    elif name == "box":
        canvas.create_rectangle(s * 0.15, s * 0.34, s * 0.85, s * 0.86, outline=color, width=lw)
        canvas.create_line(s * 0.15, s * 0.34, s * 0.5, s * 0.15, s * 0.85, s * 0.34, fill=color, width=lw,
                             joinstyle="round", capstyle="round")
        canvas.create_line(s * 0.5, s * 0.34, s * 0.5, s * 0.5, fill=color, width=lw)
    elif name == "globe":
        canvas.create_oval(s * 0.15, s * 0.15, s * 0.85, s * 0.85, outline=color, width=lw)
        canvas.create_line(s * 0.15, s * 0.5, s * 0.85, s * 0.5, fill=color, width=lw)
        canvas.create_oval(s * 0.35, s * 0.15, s * 0.65, s * 0.85, outline=color, width=lw)
    elif name == "list":
        for y in (0.26, 0.5, 0.74):
            canvas.create_oval(s * 0.14, s * y - 2, s * 0.14 + 4, s * y + 2, fill=color, outline=color)
            canvas.create_line(s * 0.28, s * y, s * 0.86, s * y, fill=color, width=lw, capstyle="round")
    elif name == "laptop":
        canvas.create_rectangle(s * 0.18, s * 0.2, s * 0.82, s * 0.62, outline=color, width=lw)
        canvas.create_line(s * 0.08, s * 0.72, s * 0.92, s * 0.72, fill=color, width=lw, capstyle="round")
    elif name == "cpu":
        canvas.create_rectangle(s * 0.3, s * 0.3, s * 0.7, s * 0.7, outline=color, width=lw)
        for frac in (0.42, 0.58):
            canvas.create_line(s * frac, s * 0.3, s * frac, s * 0.16, fill=color, width=lw)
            canvas.create_line(s * frac, s * 0.7, s * frac, s * 0.84, fill=color, width=lw)
            canvas.create_line(s * 0.3, s * frac, s * 0.16, s * frac, fill=color, width=lw)
            canvas.create_line(s * 0.7, s * frac, s * 0.84, s * frac, fill=color, width=lw)
    elif name == "memory":
        canvas.create_rectangle(s * 0.14, s * 0.35, s * 0.86, s * 0.62, outline=color, width=lw)
        for frac in (0.3, 0.5, 0.7):
            canvas.create_line(s * frac, s * 0.62, s * frac, s * 0.76, fill=color, width=lw)
    elif name == "gpu":
        canvas.create_rectangle(s * 0.13, s * 0.3, s * 0.87, s * 0.68, outline=color, width=lw)
        canvas.create_oval(s * 0.27, s * 0.39, s * 0.47, s * 0.59, outline=color, width=lw)
        canvas.create_oval(s * 0.53, s * 0.39, s * 0.73, s * 0.59, outline=color, width=lw)
    elif name == "disk":
        canvas.create_oval(s * 0.14, s * 0.14, s * 0.86, s * 0.86, outline=color, width=lw)
        canvas.create_oval(s * 0.4, s * 0.4, s * 0.6, s * 0.6, outline=color, width=lw)
    elif name == "search":
        canvas.create_oval(s * 0.15, s * 0.15, s * 0.62, s * 0.62, outline=color, width=lw)
        canvas.create_line(s * 0.58, s * 0.58, s * 0.86, s * 0.86, fill=color, width=lw, capstyle="round")
    elif name == "copies":
        canvas.create_rectangle(s * 0.32, s * 0.14, s * 0.86, s * 0.62, outline=color, width=lw)
        canvas.create_rectangle(s * 0.14, s * 0.32, s * 0.68, s * 0.8, outline=color, fill="", width=lw)
    elif name == "sun":
        canvas.create_oval(s * 0.3, s * 0.3, s * 0.7, s * 0.7, outline=color, width=lw)
        import math
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            x1, y1 = s * 0.5 + s * 0.32 * math.cos(rad), s * 0.5 + s * 0.32 * math.sin(rad)
            x2, y2 = s * 0.5 + s * 0.44 * math.cos(rad), s * 0.5 + s * 0.44 * math.sin(rad)
            canvas.create_line(x1, y1, x2, y2, fill=color, width=lw, capstyle="round")
    elif name == "moon":
        canvas.create_polygon(s * 0.62, s * 0.14, s * 0.5, s * 0.5, s * 0.62, s * 0.86,
                                 s * 0.82, s * 0.78, s * 0.7, s * 0.5, s * 0.82, s * 0.22,
                                 fill=color, outline=color, smooth=True)
    elif name == "warning":
        canvas.create_polygon(s * 0.5, s * 0.12, s * 0.9, s * 0.85, s * 0.1, s * 0.85,
                                 outline=color, fill="", width=lw, joinstyle="round")
        canvas.create_line(s * 0.5, s * 0.42, s * 0.5, s * 0.64, fill=color, width=lw, capstyle="round")
        canvas.create_oval(s * 0.47, s * 0.7, s * 0.53, s * 0.76, fill=color, outline=color)
    else:
        canvas.create_oval(s * 0.28, s * 0.28, s * 0.72, s * 0.72, outline=color, width=lw)


class Icon(tk.Canvas):
    """Icone de linha monocromatico desenhado no Canvas (sem depender de fonte emoji)."""

    def __init__(self, parent, name, color, bg, size=18):
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0, bd=0)
        self.name = name
        self.color = color
        self.size = size
        self._draw()

    def _draw(self):
        _draw_icon(self, self.name, self.size, self.color)

    def set_color(self, color):
        self.color = color
        self._draw()

    def set_bg(self, bg):
        self.config(bg=bg)


class SidebarItem(tk.Frame):
    """Linha de navegacao lateral (estilo Configuracoes do Windows 11): icone + texto,
    com destaque de fundo quando selecionada."""

    def __init__(self, parent, icon_name, label, colors, on_click):
        self.C = colors
        super().__init__(parent, bg=colors["BG_PANEL"], cursor="hand2")
        self.on_click = on_click
        self.selected = False

        self.icon = Icon(self, icon_name, colors["FG_MUTED"], colors["BG_PANEL"], size=18)
        self.icon.pack(side="left", padx=(16, 10), pady=9)
        self.text_label = tk.Label(self, text=label, bg=colors["BG_PANEL"], fg=colors["FG_MUTED"],
                                     font=("Segoe UI", 10), anchor="w")
        self.text_label.pack(side="left", fill="x", expand=True, pady=9)

        for w in (self, self.icon, self.text_label):
            w.bind("<Button-1>", lambda e: self.on_click())
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def _on_enter(self, _event):
        if not self.selected:
            self._paint(self.C["BG_CARD"], self.C["FG"])

    def _on_leave(self, _event):
        if not self.selected:
            self._paint(self.C["BG_PANEL"], self.C["FG_MUTED"])

    def _paint(self, bg, fg, bold=False):
        self.config(bg=bg)
        self.icon.set_bg(bg)
        self.icon.set_color(fg)
        self.text_label.config(bg=bg, fg=fg, font=("Segoe UI", 10, "bold" if bold else "normal"))

    def set_selected(self, selected):
        self.selected = selected
        if selected:
            self._paint(self.C["ACCENT_TINT"], self.C["ACCENT"], bold=True)
        else:
            self._paint(self.C["BG_PANEL"], self.C["FG_MUTED"])


class Tooltip:
    """Balão de dica que aparece ao passar o mouse (com um pequeno atraso, pra nao piscar
    ao so passar de raspao). Usado nas funcoes/tweaks pra reforcar a explicacao mesmo
    quando o texto ja visivel no card ficou curto ou truncado."""

    def __init__(self, widget, text, bg, fg, border, delay=450):
        self.widget = widget
        self.text = text
        self.bg = bg
        self.fg = fg
        self.border = border
        self.delay = delay
        self._after_id = None
        self._tip = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, event=None):
        self._cancel_timer()
        self._after_id = self.widget.after(self.delay, self._show)

    def _cancel_timer(self):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self):
        if self._tip is not None or not self.text:
            return
        try:
            if not self.widget.winfo_exists():
                return
            x = self.widget.winfo_rootx()
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            self._tip = tk.Toplevel(self.widget)
            self._tip.wm_overrideredirect(True)
            try:
                self._tip.attributes("-topmost", True)
            except Exception:
                pass
            self._tip.configure(bg=self.border)
            tk.Label(self._tip, text=self.text, bg=self.bg, fg=self.fg, font=("Segoe UI", 8),
                      wraplength=320, justify="left", padx=10, pady=6).pack(padx=1, pady=1)
            self._tip.wm_geometry(f"+{x}+{y}")
        except tk.TclError:
            self._tip = None

    def _on_leave(self, event=None):
        self._cancel_timer()
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
            self._tip = None


def add_tooltip(widget, text, C, delay=450):
    return Tooltip(widget, text, bg=C["BG_CARD"], fg=C["FG"], border=C["ACCENT"], delay=delay)


def make_chip(parent, text, colors):
    return tk.Label(parent, text=text, bg=colors["CHIP_BG"], fg=colors["FG_MUTED"],
                      font=("Segoe UI", 7, "bold"), padx=8, pady=2)


def make_risk_badge(parent, risk, colors, label_safe="Seguro", label_caution="Cuidado"):
    if risk == "safe":
        bg, fg, text = colors["RISK_SAFE_BG"], colors["RISK_SAFE"], f"● {label_safe}"
    else:
        bg, fg, text = colors["RISK_CAUTION_BG"], colors["RISK_CAUTION"], f"● {label_caution}"
    return tk.Label(parent, text=text, bg=bg, fg=fg, font=("Segoe UI", 7, "bold"), padx=8, pady=3)


class ItemCard:
    """Card de item em grid: titulo, chips, descricao, badge de risco e controle a direita.
    control_kind='switch' (aplica na hora) ou 'checkbox' (marca pra acao em lote, usado
    so na Limpeza)."""

    def __init__(self, parent, colors, title, description, chips=None, risk=None,
                  initial_selected=False, on_toggle=None, footer_extra="",
                  risk_labels=("Seguro", "Cuidado"), wraplength=360, control_kind="switch"):
        C = colors
        self.C = C
        self.frame = RoundedFrame(parent, bg_root=C["BG"], card_bg=C["BG_CARD"], radius=10)
        inner = self.frame.inner
        pad = 12

        title_label = tk.Label(inner, text=title, bg=C["BG_CARD"], fg=C["FG"],
                                 font=("Segoe UI Variable Display", 10, "bold"), anchor="w", justify="left",
                                 wraplength=wraplength)
        title_label.pack(fill="x", padx=pad, pady=(pad, 2), anchor="w")
        add_tooltip(title_label, description, C)

        if chips:
            chip_row = tk.Frame(inner, bg=C["BG_CARD"])
            chip_row.pack(fill="x", padx=pad, pady=(0, 4), anchor="w")
            for chip_text in chips:
                make_chip(chip_row, chip_text, C).pack(side="left", padx=(0, 6))

        self.desc_label = tk.Label(inner, text=description, bg=C["BG_CARD"], fg=C["FG_MUTED"],
                                     font=("Segoe UI", 8), wraplength=wraplength, justify="left",
                                     anchor="w")
        self.desc_label.pack(fill="x", padx=pad, pady=(0, 8), anchor="w")

        footer = tk.Frame(inner, bg=C["BG_CARD"])
        footer.pack(fill="x", padx=pad, pady=(0, pad))
        if risk:
            make_risk_badge(footer, risk, C, *risk_labels).pack(side="left")
        self.footer_label = tk.Label(footer, text=footer_extra, bg=C["BG_CARD"], fg=C["FG_MUTED"],
                                       font=("Segoe UI", 8, "bold"))
        self.footer_label.pack(side="left", padx=10)

        self.var = tk.BooleanVar(value=initial_selected)

        def _toggle():
            if on_toggle:
                on_toggle(self.var.get())

        if control_kind == "checkbox":
            self.switch = Checkbox(footer, self.var, bg_root=C["BG_CARD"], on_color=C["ACCENT"],
                                     border_color=C["FG_MUTED"], command=_toggle)
        else:
            self.switch = ToggleSwitch(footer, self.var, bg_root=C["BG_CARD"], on_color=C["ACCENT"],
                                         off_color=C["SELECT_COLOR"], command=_toggle)
        self.switch.pack(side="right")

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def grid(self, **kwargs):
        self.frame.grid(**kwargs)

    def set_footer_text(self, text):
        self.footer_label.config(text=text)

    def set_selected(self, value):
        self.var.set(value)
        self.switch.refresh()

    def is_selected(self):
        return self.var.get()


# ---------- efeitos nativos do Windows 11 via DWM ----------

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2


def apply_win11_window_effects(root, dark: bool):
    """Cantos arredondados nativos + barra de titulo escura/clara (so tem efeito no Windows 11)."""
    try:
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
        dwmapi = ctypes.windll.dwmapi

        corner_pref = ctypes.c_int(DWMWCP_ROUND)
        dwmapi.DwmSetWindowAttribute(
            ctypes.wintypes.HWND(hwnd) if hasattr(ctypes, "wintypes") else hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(corner_pref),
            ctypes.sizeof(corner_pref),
        )

        dark_value = ctypes.c_int(1 if dark else 0)
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(dark_value),
            ctypes.sizeof(dark_value),
        )
    except Exception:
        pass
