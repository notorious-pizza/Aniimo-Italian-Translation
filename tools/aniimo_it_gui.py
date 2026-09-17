#!/usr/bin/env python3
"""Aniimo — Traduzione Italiana · Centro di controllo grafico.

Interfaccia amichevole (Tkinter, solo standard library) per:
- vedere se la traduzione è allineata alla patch di Aniimo installata;
- vedere se la traduzione è già applicata e con quale versione;
- applicare la traduzione o ripristinare il backup con un clic;
- controllare le novità su GitHub.

Riusa le stesse funzioni testate dell'installer CLI (tools/aniimo_it_installer.py):
nessuna logica duplicata. Musica: mini-tema chiptune sintetizzato al volo.
"""

from __future__ import annotations

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
from tkinter import filedialog, messagebox

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import aniimo_it_installer as inst  # noqa: E402

try:
    import winsound
    HAVE_WINSOUND = True
except ImportError:  # sviluppo fuori Windows
    HAVE_WINSOUND = False

APP_TITLE = "Aniimo · Traduzione Italiana — Centro di controllo"
W, H = 800, 700
GUI_SETTINGS = inst.USER_WORK_DIR / "gui_settings.json"
THEME_WAV = inst.USER_WORK_DIR / "theme.wav"

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

NOTE_FREQ = {
    "F3": 174.61, "G3": 196.00, "A3": 220.00, "C3": 130.81,
    "A4": 440.00, "C5": 523.25, "D5": 587.33, "E5": 659.25, "G5": 783.99, "A5": 880.00,
    "C6": 1046.50, "E6": 1318.51, "G6": 1567.98,
}


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

    # melodia allegra in pentatonica di Do maggiore (None = pausa)
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
    # basso: Do - Do - Lam - Lam - Fa - Fa - Sol - Sol (una battuta ciascuno)
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
    for bar in range(8):  # luccichio sull'ultimo ottavo di battuta
        add_note(NOTE_FREQ[("C6", "E6", "G6")[bar % 3]], (bar * 8 + 7) * eighth, eighth * 0.8, 0.05)

    peak = max(1e-9, max(abs(v) for v in buf))
    scale = 0.22 * 32767.0 / peak
    frames = bytearray()
    for v in buf:
        sample = int(max(-32767.0, min(32767.0, v * scale)))
        frames += struct.pack("<h", sample)
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


def rounded_rect(cv: tk.Canvas, x1, y1, x2, y2, r, **kw) -> int:
    pts = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
        x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return cv.create_polygon(pts, smooth=True, **kw)


class RoundButton:
    """Pulsante disegnato su canvas, con hover e stato disabilitato."""

    def __init__(self, cv: tk.Canvas, x, y, w, h, label, color, dark, cmd, *, font=("Segoe UI", 11, "bold")):
        self.cv, self.x, self.y, self.w, self.h = cv, x, y, w, h
        self.color, self.dark, self.cmd = color, dark, cmd
        self.enabled = True
        self.r = min(16.0, h / 2)
        self.body = rounded_rect(cv, x - w / 2, y - h / 2, x + w / 2, y + h / 2, self.r,
                                 fill=color, outline=dark, width=2)
        self.txt = cv.create_text(x, y, text=label, fill="white", font=font)
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


class Card:
    """Card di stato: badge colorato, titolo, riga principale e sottotitolo."""

    def __init__(self, cv: tk.Canvas, x1, y1, x2, y2, icon: str, title: str):
        self.cv = cv
        rounded_rect(cv, x1, y1, x2, y2, 18, fill=CARD, outline="#EFE6DC", width=2)
        cx = x1 + 36
        self.badge = cv.create_oval(cx - 15, y1 + 20, cx + 15, y1 + 50, fill=SUN, outline="")
        cv.create_text(cx, y1 + 35, text=icon, font=("Segoe UI Symbol", 14, "bold"), fill="white")
        cv.create_text(x1 + 60, y1 + 16, text=title, anchor="nw", font=("Segoe UI", 10, "bold"), fill=INK_SOFT)
        self.value = cv.create_text(x1 + 60, y1 + 38, text="…", anchor="nw", font=("Segoe UI", 13, "bold"), fill=INK)
        self.sub = cv.create_text(x1 + 18, y2 - 12, text="", anchor="sw", font=("Segoe UI", 9), fill=INK_SOFT)

    def set(self, value: str, sub: str = "", color: str = SUN) -> None:
        self.cv.itemconfig(self.value, text=value)
        self.cv.itemconfig(self.sub, text=sub)
        self.cv.itemconfig(self.badge, fill=color)


