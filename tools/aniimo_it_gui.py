#!/usr/bin/env python3
"""Aniimo — Traduzione Italiana · Centro di controllo grafico.

Interfaccia amichevole (Tkinter, solo standard library) per:
- vedere tutte le installazioni di Aniimo (Steam, launcher, MS Store) e sceglierle;
- vedere se la traduzione è allineata alla patch installata;
- vedere se la traduzione è già applicata e con quale versione;
- applicare la traduzione (alla selezione o a tutte) o ripristinare il backup;
- controllare le novità su GitHub.

Riusa le stesse funzioni testate dell'installer CLI (tools/aniimo_it_installer.py).
Musica: mini-tema chiptune sintetizzato al volo.

REGOLA DI LAYOUT (lezione imparata): nessuna coordinata "magica". Ogni
posizione/altezza deriva dalle metriche MISURATE dei font reali, così il
layout resta corretto a qualsiasi scaling DPI. Ogni testo ha un'ancora
esplicita e una larghezza massima con ellissi. `--check` verifica a coppie
che nessun elemento si sovrapponga.
"""

from __future__ import annotations

import ctypes
import json
import math
import random
import struct
import sys
import threading
import queue
import time
import wave
from argparse import Namespace
from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import aniimo_it_installer as inst  # noqa: E402

# base risorse: in un bundle PyInstaller i dati stanno in _MEIPASS,
# nello sviluppo nella root della repo
ASSETS_DIR = Path(getattr(sys, "_MEIPASS", TOOLS_DIR.parent)) / "assets"

try:
    import winsound
    HAVE_WINSOUND = True
except ImportError:  # sviluppo fuori Windows
    HAVE_WINSOUND = False

APP_TITLE = "Aniimo · Traduzione Italiana — Centro di controllo"
W = 800  # larghezza logica fissa; l'altezza è calcolata dalle metriche

GUI_SETTINGS = inst.USER_WORK_DIR / "gui_settings.json"
THEME_WAV = inst.USER_WORK_DIR / "theme.wav"

SOURCE_LABELS = {"steam": "Steam", "standalone": "Launcher",
                 "msstore": "MS Store", "manuale": "Manuale"}

# --------------------------------------------------------------------------
# Palette pastello
CREAM = "#FFF6EA"
CARD = "#FFFFFF"
INK = "#4A3B52"
INK_SOFT = "#8A7A96"
CORAL = "#FF8FA3"
CORAL_DARK = "#E56B82"
MINT = "#7FD8BE"
MINT_DARK = "#52B89C"
LAV = "#C3B4F0"
LAV_DARK = "#9F8AD8"
SUN = "#FFD98E"
SUN_DARK = "#E8B45A"
SKY = "#A8DCF5"
BUBBLE_COLORS = ["#FFE3EC", "#DFF6EC", "#EAE4FF", "#FFF1D6", "#DCEFFF"]
LOG_BG = "#332A45"

HERO_OK = ("#DFF6EC", "#BFE3D4", "#2E6B57")
HERO_WARN = ("#FFF1D6", "#E8D5A8", "#8A6A2F")
HERO_BAD = ("#FFE3EC", "#F3B7C8", "#B4435C")

NOTE_FREQ = {
    "F3": 174.61, "G3": 196.00, "A3": 220.00, "C3": 130.81,
    "A4": 440.00, "C5": 523.25, "D5": 587.33, "E5": 659.25, "G5": 783.99, "A5": 880.00,
    "C6": 1046.50, "E6": 1318.51, "G6": 1567.98,
}


def enable_dpi_awareness() -> None:
    """Font coerenti con lo scaling reale del display (niente sorprese DPI)."""
    if sys.platform == "win32":
        try:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# --------------------------------------------------------------------------