class App:
    def __init__(self, root: tk.Tk, smoke: bool = False) -> None:
        self.root = root
        self.smoke = smoke
        self.q: "queue.Queue[tuple]" = queue.Queue()
        self.busy = False
        self.status: dict | None = None
        self.music_on = bool(load_gui_settings().get("music_on", True))
        self.t0 = time.time()
        self.blink_at = time.time() + 3.0
        self.blink_closing = False
        self.celebrate_until = 0.0
        self.mascot_dy = 0.0
        self.confetti: list[tuple[int, float, float]] = []

        root.title(APP_TITLE)
        root.resizable(False, False)
        root.configure(bg=CREAM)
        # centra la finestra e portala in primo piano all'avvio
        root.update_idletasks()
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{W}x{H}+{(sw - W) // 2}+{max(0, (sh - H) // 2 - 20)}")
        root.attributes("-topmost", True)
        root.after(2500, lambda: root.attributes("-topmost", False))
        try:
            root.iconbitmap(str(TOOLS_DIR.parent / "assets" / "aniimo-italian-installer-icon.ico"))
        except tk.TclError:
            pass

        self.cv = tk.Canvas(root, width=W, height=H, bg=CREAM, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)

        self._build_layout()
        self._spawn_bubbles()
        self._build_mascot(96, 84)

        # log in stile console, incorporato nel canvas
        self.log = tk.Text(self.root, bg=LOG_BG, fg="#EDE6F7", relief="flat", height=8,
                           font=("Consolas", 9), wrap="word", state="disabled",
                           padx=10, pady=6, highlightthickness=0)
        rounded_rect(self.cv, 24, H - 212, W - 24, H - 32, 18, fill=LOG_BG, outline="#241D33", width=2)
        self.log_title = self.cv.create_text(42, H - 202, text="Registro attività",
                                             anchor="nw", font=("Segoe UI", 9, "bold"), fill="#B9AFD6")
        self.cv.create_window(W // 2, H - 118, window=self.log, width=W - 68, height=132)

        root.after(80, self._poll)
        root.after(50, self._tick)
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

    # ------------------------------------------------------------------ UI
    def _build_layout(self) -> None:
        cv = self.cv
        rounded_rect(cv, 18, 14, W - 18, 148, 22, fill=CARD, outline="#EFE6DC", width=2)
        cv.create_text(178, 34, text="Traduzione Italiana", anchor="nw",
                       font=("Segoe UI", 21, "bold"), fill=INK)
        cv.create_text(178, 72, text="Centro di controllo · fork notorious-pizza · traduzione originale di Sici29",
                       anchor="nw", font=("Segoe UI", 10), fill=INK_SOFT)
        cv.create_text(178, 98, text="Nel gioco seleziona: Inglese",
                       anchor="nw", font=("Segoe UI", 10, "italic"), fill=CORAL_DARK)

        self.music_btn = RoundButton(cv, W - 76, 48, 84, 34, "Musica ♪", MINT, MINT_DARK,
                                     self.toggle_music, font=("Segoe UI", 10, "bold"))
        self.gh_btn = RoundButton(cv, W - 76, 92, 84, 34, "GitHub", LAV, LAV_DARK,
                                  self.open_github, font=("Segoe UI", 10, "bold"))

        x1, y1, x2 = 24, 168, W - 24
        gap, ch = 14, 80
        cw = (x2 - x1 - gap) / 2
        self.card_game = Card(cv, x1, y1, x1 + cw, y1 + ch, "◆", "Gioco rilevato")
        self.card_tr = Card(cv, x1 + cw + gap, y1, x2, y1 + ch, "✦", "Traduzione")
        self.card_align = Card(cv, x1, y1 + ch + gap, x1 + cw, y1 + 2 * ch + gap, "⬡", "Allineamento patch")
        self.card_news = Card(cv, x1 + cw + gap, y1 + ch + gap, x2, y1 + 2 * ch + gap, "✧", "Novità traduzione")

        by = 396
        self.btn_refresh = RoundButton(cv, 122, by, 180, 46, "↻  Aggiorna stato", MINT, MINT_DARK, self.refresh_status)
        self.btn_apply = RoundButton(cv, 352, by, 226, 54, "✦  Applica traduzione", CORAL, CORAL_DARK,
                                     self.apply_translation)
        self.btn_restore = RoundButton(cv, 576, by, 196, 46, "♻  Ripristina backup", LAV, LAV_DARK,
                                       self.restore_backup)
        self.btn_folder = RoundButton(cv, 152, by + 44, 240, 34, "▸  Apri cartella gioco", SUN, SUN_DARK,
                                      self.open_game_folder, font=("Segoe UI", 9, "bold"))
        self.btn_pick = RoundButton(cv, 304, by + 44, 200, 34, "◎  Scegli cartella…", SUN, SUN_DARK,
                                    self.choose_folder, font=("Segoe UI", 9, "bold"))
        self.btn_releases = RoundButton(cv, 470, by + 44, 210, 34, "↓  Release su GitHub", SUN, SUN_DARK,
                                        self.open_releases, font=("Segoe UI", 9, "bold"))

        self.footer = cv.create_text(W // 2, H - 16, text="", font=("Segoe UI", 8), fill=INK_SOFT)

    def _spawn_bubbles(self) -> None:
        self.bubbles = []
        for _ in range(14):
            r = random.uniform(6, 16)
            x = random.uniform(10, W - 10)
            y = random.uniform(160, H - 60)
            item = self.cv.create_oval(x - r, y - r, x + r, y + r,
                                       fill=random.choice(BUBBLE_COLORS), outline="")
            self.cv.tag_lower(item)
            self.bubbles.append((item, random.uniform(0.15, 0.5), random.uniform(-0.3, 0.3)))

    def _build_mascot(self, mx: float, my: float) -> None:
        """Piccola creatura tonda in stile Aniimo: orecchie, fogliolina, blush."""
        cv = self.cv
        self.mx, self.my = mx, my
        items: list[int] = []
        for sx in (-1, 1):  # orecchie (sotto il corpo nel z-order)
            items.append(cv.create_polygon(mx + sx * 26, my - 18, mx + sx * 42, my - 56, mx + sx * 8, my - 28,
                                           smooth=True, fill="#FFE0E9", outline="#F3B7C8", width=3))
        items.append(cv.create_line(mx, my - 28, mx, my - 42, width=3, fill="#7FBF8E"))  # gambo foglia
        items.append(cv.create_oval(mx - 12, my - 56, mx + 10, my - 40,
                                    fill="#9FE0AE", outline="#7FBF8E", width=2))
        items.append(cv.create_oval(mx - 42, my - 32, mx + 42, my + 46,
                                    fill="#FFE0E9", outline="#F3B7C8", width=3))  # corpo
        items.append(cv.create_oval(mx - 24, my + 4, mx + 24, my + 44, fill="#FFF7FA", outline=""))  # pancia
        self.m_eyes = [
            cv.create_oval(mx - 21, my - 9, mx - 11, my + 1, fill=INK, outline=""),
            cv.create_oval(mx + 11, my - 9, mx + 21, my + 1, fill=INK, outline=""),
        ]
        self.m_eyes_happy = [
            cv.create_arc(mx - 22, my - 7, mx - 10, my + 5, start=20, extent=140, style="arc",
                          width=2, state="hidden"),
            cv.create_arc(mx + 10, my - 7, mx + 22, my + 5, start=20, extent=140, style="arc",
                          width=2, state="hidden"),
        ]
        items.append(cv.create_oval(mx - 31, my + 7, mx - 19, my + 15, fill="#FFB9CC", outline=""))  # blush
        items.append(cv.create_oval(mx + 19, my + 7, mx + 31, my + 15, fill="#FFB9CC", outline=""))
        items.append(cv.create_arc(mx - 7, my + 9, mx + 7, my + 19, start=20, extent=140,
                                   style="arc", width=2))  # sorriso ^ ^
        self.m_group = items + self.m_eyes + self.m_eyes_happy
        for item in items:
            self.cv.tag_raise(item)

    # ------------------------------------------------------------ animazione
    def _tick(self) -> None:
        now = time.time()
        # bolle che salgono lente, riappaiono in basso
        for item, vy, wob in self.bubbles:
            self.cv.move(item, wob * 0.6, -vy)
            x1b, y1b, _, y2b = self.cv.bbox(item)
            if y2b < 152 or x1b < -20 or x1b > W + 20:
                self.cv.move(item, -wob * 0.6 + random.uniform(-8, 8), H - 40 - y1b)

        # mascotte: respiro + saltelli di gioia
        happy = now < self.celebrate_until
        bob = math.sin((now - self.t0) * 2.2) * 4
        if happy:
            bob -= abs(math.sin((now - self.t0) * 7.0)) * 16
        dy = bob - self.mascot_dy
        if dy:
            self.mascot_dy = bob
            for item in self.m_group:
                self.cv.move(item, 0, dy)

        # blink periodale; occhi a falce quando festeggia
        if happy:
            show, happy_show = "hidden", "normal"
        elif now >= self.blink_at:
            show, happy_show = "hidden", "hidden"  # occhi chiusi = entrambi nascosti per un istante
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

        # confetti in caduta
        if self.confetti:
            alive = []
            for item, vx, vy in self.confetti:
                vy += 0.35
                self.cv.move(item, vx, vy)
                _, y1c, _, _ = self.cv.bbox(item)
                if y1c < H + 20:
                    alive.append((item, vx, vy))
                else:
                    self.cv.delete(item)
            self.confetti = alive
        self.root.after(50, self._tick)

    def _poll(self) -> None:
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
        self.root.after(80, self._poll)

    # ------------------------------------------------------------ thread worker
    def _run_worker(self, fn, label: str, *, celebrate_on_success: bool = False,
                    info_on_success: str | None = None, refresh_after: bool = True) -> None:
        if self.busy:
            return
        self.busy = True
        for b in (self.btn_refresh, self.btn_apply, self.btn_restore, self.btn_pick):
            b.set_enabled(False)
        self.cv.itemconfig(self.log_title, text=f"Registro attività · {label} in corso…")
        self._log_line(f"— {label} —")

        def worker() -> None:
            old_stdout = sys.stdout
            code: int | None = None
            err: str | None = None
            try:
                # il redirect cattura le print dell'installer; ristretto alla sola
                # chiamata per non toccare lo stdout globale più del necessario
                sys.stdout = QueueWriter(self.q)
                code = fn()
            except Exception as exc:  # noqa: BLE001
                err = f"{type(exc).__name__}: {exc}"
            finally:
                sys.stdout = old_stdout
            self.q.put(("done", {"label": label, "code": code, "err": err,
                                "celebrate": celebrate_on_success, "info": info_on_success,
                                "refresh": refresh_after}))

        threading.Thread(target=worker, daemon=True).start()

    def _work_done(self, info: dict) -> None:
        self.busy = False
        for b in (self.btn_refresh, self.btn_apply, self.btn_restore, self.btn_pick):
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
        elif info["code"] is not None:
            self._log_line(f"! {info['label']} interrotto (codice {info['code']}). Leggi il registro.")
        if info["refresh"]:
            self.refresh_status()

    def _log_line(self, text: str) -> None:
        self.q.put(("log", text))

    # ------------------------------------------------------------ stato
    def refresh_status(self) -> None:
        if self.busy:
            return
        self.card_game.set("Rilevo il gioco…", "un attimo ✧", SKY)

        def job() -> int:
            status = inst.collect_startup_status()
            self.q.put(("status", status))
            return 0

        self._run_worker(job, "Rilevamento stato", refresh_after=False)

    def _render_status(self, status: dict) -> None:
        self.status = status
        manifest = status.get("manifest", {})
        game_dir = status.get("game_dir")

        if not game_dir:
            self.card_game.set("Gioco non trovato", "usa «Scegli cartella…»", CORAL)
        else:
            upd = status.get("detected_game_update") or "?"
            running = inst.process_running()
            if running:
                self.card_game.set(f"Build {upd}", f"⚠ in esecuzione: {', '.join(running)}", SUN)
            else:
                self.card_game.set(f"Build {upd}", str(game_dir), MINT)

        tr = status.get("translation_installed")
        if tr is True:
            ver = status.get("installed_translation_version") or "?"
            ratio = status.get("translation_match_ratio")
            pct = f" · {ratio * 100:.0f}% corrisponde" if isinstance(ratio, (int, float)) else ""
            self.card_tr.set(f"✓ Installata (v{ver})",
                             f"slot {status.get('translation_slot') or 'en'}{pct}", MINT)
        elif tr is False:
            self.card_tr.set("Non installata", "pronta all'uso ✦", CORAL)
        else:
            self.card_tr.set("Stato incerto", "archivio non leggibile", SUN)

        supported = [str(v) for v in (manifest.get("supported_game_updates") or [])]
        upd = status.get("detected_game_update")
        unknown = status.get("unknown_text_count")
        if not game_dir:
            self.card_align.set("—", "gioco non rilevato", SUN)
        elif unknown:
            self.card_align.set(f"⚠ {unknown} stringhe nuove", "restano in inglese (fallback)", CORAL)
        elif upd and str(upd) in supported:
            self.card_align.set("✓ Allineata alla patch", f"build {upd} supportata e verificata", MINT)
        elif status.get("text_resources_supported") is True:
            self.card_align.set("✓ Compatibile per contenuto", f"build {upd} non testata, testi identici", MINT)
        else:
            self.card_align.set("Da verificare", f"build {upd} non in lista", SUN)

        upd_info = status.get("update") or {}
        cur = upd_info.get("current", "?")
        if upd_info.get("error"):
            self.card_news.set("Offline", "controllo novità non disponibile", SUN)
        elif upd_info.get("update_available"):
            self.card_news.set(f"⚠ v{upd_info.get('latest')} disponibile",
                               "scarica dalla pagina Release", CORAL)
        else:
            self.card_news.set("✓ Traduzione aggiornata", f"versione corrente v{cur}", MINT)

        self.cv.itemconfig(self.footer, text=(
            f"installer v{manifest.get('translation_version', '?')} · build supportate: "
            f"{', '.join(supported) or '—'} · backup in {inst.USER_WORK_DIR / 'backups'}"
        ))

    # ------------------------------------------------------------ azioni
    def apply_translation(self) -> None:
        running = inst.process_running()
        warn = "Verrà creato un backup automatico e poi applicata la traduzione italiana.\n\n"
        if running:
            warn += "⚠ Il gioco/launcher risulta in esecuzione: chiudilo prima di continuare.\n\n"
        warn += ("Traduzione non ufficiale: modifica file locali del client. Nessuna garanzia "
                 "contro controlli d'integrità o sanzioni sull'account (anti-cheat NetEase).")
        if not messagebox.askokcancel("Applica traduzione", warn, icon="warning"):
            return
        args = Namespace(game_dir=None, no_update_check=True, ignore_update=True,
                         force=False, force_open=False, also_english=False, target="en")
        self._run_worker(lambda: inst.cmd_install(args), "Installazione traduzione",
                         celebrate_on_success=True,
                         info_on_success="Traduzione applicata!\n\nNel gioco seleziona la lingua: Inglese.")

    def restore_backup(self) -> None:
        if not messagebox.askyesno("Ripristina backup",
                                   "Riporto gli archivi del gioco all'ultimo backup\n(traduzione rimossa)?"):
            return
        args = Namespace(game_dir=None, force_open=False)
        self._run_worker(lambda: inst.cmd_restore(args), "Ripristino backup",
                         celebrate_on_success=True,
                         info_on_success="Backup ripristinato: il gioco è tornato in inglese originale.")

    def open_game_folder(self) -> None:
        game_dir = (self.status or {}).get("game_dir")
        if not game_dir:
            messagebox.showinfo(APP_TITLE,
                                "Gioco non ancora rilevato:\npremi «Aggiorna stato» o scegli la cartella.")
            return
        import webbrowser  # noqa: PLC0415
        webbrowser.open(game_dir.as_uri())

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="Scegli la cartella di Aniimo (contiene Aniimo.exe)")
        if folder:
            inst.save_game_dir(Path(folder))
            self._log_line(f"Cartella impostata: {folder}")
            self.refresh_status()

    def open_github(self) -> None:
        import webbrowser  # noqa: PLC0415
        webbrowser.open("https://github.com/notorious-pizza/Aniimo-Italian-Translation")

    def open_releases(self) -> None:
        import webbrowser  # noqa: PLC0415
        webbrowser.open(((self.status or {}).get("update") or {}).get("releases_url")
                        or "https://github.com/notorious-pizza/Aniimo-Italian-Translation/releases")

    # ------------------------------------------------------------ musica & festa
    def toggle_music(self, force_on: bool = False) -> None:
        if not HAVE_WINSOUND:
            self.music_on = False
            self.music_btn.set_enabled(False)
            return
        self.music_on = force_on or not self.music_on
        if self.music_on:
            self._start_music()
        else:
            winsound.PlaySound(None, winsound.SND_PURGE)
        save_gui_settings({"music_on": self.music_on})

    def celebrate(self) -> None:
        self.celebrate_until = time.time() + 2.2
        for _ in range(46):
            x = random.uniform(30, W - 30)
            item = self.cv.create_rectangle(x, 150, x + random.uniform(4, 9), 164,
                                            fill=random.choice([CORAL, MINT, LAV, SUN, SKY]), outline="")
            self.cv.tag_raise(item)
            self.confetti.append((item, random.uniform(-2.4, 2.4), random.uniform(-3.0, 0.0)))


def main() -> int:
    smoke = "--smoke" in sys.argv
    root = tk.Tk()
    App(root, smoke=smoke)
    if smoke:
        root.after(1500, root.destroy)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