# Musica — tema chiptune generato proceduralmente (nessun asset binario)
def ensure_theme_wav() -> Path:
    """Sintetizza (una volta sola) il tema musicale del centro di controllo."""
    if THEME_WAV.is_file():
        return THEME_WAV
    THEME_WAV.parent.mkdir(parents=True, exist_ok=True)
    sr = 22050
    bpm = 126.0
    eighth = 60.0 / bpm / 2.0
    steps = 64  # 8 battute
    total = int(steps * eighth * sr) + sr
    buf = [0.0] * total

    melody = [
        "E5", "G5", "A5", "G5",  "E5", "D5", "C5", None,
        "D5", "E5", "G5", "E5",  "D5", "C5", "A4", None,
        "E5", "G5", "A5", "C6",  "A5", "G5", "E5", "D5",
        "C5", "D5", "E5", "G5",  "E5", "D5", "C5", None,
        "G5", "A5", "C6", "A5",  "G5", "E5", "G5", None,
        "A5", "G5", "E5", "D5",  "E5", "D5", "C5", None,
        "C5", "E5", "G5", "A5",  "G5", "E5", "D5", "C5",
        "D5", "E5", "D5", "C5",  "C5", None, None, None,
    ]
    bass_bars = ["C3", "C3", "A3", "A3", "F3", "F3", "G3", "G3"]

    def add_note(freq: float, start: float, dur: float, amp: float) -> None:
        i0 = int(start * sr)
        n = min(int(dur * sr), total - i0)
        for i in range(n):
            t = i / sr
            env = min(1.0, t / 0.006) * math.exp(-2.2 * t / dur)
            s = math.sin(2 * math.pi * freq * t)
            core = 0.62 * s + 0.38 * (1.0 if s >= 0 else -1.0)
            buf[i0 + i] += amp * env * core

    for step, note in enumerate(melody):
        if note:
            add_note(NOTE_FREQ[note], step * eighth, eighth * 0.92, 0.15)
    for bar, root in enumerate(bass_bars):
        for beat in range(4):
            add_note(NOTE_FREQ[root], (bar * 8 + beat * 2) * eighth, eighth * 1.5, 0.09)
    for bar in range(8):
        add_note(NOTE_FREQ[("C6", "E6", "G6")[bar % 3]], (bar * 8 + 7) * eighth, eighth * 0.8, 0.05)

    peak = max(1e-9, max(abs(v) for v in buf))
    scale = 0.22 * 32767.0 / peak
    frames = bytearray()
    for v in buf:
        frames += struct.pack("<h", int(max(-32767.0, min(32767.0, v * scale))))
    with wave.open(str(THEME_WAV), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(bytes(frames))
    return THEME_WAV


def load_gui_settings() -> dict:
    try:
        return json.loads(GUI_SETTINGS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_gui_settings(data: dict) -> None:
    try:
        GUI_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        GUI_SETTINGS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


class QueueWriter:
    """Redirige le print dell'installer nella coda della GUI."""

    def __init__(self, q: "queue.Queue[str]") -> None:
        self.q = q

    def write(self, s: str) -> int:
        if s.strip():
            self.q.put(("log", s.rstrip("\n")))
        return len(s)

    def flush(self) -> None:
        pass


class Metrics:
    """Font reali + misure; il layout dipende solo da questi numeri."""

    def __init__(self, root: tk.Misc):
        mk = lambda spec: tkfont.Font(root=root, font=spec)  # noqa: E731
        self.huge = mk(("Segoe UI", 15, "bold"))
        self.sub = mk(("Segoe UI", 9))
        self.ital = mk(("Segoe UI", 9, "italic"))
        self.hero = mk(("Segoe UI", 11, "bold"))
        self.card_t = mk(("Segoe UI", 9, "bold"))
        self.card_v = mk(("Segoe UI", 11, "bold"))
        self.card_s = mk(("Segoe UI", 8))
        self.btn = mk(("Segoe UI", 10, "bold"))
        self.btn_s = mk(("Segoe UI", 9, "bold"))
        self.logt = mk(("Segoe UI", 9, "bold"))
        self.log = mk(("Consolas", 9))
        self.foot = mk(("Segoe UI", 8))
        self.icon = mk(("Segoe UI Symbol", 12, "bold"))

    def line(self, f: tkfont.Font) -> int:
        return f.metrics("linespace")

    def fit(self, text: str, f: tkfont.Font, max_w: float) -> str:
        """Tronca con ellissi finché il testo non entra in max_w."""
        if f.measure(text) <= max_w or not text:
            return text
        ell = "…"
        while text and f.measure(text + ell) > max_w:
            text = text[:-1]
        return text + ell


def dense_round_rect(cv: tk.Canvas, x1, y1, x2, y2, r, steps: int = 5, **kw) -> int:
    """Rettangolo angolato con archi campionati: smooth senza rigonfiamenti."""
    r = max(2.0, min(r, (y2 - y1) / 2 - 1, (x2 - x1) / 2 - 1))
    pts: list[float] = [x1 + r, y1, x2 - r, y1]

    def arc(cx: float, cy: float, a0: float, a1: float) -> None:
        for i in range(1, steps + 1):
            a = math.radians(a0 + (a1 - a0) * i / steps)
            pts.extend((cx + r * math.cos(a), cy + r * math.sin(a)))

    arc(x2 - r, y1 + r, -90, 0)
    pts.extend((x2, y1 + r, x2, y2 - r))
    arc(x2 - r, y2 - r, 0, 90)
    pts.extend((x2 - r, y2, x1 + r, y2))
    arc(x1 + r, y2 - r, 90, 180)
    pts.extend((x1, y2 - r, x1, y1 + r))
    arc(x1 + r, y1 + r, 180, 270)
    return cv.create_polygon(pts, smooth=True, **kw)


class RoundButton:
    """Pulsante disegnato su canvas, con hover e stato disabilitato."""

    def __init__(self, cv: tk.Canvas, x, y, w, h, label, color, dark, cmd, m: Metrics,
                 *, big: bool = True):
        self.cv, self.x, self.y, self.w, self.h = cv, x, y, w, h
        self.color, self.dark, self.cmd = color, dark, cmd
        self.enabled = True
        self.body = dense_round_rect(cv, x - w / 2, y - h / 2, x + w / 2, y + h / 2,
                                     min(14.0, h / 2 - 2), fill=color, outline=dark, width=2)
        self.txt = cv.create_text(x, y, text=label, fill="white",
                                  font=m.btn if big else m.btn_s)
        for item in (self.body, self.txt):
            cv.tag_bind(item, "<Button-1>", self._click)
            cv.tag_bind(item, "<Enter>", self._hover)
            cv.tag_bind(item, "<Leave>", self._leave)

    def _hover(self, _e=None) -> None:
        if self.enabled:
            self.cv.itemconfig(self.body, fill=self.dark)

    def _leave(self, _e=None) -> None:
        if self.enabled:
            self.cv.itemconfig(self.body, fill=self.color)

    def _click(self, _e=None) -> None:
        if self.enabled and self.cmd:
            self.cmd()

    def set_enabled(self, on: bool) -> None:
        self.enabled = on
        self.cv.itemconfig(self.body, fill=self.color if on else "#DDD6E4",
                           outline=self.dark if on else "#B9B1C6")
        self.cv.itemconfig(self.txt, fill="white" if on else "#F4F1F8")

    def set_label(self, label: str) -> None:
        self.cv.itemconfig(self.txt, text=label)

    def set_style(self, color: str, dark: str) -> None:
        self.color, self.dark = color, dark
        if self.enabled:
            self.cv.itemconfig(self.body, fill=color, outline=dark)


class Card:
    """Card di stato: badge, titolo, riga principale e sottotitolo — tutti vincolati."""

    def __init__(self, cv: tk.Canvas, x1, y1, x2, y2, icon: str, title: str, m: Metrics):
        self.cv, self.x1, self.y1, self.x2, self.y2 = cv, x1, y1, x2, y2
        self.m = m
        dense_round_rect(cv, x1, y1, x2, y2, 14, fill=CARD, outline="#EFE6DC", width=2)
        badge_d = min(30.0, (y2 - y1) * 0.38)
        bcx = x1 + badge_d / 2 + 12
        bcy = y1 + (y2 - y1) / 2
        self.badge = cv.create_oval(bcx - badge_d / 2, bcy - badge_d / 2,
                                    bcx + badge_d / 2, bcy + badge_d / 2, fill=SUN, outline="")
        cv.create_text(bcx, bcy, text=icon, font=m.icon, fill="white")
        tx = x1 + badge_d + 26
        self.max_w = x2 - tx - 12
        cv.create_text(tx, y1 + 8, text=m.fit(title, m.card_t, self.max_w), anchor="nw",
                       font=m.card_t, fill=INK_SOFT)
        self.value = cv.create_text(tx, y1 + 8 + m.line(m.card_t) + 2, text="…",
                                    anchor="nw", font=m.card_v, fill=INK)
        self.sub = cv.create_text(x1 + 12, y2 - 6, text="", anchor="sw",
                                  font=m.card_s, fill=INK_SOFT)
        self.sub_max_w = x2 - x1 - 24

    def set(self, value: str, sub: str = "", color: str = SUN) -> None:
        m = self.m
        self.cv.itemconfig(self.value, text=m.fit(value, m.card_v, self.max_w))
        self.cv.itemconfig(self.sub, text=m.fit(sub, m.card_s, self.sub_max_w))
        self.cv.itemconfig(self.badge, fill=color)


class App:
    def __init__(self, root: tk.Tk, smoke: bool = False, defer_status: bool = False) -> None:
        self.root = root
        self.smoke = smoke
        self.q: "queue.Queue[tuple]" = queue.Queue()
        self.busy = False
        self.payload: dict | None = None
        self.installs: list[dict] = []
        self.selected: dict | None = None
        self.manifest = inst.local_manifest()
        self.chip_items: list[int] = []
        self.pill_items: list[int] = []
        self.music_on = bool(load_gui_settings().get("music_on", True))
        self.t0 = time.time()
        self.blink_at = time.time() + 3.0
        self.blink_closing = False
        self.celebrate_until = 0.0
        self.mascot_dy = 0.0
        self.confetti: list[tuple[int, float, float]] = []
        self.reserved: list[tuple[float, float, float, float, str]] = []

        root.title(APP_TITLE)
        root.resizable(False, False)
        root.configure(bg=CREAM)

        self.m = Metrics(root)
        self.cv = tk.Canvas(root, width=W, height=600, bg=CREAM, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)

        self._build_layout()
        self._spawn_bubbles()
        self._build_mascot()

        # dimensione finale: l'altezza deriva dal flusso misurato
        root.update_idletasks()
        self.cv.configure(height=self.total_h)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        pos_x, pos_y = (sw - W) // 2, max(0, (sh - self.total_h) // 2 - 20)
        root.geometry(f"{W}x{self.total_h}+{pos_x}+{pos_y}")
        root.attributes("-topmost", True)
        root.after(4000, lambda: root.attributes("-topmost", False))
        try:
            root.iconbitmap(str(ASSETS_DIR / "aniimo-italian-installer-icon.ico"))
        except tk.TclError:
            pass

        # log in stile console, incorporato nel canvas
        self.log = tk.Text(self.root, bg=LOG_BG, fg="#EDE6F7", relief="flat",
                           font=("Consolas", 9), wrap="word", state="disabled",
                           padx=10, pady=4, highlightthickness=0)
        log_h = self.log_bottom - self.log_top - self.m.line(self.m.logt) - 8
        dense_round_rect(self.cv, self.margin, self.log_top, W - self.margin, self.log_bottom,
                         14, fill=LOG_BG, outline="#241D33", width=2)
        self.log_title = self.cv.create_text(
            self.margin + 18, self.log_top + 8, text="Registro attività",
            anchor="nw", font=self.m.logt, fill="#B9AFD6")
        self.cv.create_window(W // 2, self.log_top + 8 + self.m.line(self.m.logt)
                              + (log_h - self.m.line(self.m.logt) - 8) / 2,
                              window=self.log, width=W - 2 * self.margin - 20, height=log_h)
        self.log.configure(state="normal")
        for line in (
            "Benvenuto nel Centro di controllo ✦",
            "Rilevo le installazioni di Aniimo (può richiedere qualche secondo)…",
        ):
            self.log.insert("end", line + "\n")
        self.log.configure(state="disabled")

        self.footer = self.cv.create_text(
            W // 2, self.total_h - 6, text="", anchor="s", font=self.m.foot, fill=INK_SOFT)

        self._tick_job = root.after(50, self._tick)
        self._poll_job = root.after(80, self._poll)
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        if not defer_status:
            self.refresh_status()
        if self.music_on and not smoke:
            # la prima sintesi del tema può richiedere qualche secondo: fuori dal thread UI
            threading.Thread(target=self._start_music, daemon=True).start()

    def _start_music(self) -> None:
        if not HAVE_WINSOUND:
            return
        try:
            winsound.PlaySound(str(ensure_theme_wav()),
                               winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
        except Exception:
            self.music_on = False

    def _on_close(self) -> None:
        for attr in ("_tick_job", "_poll_job"):
            job = getattr(self, attr, None)
            if job:
                try:
                    self.root.after_cancel(job)
                except Exception:
                    pass
        self.root.destroy()

    # ------------------------------------------------------------------ UI
    def _build_layout(self) -> None:
        cv, m = self.cv, self.m
        mg = self.margin = 18
        gap = 14  # gap verticale generoso: gli elementi non si toccano mai
        pad = 10
        y = 14.0

        # --- header --------------------------------------------------------
        head_inner = m.line(m.huge) + 4 + m.line(m.sub) + 3 + m.line(m.ital)
        mascot_h = 108.0
        header_h = max(head_inner + 2 * pad + 6, mascot_h)
        dense_round_rect(cv, mg, y, W - mg, y + header_h, 16,
                         fill=CARD, outline="#EFE6DC", width=2)
        text_x = 176
        btn_zone = 108
        avail = W - mg - btn_zone - text_x - 12
        cv.create_text(text_x, y + pad, text="Traduzione Italiana", anchor="nw", font=m.huge, fill=INK)
        cv.create_text(text_x, y + pad + m.line(m.huge) + 4,
                       text=m.fit("Centro di controllo · fork notorious-pizza · traduzione originale di Sici29",
                                  m.sub, avail),
                       anchor="nw", font=m.sub, fill=INK_SOFT)
        cv.create_text(text_x, y + pad + m.line(m.huge) + 4 + m.line(m.sub) + 3,
                       text="Nel gioco seleziona: Inglese",
                       anchor="nw", font=m.ital, fill=CORAL_DARK)
        bw = 100
        bhh = m.line(m.btn_s) + 16
        bx = W - mg - 14 - bw / 2
        by1 = y + 12 + bhh / 2
        by2 = by1 + bhh + 8
        self.music_btn = RoundButton(cv, bx, by1, bw, bhh, "Musica ♪", MINT, MINT_DARK,
                                     self.toggle_music, m, big=False)
        self.gh_btn = RoundButton(cv, bx, by2, bw, bhh, "GitHub", LAV, LAV_DARK,
                                  self.open_github, m, big=False)
        self._reserve(mg, y, W - mg, y + header_h, "header")
        self.header_y, self.header_h = y, header_h
        y += header_h + gap

        # --- banner di sintesi ---------------------------------------------
        self.hero_lines = 2
        hero_h = self.hero_lines * m.line(m.hero) + 2 * pad
        self.hero = dense_round_rect(cv, mg, y, W - mg, y + hero_h, 14,
                                     fill=HERO_WARN[0], outline=HERO_WARN[1], width=2)
        self.hero_text = cv.create_text(W // 2, y + hero_h / 2, text="Carico lo stato…",
                                        width=W - 2 * mg - 32, justify="center",
                                        font=m.hero, fill=HERO_WARN[2])
        self._reserve(mg, y, W - mg, y + hero_h, "hero")
        y += hero_h + gap

        # --- striscia selettore installazioni -------------------------------
        self.strip_h = m.line(m.btn_s) + 20
        self.strip_y = y
        self._reserve(mg, y, W - mg, y + self.strip_h, "selector")
        y += self.strip_h + gap

        # --- card di stato ---------------------------------------------------
        ch = m.line(m.card_t) + 2 + m.line(m.card_v) + 4 + m.line(m.card_s) + 2 * pad + 4
        cw = (W - 2 * mg - gap) / 2
        self.card_game = Card(cv, mg, y, mg + cw, y + ch, "◆", "Installazione", m)
        self.card_tr = Card(cv, mg + cw + gap, y, W - mg, y + ch, "✦", "Traduzione", m)
        self.card_align = Card(cv, mg, y + ch + gap, mg + cw, y + 2 * ch + gap, "⬡",
                               "Allineamento patch", m)
        self.card_news = Card(cv, mg + cw + gap, y + ch + gap, W - mg, y + 2 * ch + gap, "✧",
                              "Novità traduzione", m)
        self._reserve(mg, y, W - mg, y + 2 * ch + gap, "card")
        y += 2 * ch + gap + gap

        # --- pulsanti principali ---------------------------------------------
        bh = m.line(m.btn) + 22
        big = [
            ("↻  Aggiorna stato", MINT, MINT_DARK, None),
            ("✦  Applica traduzione", CORAL, CORAL_DARK, None),
            ("♻  Ripristina backup", LAV, LAV_DARK, None),
        ]
        widths = [max(150.0, m.btn.measure(lbl) + 36) for lbl, *_ in big]
        budget = W - 2 * mg
        total = sum(widths) + 18 * 2
        if total > budget:
            k = budget / total
            widths = [w * k for w in widths]
        x = mg + (budget - total) / 2
        made = []
        for (lbl, color, dark, _), w in zip(big, widths):
            x += w / 2
            made.append(RoundButton(cv, x, y + bh / 2, w, bh, lbl, color, dark, None, m))
            self._reserve(x - w / 2, y, x + w / 2, y + bh, f"btn:{lbl}")
            x += w / 2 + 18
        self.btn_refresh, self.btn_apply, self.btn_restore = made
        self.btn_refresh.cmd = self.refresh_status
        self.btn_apply.cmd = self.apply_translation
        self.btn_restore.cmd = self.restore_backup
        y += bh + gap + gap

        # --- striscia azioni secondarie (dinamica) ---------------------------
        self.sec_h = m.line(m.btn_s) + 18
        self.sec_y = y
        self._reserve(mg, y, W - mg, y + self.sec_h, "secondary")
        y += self.sec_h + gap

        # --- log + footer (chiusura del flusso) ------------------------------
        log_lines = 6
        self.log_top = y
        self.log_bottom = y + m.line(m.logt) + 10 + log_lines * m.line(m.log) + 12
        self._reserve(mg, self.log_top, W - mg, self.log_bottom, "log")
        self.total_h = int(self.log_bottom + m.line(m.foot) + 14)

    def _reserve(self, x1, y1, x2, y2, name: str) -> None:
        self.reserved.append((x1, y1, x2, y2, name))

    def check_overlaps(self) -> list[str]:
        """Verifica a coppie che le aree riservate non si intersechino (padding 2px)."""
        bad = []
        for i in range(len(self.reserved)):
            for j in range(i + 1, len(self.reserved)):
                a, b = self.reserved[i], self.reserved[j]
                if a[0] < b[2] - 2 and b[0] < a[2] - 2 and a[1] < b[3] - 2 and b[1] < a[3] - 2:
                    bad.append(f"{a[4]} ∩ {b[4]}")
        return bad

    def _spawn_bubbles(self) -> None:
        self.bubbles = []
        top = self.header_y + self.header_h + 4
        for _ in range(14):
            r = random.uniform(6, 16)
            x = random.uniform(10, W - 10)
            y = random.uniform(top, self.log_top - 20)
            item = self.cv.create_oval(x - r, y - r, x + r, y + r,
                                       fill=random.choice(BUBBLE_COLORS), outline="")
            self.cv.tag_lower(item)
            self.bubbles.append((item, random.uniform(0.15, 0.5), random.uniform(-0.3, 0.3)))

    def _build_mascot(self) -> None:
        """Piccola creatura tonda in stile Aniimo: orecchie, fogliolina, blush."""
        cv = self.cv
        mx = 94.0
        my = self.header_y + self.header_h / 2 + 4
        self.mx, self.my = mx, my
        items: list[int] = []
        for sx in (-1, 1):  # orecchie
            items.append(cv.create_polygon(mx + sx * 26, my - 18, mx + sx * 42, my - 56,
                                           mx + sx * 8, my - 28,
                                           smooth=True, fill="#FFE0E9", outline="#F3B7C8", width=3))
        items.append(cv.create_line(mx, my - 28, mx, my - 42, width=3, fill="#7FBF8E"))
        items.append(cv.create_oval(mx - 12, my - 56, mx + 10, my - 40,
                                    fill="#9FE0AE", outline="#7FBF8E", width=2))
        items.append(cv.create_oval(mx - 42, my - 32, mx + 42, my + 46,
                                    fill="#FFE0E9", outline="#F3B7C8", width=3))
        items.append(cv.create_oval(mx - 24, my + 4, mx + 24, my + 44, fill="#FFF7FA", outline=""))
        self.m_eyes = [
            cv.create_oval(mx - 21, my - 9, mx - 11, my + 1, fill=INK, outline=""),
            cv.create_oval(mx + 11, my - 9, mx + 21, my + 1, fill=INK, outline=""),
        ]
        self.m_shine = [
            cv.create_oval(mx - 19, my - 8, mx - 15, my - 4, fill="white", outline=""),
            cv.create_oval(mx + 13, my - 8, mx + 17, my - 4, fill="white", outline=""),
        ]
        self.m_eyes_happy = [
            cv.create_arc(mx - 22, my - 7, mx - 10, my + 5, start=20, extent=140,
                          style="arc", width=2, state="hidden"),
            cv.create_arc(mx + 10, my - 7, mx + 22, my + 5, start=20, extent=140,
                          style="arc", width=2, state="hidden"),
        ]
        items.append(cv.create_oval(mx - 31, my + 7, mx - 19, my + 15, fill="#FFB9CC", outline=""))
        items.append(cv.create_oval(mx + 19, my + 7, mx + 31, my + 15, fill="#FFB9CC", outline=""))
        items.append(cv.create_arc(mx - 7, my + 9, mx + 7, my + 19, start=20, extent=140,
                                   style="arc", width=2))
        self.m_heart = cv.create_text(mx + 52, my - 42, text="♥", fill=CORAL,
                                      font=("Segoe UI Symbol", 11, "bold"))
        items.append(cv.create_text(mx - 56, my - 26, text="✧", fill="#F3B7C8",
                                    font=("Segoe UI Symbol", 10)))
        self.m_group = items + self.m_eyes + self.m_shine + self.m_eyes_happy
        for item in items:
            self.cv.tag_raise(item)

    # ------------------------------------------------------------ animazione
    def _tick(self) -> None:
        if not self.root.winfo_exists():
            return
        now = time.time()
        for item, vy, wob in self.bubbles:
            self.cv.move(item, wob * 0.6, -vy)
            x1b, y1b, _, y2b = self.cv.bbox(item)
            if y2b < self.header_y + self.header_h or x1b < -20 or x1b > W + 20:
                self.cv.move(item, -wob * 0.6 + random.uniform(-8, 8),
                             self.log_top - 20 - y1b)

        happy = now < self.celebrate_until
        bob = math.sin((now - self.t0) * 2.2) * 4
        if happy:
            bob -= abs(math.sin((now - self.t0) * 7.0)) * 16
        dy = bob - self.mascot_dy
        if dy:
            self.mascot_dy = bob
            for item in self.m_group:
                self.cv.move(item, 0, dy)
        pulse = 11 + int(2.5 * (1.0 + math.sin((now - self.t0) * 3.2)))
        self.cv.itemconfig(self.m_heart, font=("Segoe UI Symbol", pulse, "bold"))

        if happy:
            show, happy_show = "hidden", "normal"
        elif now >= self.blink_at:
            show, happy_show = "hidden", "hidden"
            if not self.blink_closing:
                self.blink_closing = True
        else:
            show, happy_show = "normal", "hidden"
        if self.blink_closing and not happy and now - self.blink_at > 0.14:
            self.blink_closing = False
            self.blink_at = now + random.uniform(2.4, 4.6)
            show, happy_show = "normal", "hidden"
        for e in self.m_eyes:
            self.cv.itemconfig(e, state=show)
        for e in self.m_eyes_happy:
            self.cv.itemconfig(e, state=happy_show)
        for e in self.m_shine:
            self.cv.itemconfig(e, state=show)

        if self.confetti:
            alive = []
            for item, vx, vy in self.confetti:
                vy += 0.35
                self.cv.move(item, vx, vy)
                _, y1c, _, _ = self.cv.bbox(item)
                if y1c < self.total_h + 20:
                    alive.append((item, vx, vy))
                else:
                    self.cv.delete(item)
            self.confetti = alive
        self._tick_job = self.root.after(50, self._tick)

    def _poll(self) -> None:
        if not self.root.winfo_exists():
            return
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "log":
                    self.log.configure(state="normal")
                    self.log.insert("end", payload + "\n")
                    self.log.see("end")
                    self.log.configure(state="disabled")
                elif kind == "done":
                    self._work_done(payload)
                elif kind == "status":
                    self._render_status(payload)
        except queue.Empty:
            pass
        self._poll_job = self.root.after(80, self._poll)

    # ------------------------------------------------------------ thread worker
    def _run_worker(self, fn, label: str, *, celebrate_on_success: bool = False,
                    info_on_success: str | None = None, refresh_after: bool = True,
                    on_success=None) -> None:
        if self.busy:
            return
        self.busy = True
        for b in (self.btn_refresh, self.btn_apply, self.btn_restore):
            b.set_enabled(False)
        self.cv.itemconfig(self.log_title, text=f"Registro attività · {label} in corso…")
        self._log_line(f"— {label} —")

        def worker() -> None:
            old_stdout = sys.stdout
            code: int | None = None
            err: str | None = None
            try:
                sys.stdout = QueueWriter(self.q)
                code = fn()
            except Exception as exc:  # noqa: BLE001
                err = f"{type(exc).__name__}: {exc}"
            finally:
                sys.stdout = old_stdout
            self.q.put(("done", {"label": label, "code": code, "err": err,
                                "celebrate": celebrate_on_success, "info": info_on_success,
                                "refresh": refresh_after, "on_success": on_success}))

        threading.Thread(target=worker, daemon=True).start()

    def _work_done(self, info: dict) -> None:
        self.busy = False
        for b in (self.btn_refresh, self.btn_apply, self.btn_restore):
            b.set_enabled(True)
        self.cv.itemconfig(self.log_title, text="Registro attività")
        if info["err"]:
            self._log_line(f"✗ Errore: {info['err']}")
            messagebox.showerror(APP_TITLE, f"Operazione non riuscita:\n{info['err']}")
        elif info["code"] == 0:
            self._log_line(f"✓ {info['label']} completato!")
            if info["celebrate"]:
                self.celebrate()
            if info["info"]:
                messagebox.showinfo(APP_TITLE, info["info"])
            if info.get("on_success"):
                info["on_success"]()
        elif info["code"] is not None:
            self._log_line(f"! {info['label']} interrotto (codice {info['code']}). Leggi il registro.")
        if info["refresh"]:
            self.refresh_status()
        else:
            self._render_buttons()

    def _log_line(self, text: str) -> None:
        self.q.put(("log", text))

    # ------------------------------------------------------------ stato
    def refresh_status(self) -> None:
        if self.busy:
            return
        self.card_game.set("Rilevo le installazioni…", "un attimo ✧", SKY)

        def job() -> int:
            installs = inst.list_game_installations()
            saved = str(load_gui_settings().get("selected_game_dir") or "")
            if saved:
                sp = Path(saved)
                try:
                    ok_saved = sp.is_dir() and inst.looks_like_game_dir(sp) and not any(
                        e["path"].resolve() == sp.resolve() for e in installs)
                except OSError:
                    ok_saved = False
                if ok_saved:
                    installs.append(inst.describe_installation(sp, source="manuale"))
            payload = {
                "installs": installs,
                "running": inst.process_running(),
                "update": inst.check_for_updates(silent=True),
            }
            self.q.put(("status", payload))
            return 0

        self._run_worker(job, "Rilevamento installazioni", refresh_after=False)

    @staticmethod
    def short_path(text: str, keep: int = 46) -> str:
        if len(text) <= keep:
            return text
        return text[:16] + "…" + text[-(keep - 17):]

    def _set_hero(self, text: str, theme: tuple[str, str, str]) -> None:
        bg, outline, fg = theme
        self.cv.itemconfig(self.hero, fill=bg, outline=outline)
        self.cv.itemconfig(self.hero_text, text=text, fill=fg)

    # ------------------------------------------------------------ selettore e pillole
    def _draw_install_chips(self) -> None:
        cv, m = self.cv, self.m
        for item in self.chip_items:
            cv.delete(item)
        self.chip_items = []
        if not self.installs:
            return
        y = self.strip_y + self.strip_h / 2
        h = self.strip_h - 4
        labels = []
        for e in self.installs:
            name = SOURCE_LABELS.get(e["source"], e["source"])
            lbl = f"{name} · build {e.get('update') or '?'}"
            if not e.get("writable"):
                lbl = "✕ " + lbl
            labels.append((lbl, e))
        gap_px = 10
        widths = [max(90.0, m.btn_s.measure(l) + 28) for l, _ in labels]
        budget = W - 2 * self.margin
        total = sum(widths) + gap_px * (len(labels) - 1)
        if total > budget:  # restringi proporzionalmente e accorcia le etichette
            k = (budget - gap_px * (len(labels) - 1)) / sum(widths)
            widths = [w * k for w in widths]
        x = self.margin + max(0.0, (budget - (sum(widths) + gap_px * (len(labels) - 1))) / 2)
        for (lbl, e), w in zip(labels, widths):
            x += w / 2
            sel = e is self.selected
            if not e.get("writable"):
                fill, outline, fg = "#E8E4EE", "#C9C2D6", INK_SOFT
            elif sel:
                fill, outline, fg = MINT, MINT_DARK, "white"
            else:
                fill, outline, fg = CARD, "#E3D9CF", INK
            body = dense_round_rect(cv, x - w / 2, y - h / 2, x + w / 2, y + h / 2,
                                    min(12.0, h / 2 - 2), fill=fill, outline=outline, width=2)
            txt = cv.create_text(x, y, text=m.fit(lbl, m.btn_s, w - 14), fill=fg, font=m.btn_s)
            self.chip_items += [body, txt]
            for it in (body, txt):
                cv.tag_bind(it, "<Button-1>", lambda _ev, entry=e: self.select_install(entry))
            x += w / 2 + gap_px

    def _draw_secondary_pills(self) -> None:
        cv, m = self.cv, self.m
        for item in self.pill_items:
            cv.delete(item)
        self.pill_items = []
        y = self.sec_y + self.sec_h / 2
        h = self.sec_h - 4
        patchable = [e for e in self.installs
                     if e.get("writable") and e.get("lua_ready")]
        upd_info = (self.payload or {}).get("update") or {}
        pills: list[tuple[str, str, str, object]] = []
        if upd_info.get("update_available") and upd_info.get("asset"):
            pills.append((f"⬇  Aggiorna programma a v{upd_info.get('latest')}",
                          CORAL_DARK, CORAL, self.self_update_program))
        if len(patchable) >= 2:
            pills.append(("✦✦  Applica a TUTTE le installazioni", CORAL, CORAL_DARK,
                          self.apply_to_all))
        pills.append(("▸  Apri cartella gioco", SUN, SUN_DARK, self.open_game_folder))
        pills.append(("◎  Scegli cartella…", SUN, SUN_DARK, self.choose_folder))
        pills.append(("↓  Release su GitHub", SUN, SUN_DARK, self.open_releases))
        gap_px = 10
        widths = [max(110.0, m.btn_s.measure(l) + 28) for l, *_ in pills]
        budget = W - 2 * self.margin
        total = sum(widths) + gap_px * (len(pills) - 1)
        if total > budget:
            k = (budget - gap_px * (len(pills) - 1)) / sum(widths)
            widths = [w * k for w in widths]
        x = self.margin + max(0.0, (budget - (sum(widths) + gap_px * (len(pills) - 1))) / 2)
        for (lbl, color, dark, cmd), w in zip(pills, widths):
            x += w / 2
            dim = cmd is self.apply_to_all and self.busy
            body = dense_round_rect(cv, x - w / 2, y - h / 2, x + w / 2, y + h / 2,
                                    min(12.0, h / 2 - 2),
                                    fill="#DDD6E4" if dim else color,
                                    outline="#B9B1C6" if dim else dark, width=2)
            txt = cv.create_text(x, y, text=m.fit(lbl, m.btn_s, w - 14),
                                 fill="#F4F1F8" if dim else "white", font=m.btn_s)
            self.pill_items += [body, txt]
            for it in (body, txt):
                cv.tag_bind(it, "<Button-1>", lambda _ev, c=cmd: self._pill_click(c))
            x += w / 2 + gap_px

    def _pill_click(self, cmd) -> None:
        if self.busy:
            return
        if cmd:
            cmd()

    def select_install(self, entry: dict) -> None:
        if self.busy or entry is self.selected:
            return
        self.selected = entry
        settings = load_gui_settings()
        settings["selected_game_dir"] = str(entry["path"])
        save_gui_settings(settings)
        if self.payload:
            self._render_status(self.payload)

    # ------------------------------------------------------------ rendering stato
    def _render_status(self, payload: dict) -> None:
        self.payload = payload
        self.installs = payload.get("installs") or []
        settings = load_gui_settings()
        saved = str(settings.get("selected_game_dir") or "")
        self.selected = None
        for e in self.installs:
            if str(e["path"]) == saved:
                self.selected = e
                break
        if self.selected is None and self.installs:
            self.selected = self.installs[0]
        self._draw_install_chips()
        self._render_selected()
        self._draw_secondary_pills()

    def _render_buttons(self) -> None:
        sel = self.selected
        ok = bool(sel) and sel.get("writable") and sel.get("lua_ready")
        self.btn_apply.set_enabled(ok and not self.busy)
        self.btn_restore.set_enabled(ok and not self.busy)
        self.btn_refresh.set_enabled(not self.busy)
        self._draw_secondary_pills()

    def _render_selected(self) -> None:
        m = self.m
        sel = self.selected
        running_names = self.payload.get("running") or [] if self.payload else []
        running = bool(running_names)
        upd_info = (self.payload or {}).get("update") or {}
        supported = [str(v) for v in (self.manifest.get("supported_game_updates") or [])]

        if not self.installs:
            self.card_game.set("Nessuna installazione", "usa «Scegli cartella…»", CORAL)
            self.card_tr.set("—", "", SUN)
            self.card_align.set("—", "", SUN)
            self._set_hero("Nessuna installazione di Aniimo trovata — usa «Scegli cartella…»", HERO_BAD)
        elif sel is None:
            self._set_hero("Seleziona un'installazione dalla striscia sopra", HERO_WARN)
        else:
            source = SOURCE_LABELS.get(sel["source"], sel["source"])
            upd = sel.get("update") or "?"
            if running:
                self.card_game.set(f"{source} · build {upd}",
                                   f"⚠ in esecuzione: {', '.join(running_names)}", SUN)
            else:
                self.card_game.set(f"{source} · build {upd}",
                                   App.short_path(str(sel["path"])),
                                   MINT if sel.get("writable") else SUN)

            tr = sel.get("translation_installed")
            if tr is True:
                ver = sel.get("installed_translation_version") or "?"
                ratio = sel.get("translation_match_ratio")
                pct = f" · {ratio * 100:.0f}%" if isinstance(ratio, (int, float)) else ""
                self.card_tr.set(f"✓ Installata (v{ver})",
                                 f"slot {sel.get('translation_slot') or 'en'}{pct} corrisponde", MINT)
            elif tr is False:
                self.card_tr.set("Non installata", "pronta all'uso ✦", CORAL)
            else:
                self.card_tr.set("Stato incerto", "archivio non leggibile", SUN)

            unknown = sel.get("unknown_text_count")
            aligned = bool(upd != "?" and str(upd) in supported)
            if not sel.get("lua_ready"):
                self.card_align.set("Dati non scaricati", "avvia questa copia del gioco una volta", SUN)
            elif unknown:
                self.card_align.set(f"⚠ {unknown} stringhe nuove", "restano in inglese (fallback)", CORAL)
            elif aligned:
                self.card_align.set("✓ Allineata alla patch", f"build {upd} supportata e verificata", MINT)
            elif sel.get("texts_supported") is True:
                self.card_align.set("✓ Compatibile per contenuto", f"build {upd} non testata, testi identici", MINT)
            else:
                self.card_align.set("Da verificare", f"build {upd} non in lista", SUN)

            # hero per l'installazione selezionata
            if not sel.get("writable"):
                self._set_hero("Versione Microsoft Store protetta (cartelle UWP): "
                               "la traduzione non può essere applicata a questa copia", HERO_BAD)
            elif not sel.get("lua_ready"):
                self._set_hero("Questa copia non ha ancora scaricato i dati del gioco: "
                               "avviala una volta, poi applica la traduzione", HERO_WARN)
            elif running:
                self._set_hero("⚠ Aniimo è in esecuzione — chiudilo prima di applicare o ripristinare", HERO_WARN)
            elif unknown:
                self._set_hero(f"⚠ {unknown} stringhe nuove restano in inglese: "
                               f"serve un aggiornamento della traduzione", HERO_BAD)
            elif tr is False:
                self._set_hero(f"Traduzione pronta su {source} — premi «✦ Applica traduzione»", HERO_WARN)
            elif tr is True and (aligned or sel.get("texts_supported") is True):
                if upd_info.get("update_available"):
                    self._set_hero(f"✓ Tutto pronto · novità v{upd_info.get('latest')} su GitHub", HERO_WARN)
                else:
                    self._set_hero(f"✓ Tutto pronto su {source} — traduzione installata "
                                   f"e allineata alla build {upd}", HERO_OK)
            else:
                self._set_hero("Stato traduzione incerto — consulta il registro sotto", HERO_WARN)

        # card novità (globale)
        cur = upd_info.get("current", "?")
        checked = f" · controllo {upd_info['checked_at']}" if upd_info.get("checked_at") else ""
        if upd_info.get("error"):
            if upd_info.get("rate_limited"):
                self.card_news.set("Limite GitHub temporaneo",
                                   "troppe richieste: si sblocca entro un'ora", SUN)
            else:
                self.card_news.set("Controllo offline",
                                   "GitHub non raggiungibile, riprova più tardi", SUN)
        elif upd_info.get("update_available"):
            self.card_news.set(f"⚠ v{upd_info.get('latest')} disponibile",
                               "scarica dalla pagina Release", CORAL)
        else:
            self.card_news.set("✓ Traduzione aggiornata", f"versione corrente v{cur}{checked}", MINT)

        self.cv.itemconfig(self.footer, text=m.fit(
            f"installer v{self.manifest.get('translation_version', '?')} · build supportate: "
            f"{', '.join(supported) or '—'} · backup: Documenti\\AniimoItalianTranslation",
            m.foot, W - 2 * self.margin))
        self._render_buttons()

    # ------------------------------------------------------------ azioni
    def _selected_ok(self) -> bool:
        sel = self.selected
        if not sel or not sel.get("writable") or not sel.get("lua_ready"):
            messagebox.showinfo(APP_TITLE,
                                "Questa installazione non è al momento patchabile:\n"
                                "se è del Microsoft Store le cartelle sono protette, altrimenti\n"
                                "avvia quella copia del gioco una volta per scaricare i dati.")
            return False
        return True

    def apply_translation(self) -> None:
        if self.busy or not self._selected_ok():
            return
        running = inst.process_running()
        warn = "Verrà creato un backup automatico e poi applicata la traduzione italiana.\n\n"
        warn += f"Installazione: {self.selected['path']}\n\n"
        if running:
            warn += "⚠ Il gioco/launcher risulta in esecuzione: chiudilo prima di continuare.\n\n"
        warn += ("Traduzione non ufficiale: modifica file locali del client. Nessuna garanzia "
                 "contro controlli d'integrità o sanzioni sull'account (anti-cheat NetEase).")
        if not messagebox.askokcancel("Applica traduzione", warn, icon="warning"):
            return
        args = Namespace(game_dir=str(self.selected["path"]), no_update_check=True,
                         ignore_update=True, force=False, force_open=False,
                         also_english=False, target="en")
        self._run_worker(lambda: inst.cmd_install(args), "Installazione traduzione",
                         celebrate_on_success=True,
                         info_on_success="Traduzione applicata!\n\nNel gioco seleziona la lingua: Inglese.")

    def apply_to_all(self) -> None:
        if self.busy:
            return
        targets = [e for e in self.installs if e.get("writable") and e.get("lua_ready")]
        if len(targets) < 2:
            messagebox.showinfo(APP_TITLE, "Serve più di un'installazione patchabile.")
            return
        running = inst.process_running()
        warn = (f"Applicherò la traduzione a {len(targets)} installazioni in sequenza:\n\n"
                + "\n".join(f"· {e['path']}" for e in targets)
                + "\n\nBackup automatico per ciascuna.")
        if running:
            warn += "\n\n⚠ Il gioco/launcher risulta in esecuzione: chiudilo prima di continuare."
        warn += ("\n\nTraduzione non ufficiale: nessuna garanzia contro controlli d'integrità "
                 "o sanzioni sull'account (anti-cheat NetEase).")
        if not messagebox.askokcancel("Applica a tutte", warn, icon="warning"):
            return

        def job() -> int:
            codes = []
            for i, e in enumerate(targets, 1):
                print(f"[{i}/{len(targets)}] {e['path']}")
                args = Namespace(game_dir=str(e["path"]), no_update_check=True,
                                 ignore_update=True, force=False, force_open=False,
                                 also_english=False, target="en")
                try:
                    codes.append(inst.cmd_install(args))
                except Exception as exc:  # noqa: BLE001 - continua con le altre
                    print(f"✗ Errore su {e['path']}: {exc}")
                    codes.append(1)
            return 0 if all(c == 0 for c in codes) else max(codes)

        self._run_worker(job, "Installazione su tutte le installazioni",
                         celebrate_on_success=True,
                         info_on_success=f"Traduzione applicata a {len(targets)} installazioni!\n\n"
                                         "Nel gioco seleziona la lingua: Inglese.")

    def restore_backup(self) -> None:
        if self.busy or not self._selected_ok():
            return
        if not messagebox.askyesno("Ripristina backup",
                                   f"Riporto gli archivi di\n{self.selected['path']}\n"
                                   "all'ultimo backup (traduzione rimossa)?"):
            return
        args = Namespace(game_dir=str(self.selected["path"]), force_open=False)
        self._run_worker(lambda: inst.cmd_restore(args), "Ripristino backup",
                         celebrate_on_success=True,
                         info_on_success="Backup ripristinato: il gioco è tornato in inglese originale.")

    def open_game_folder(self) -> None:
        sel = self.selected
        if not sel:
            messagebox.showinfo(APP_TITLE, "Nessuna installazione selezionata.")
            return
        import webbrowser  # noqa: PLC0415
        webbrowser.open(Path(sel["path"]).as_uri())

    def choose_folder(self) -> None:
        if self.busy:
            return
        folder = filedialog.askdirectory(title="Scegli la cartella di Aniimo (contiene Aniimo.exe)")
        if not folder:
            return
        settings = load_gui_settings()
        settings["selected_game_dir"] = folder
        save_gui_settings(settings)
        try:
            inst.save_game_dir(Path(folder))
        except Exception:  # noqa: BLE001
            pass
        self._log_line(f"Cartella impostata: {folder} — rieseguo il rilevamento…")
        self.refresh_status()

    def open_github(self) -> None:
        import webbrowser  # noqa: PLC0415
        webbrowser.open("https://github.com/notorious-pizza/Aniimo-Italian-Translation")

    def open_releases(self) -> None:
        import webbrowser  # noqa: PLC0415
        webbrowser.open(((self.payload or {}).get("update") or {}).get("releases_url")
                        or "https://github.com/notorious-pizza/Aniimo-Italian-Translation/releases")

    # ------------------------------------------------------------ auto-aggiornamento programma
    def self_update_program(self) -> None:
        if self.busy:
            return
        upd_info = (self.payload or {}).get("update") or {}
        if not upd_info.get("update_available") or not upd_info.get("asset"):
            messagebox.showinfo(APP_TITLE, "Nessun aggiornamento scaricabile al momento.")
            return
        latest = upd_info.get("latest")
        if not messagebox.askokcancel(
                "Aggiorna programma",
                f"Scarico la versione {latest} da GitHub (verifica SHA-256)\n"
                "e riavvio il programma da solo.\n\nLa finestra si chiuderà al termine del download."):
            return

        def job() -> int:
            status = {k: upd_info[k] for k in ("current", "latest", "releases_url", "asset")}
            return 0 if inst.schedule_self_update(status) else 1

        def after_download() -> None:
            self._log_line("Download pronto: chiudo la finestra per completare l'aggiornamento…")
            self.root.after(900, self._on_close)

        self._run_worker(job, "Aggiornamento programma", refresh_after=False,
                         on_success=after_download)

    # ------------------------------------------------------------ musica & festa
    def toggle_music(self, force_on: bool = False) -> None:
        if not HAVE_WINSOUND:
            self.music_on = False
            self.music_btn.set_enabled(False)
            self.music_btn.set_label("Musica —")
            return
        self.music_on = force_on or not self.music_on
        if self.music_on:
            self._start_music()
        else:
            winsound.PlaySound(None, winsound.SND_PURGE)
        self.music_btn.set_label("Musica ♪" if self.music_on else "Musica ✕")
        self.music_btn.set_style(MINT if self.music_on else "#CFC8DA",
                                 MINT_DARK if self.music_on else "#B9B1C6")
        save_gui_settings({"music_on": self.music_on})

    def celebrate(self) -> None:
        self.celebrate_until = time.time() + 2.2
        for _ in range(46):
            x = random.uniform(30, W - 30)
            item = self.cv.create_rectangle(x, self.header_y + self.header_h,
                                            x + random.uniform(4, 9), self.header_y + self.header_h + 14,
                                            fill=random.choice([CORAL, MINT, LAV, SUN, SKY]), outline="")
            self.cv.tag_raise(item)
            self.confetti.append((item, random.uniform(-2.4, 2.4), random.uniform(-3.0, 0.0)))


def self_screenshot(root: tk.Tk, out_path: str) -> bool:
    """Cattura la propria finestra con PrintWindow (modalità sviluppo, richiede Pillow)."""
    try:
        import ctypes.wintypes as wt
        from PIL import Image
    except ImportError:
        return False
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    root.update_idletasks()
    root.update()
    hwnd = root.winfo_id()
    while user32.GetParent(hwnd):
        hwnd = user32.GetParent(hwnd)
    rect = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = max(1, rect.right - rect.left), max(1, rect.bottom - rect.top)
    hdc = user32.GetWindowDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mem, bmp)
    for _ in range(3):
        root.update()
        user32.PrintWindow(hwnd, mem, 2)
    user32.InvalidateRect(hwnd, None, True)
    root.update()
    user32.PrintWindow(hwnd, mem, 2)

    class BMI(ctypes.Structure):
        _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG),
                    ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                    ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", wt.LONG),
                    ("biYPelsPerMeter", wt.LONG), ("biClrUsed", wt.DWORD),
                    ("biClrImportant", wt.DWORD)]

    bmi = BMI()
    bmi.biSize = ctypes.sizeof(BMI)
    bmi.biWidth, bmi.biHeight = w, -h
    bmi.biPlanes, bmi.biBitCount, bmi.biCompression = 1, 32, 0
    buf = (ctypes.c_char * (w * h * 4))()
    gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bmi), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(hwnd, hdc)
    img = Image.frombytes("RGBA", (w, h), bytes(buf), "raw", "BGRA", 0, 1)
    img.convert("RGB").save(out_path)
    return True


def main() -> int:
    enable_dpi_awareness()
    # fase interna di auto-aggiornamento: questo processo è il NUOVO exe scaricato
    # e deve sostituire il vecchio prima di riaprirlo (stesso meccanismo dell'installer CLI)
    if len(sys.argv) > 1 and sys.argv[1] == inst.UPDATE_APPLY_COMMAND:
        import argparse  # noqa: PLC0415
        internal = argparse.ArgumentParser(add_help=False)
        internal.add_argument(inst.UPDATE_APPLY_COMMAND)
        internal.add_argument("--target-exe", required=True)
        internal.add_argument("--previous-version", default="")
        try:
            return inst.cmd_apply_update(internal.parse_args())
        except Exception:  # noqa: BLE001
            return 1

    update_completed = len(sys.argv) > 1 and sys.argv[1] == inst.UPDATE_COMPLETE_COMMAND
    previous_version = sys.argv[2] if update_completed and len(sys.argv) > 2 else ""

    smoke = "--smoke" in sys.argv
    foto = sys.argv[sys.argv.index("--foto") + 1] if "--foto" in sys.argv else None
    check_only = "--check" in sys.argv
    root = tk.Tk()
    app = App(root, smoke=smoke or bool(foto) or check_only, defer_status=check_only)
    if update_completed and not smoke:
        app._log_line(f"✓ Programma aggiornato all'ultima versione"
                      + (f" (precedente v{previous_version})" if previous_version else "")
                      + ".")

    if check_only:
        problems = app.check_overlaps()
        for p in problems:
            print("OVERLAP:", p)
        print("OVERLAPS:", len(problems), "| altezza calcolata:", app.total_h)
        root.destroy()
        return 1 if problems else 0

    if foto:
        def scatta() -> None:
            time.sleep(12.0)  # lascia completare il rilevamento installazioni
            for _ in range(30):
                root.update()
                time.sleep(0.1)
            ok = self_screenshot(root, foto)
            print("FOTO:", "OK" if ok else "FALLITA")
            root.destroy()
        threading.Thread(target=scatta, daemon=True).start()
    elif smoke:
        root.after(1500, root.destroy)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
