"""Min-Max (XOX) mäng AI vastu, koos skoori, ajaloo ja AI arvutuskoormuse näitajaga.

Kujundus: kirsiõie (sakura) teema värvides #d52a63 / #e59693 / #621027,
koos langevate kirsiõite animatsiooniga.

Käivitamine: py main.py  (või topeltklõps Kaivita_mang.bat failil)
"""

import json
import os
import random
import time
import tkinter as tk
from tkinter import ttk
from datetime import datetime

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ajalugu.json")
MAX_HISTORY = 200           # kui palju tulemusi failis säilitada
VISIBLE_HISTORY = 10        # kui palju viimast mängu näidatakse akna peal

PLAYER = "X"
AI = "O"

WIN_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
]

# ---------- Kirsiõie värvipalett ----------
ACCENT = "#d52a63"        # elav roosa-punane — nupud, rõhuasetused
ACCENT_SOFT = "#e59693"   # pehme roosa — taustad, õrnad detailid
ACCENT_DARK = "#621027"   # sügav bordoo — tekst, raamid
ACCENT_HOVER = "#aa224f"  # tumedam roosa — hõljutus/vajutus
BG_LIGHT = "#fbeced"      # väga õrn roosakas aknataust
PANEL_BG = "#f6d9d8"      # paneelide taust
CELL_BG = "#fffafa"       # mängulahtri taust
DRAW_TEXT = "#8a4a4f"     # viigi teate toon (palett, tumendatud)

# ---------- Fondid ----------
FONT_TITLE = ("Segoe Script", 24, "bold")      # kaunistuslik pealkiri
FONT_STATUS = ("Segoe Script", 14, "bold")     # mängu olek
FONT_UI = ("Candara", 10)                      # üldine liidese font
FONT_UI_BOLD = ("Candara", 10, "bold")
FONT_HEADER = ("Candara", 11, "bold")
FONT_CELL = ("Candara", 30, "bold")            # X / O lahtrites
FONT_LIST = ("Candara", 9)


def check_winner(board):
    for a, b, c in WIN_LINES:
        if board[a] != " " and board[a] == board[b] == board[c]:
            return board[a]
    if " " not in board:
        return "DRAW"
    return None


def find_winning_line(board):
    for a, b, c in WIN_LINES:
        if board[a] != " " and board[a] == board[b] == board[c]:
            return (a, b, c)
    return None


class AIStats:
    """Peab arvet AI viimase käigu ja kogu mängu arvutuskoormuse üle."""

    def __init__(self):
        self.last_nodes = 0
        self.last_time_ms = 0.0
        self.total_nodes = 0
        self.max_seen_nodes = 1  # nulliga jagamise vältimiseks

    def reset_game(self):
        self.last_nodes = 0
        self.last_time_ms = 0.0
        self.total_nodes = 0

    def record_move(self, nodes, elapsed_ms):
        self.last_nodes = nodes
        self.last_time_ms = elapsed_ms
        self.total_nodes += nodes
        self.max_seen_nodes = max(self.max_seen_nodes, nodes)


class PetalField:
    """Langevate kirsiõie õite (sakura) animatsioon ühel Canvasel."""

    PETAL_COLORS = (ACCENT, ACCENT_SOFT, "#f3c3c0", ACCENT_DARK)

    def __init__(self, canvas, count=10):
        self.canvas = canvas
        self.petals = []
        for _ in range(count):
            self.petals.append(self._make_petal(random_y=True))
        self.canvas.bind("<Configure>", lambda e: None)
        self._animate()

    def _make_petal(self, random_y=False):
        w = max(self.canvas.winfo_width(), 40)
        x = random.uniform(0, w)
        y = random.uniform(0, 600) if random_y else -10
        size = random.uniform(5, 10)
        speed = random.uniform(0.6, 1.6)
        drift = random.uniform(-0.6, 0.6)
        phase = random.uniform(0, 6.28)
        color = random.choice(self.PETAL_COLORS)
        item = self.canvas.create_oval(x, y, x + size, y + size * 0.8, fill=color, outline="")
        return {"item": item, "x": x, "y": y, "size": size, "speed": speed,
                "drift": drift, "phase": phase}

    def _animate(self):
        h = max(self.canvas.winfo_height(), 400)
        w = max(self.canvas.winfo_width(), 40)
        for p in self.petals:
            p["phase"] += 0.05
            p["y"] += p["speed"]
            p["x"] += p["drift"] + 0.4 * (0.5 - random.random())
            if p["y"] > h:
                p["y"] = -10
                p["x"] = random.uniform(0, w)
            self.canvas.coords(
                p["item"], p["x"], p["y"], p["x"] + p["size"], p["y"] + p["size"] * 0.8
            )
        self.canvas.after(45, self._animate)


class MinimaxApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🌸 Min-Max XOX mäng 🌸")
        self.resizable(False, False)
        self.configure(bg=BG_LIGHT)

        self.board = [" "] * 9
        self.buttons = []
        self.game_over = False
        self.starter = PLAYER  # kes alustab järgmist mängu (vahetub iga mängu järel)
        self.stats = AIStats()
        self.difficulty = tk.StringVar(value="Raske (täis minimax)")
        self.history = self.load_history()

        self._build_style()
        self._build_ui()
        self._new_game()

    # ---------- Püsisalvestus ----------
    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def save_history(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history[-MAX_HISTORY:], f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    # ---------- Stiil ----------
    def _build_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(".", background=BG_LIGHT, font=FONT_UI, foreground=ACCENT_DARK)
        style.configure("TFrame", background=BG_LIGHT)
        style.configure("TLabel", background=BG_LIGHT, foreground=ACCENT_DARK, font=FONT_UI)

        style.configure(
            "TLabelframe", background=PANEL_BG, bordercolor=ACCENT_SOFT,
            relief="groove", borderwidth=2,
        )
        style.configure(
            "TLabelframe.Label", background=PANEL_BG, foreground=ACCENT_DARK,
            font=FONT_HEADER,
        )

        style.configure(
            "TButton", background=ACCENT, foreground="white", font=FONT_UI_BOLD,
            padding=6, relief="flat", borderwidth=0,
        )
        style.map(
            "TButton",
            background=[("active", ACCENT_HOVER), ("disabled", ACCENT_SOFT)],
            foreground=[("disabled", "#ffffff")],
        )

        style.configure(
            "TCombobox", fieldbackground=CELL_BG, background=PANEL_BG,
            foreground=ACCENT_DARK, arrowcolor=ACCENT_DARK,
        )
        style.map("TCombobox", fieldbackground=[("readonly", CELL_BG)])

        style.configure(
            "Petal.Horizontal.TProgressbar", troughcolor=PANEL_BG,
            background=ACCENT, bordercolor=PANEL_BG, lightcolor=ACCENT, darkcolor=ACCENT,
        )

        style.configure(
            "Vertical.TScrollbar", background=ACCENT_SOFT, troughcolor=PANEL_BG,
            arrowcolor=ACCENT_DARK,
        )

    # ---------- UI ----------
    def _build_ui(self):
        # ---- Ülemine kaunistusriba kirsiõitega ----
        banner = tk.Canvas(self, height=70, bg=ACCENT_SOFT, highlightthickness=0)
        banner.grid(row=0, column=0, columnspan=3, sticky="ew")
        title_item = banner.create_text(
            0, 35, text="🌸  Min-Max XOX mäng  🌸",
            font=FONT_TITLE, fill=ACCENT_DARK,
        )
        PetalField(banner, count=14)

        # ---- Vasak kaunistusriba ----
        left_petals = tk.Canvas(self, width=42, height=560, bg=BG_LIGHT, highlightthickness=0)
        left_petals.grid(row=1, column=0, sticky="ns")
        PetalField(left_petals, count=8)

        # ---- Keskmine sisu ----
        root = tk.Frame(self, bg=BG_LIGHT, padx=14, pady=12)
        root.grid(row=1, column=1, sticky="nsew")

        # ---- Vasak: mängulaud ----
        board_frame = tk.Frame(root, bg=BG_LIGHT)
        board_frame.grid(row=0, column=0, rowspan=3, padx=(0, 16))

        for i in range(9):
            btn = tk.Button(
                board_frame, text=" ", font=FONT_CELL,
                width=4, height=2,
                bg=CELL_BG, fg=ACCENT_DARK,
                activebackground=ACCENT_SOFT,
                relief="ridge", borderwidth=2,
                highlightbackground=ACCENT_SOFT,
                command=lambda i=i: self._on_cell_click(i),
            )
            btn.grid(row=i // 3, column=i % 3, padx=3, pady=3)
            btn.bind("<Enter>", lambda e, i=i: self._on_cell_hover(i, True))
            btn.bind("<Leave>", lambda e, i=i: self._on_cell_hover(i, False))
            self.buttons.append(btn)

        self.status_label = tk.Label(
            board_frame, text="", font=FONT_STATUS, bg=BG_LIGHT, fg=ACCENT_DARK,
        )
        self.status_label.grid(row=3, column=0, columnspan=3, pady=(10, 0))

        controls = tk.Frame(board_frame, bg=BG_LIGHT)
        controls.grid(row=4, column=0, columnspan=3, pady=(8, 0), sticky="ew")
        tk.Label(controls, text="Raskusaste:", bg=BG_LIGHT, fg=ACCENT_DARK, font=FONT_UI).pack(side="left")
        diff_box = ttk.Combobox(
            controls, textvariable=self.difficulty, state="readonly", width=20,
            values=["Lihtne (2 käiku ette)", "Keskmine (4 käiku ette)", "Raske (täis minimax)"],
        )
        diff_box.pack(side="left", padx=6)
        diff_box.current(2)

        ttk.Button(board_frame, text="🌸 Uus mäng", command=self._new_game).grid(
            row=5, column=0, columnspan=3, pady=(10, 0), sticky="ew"
        )

        # ---- Parem: skoor + juhtseis ----
        right = tk.Frame(root, bg=BG_LIGHT)
        right.grid(row=0, column=1, sticky="nsew")

        score_box = ttk.LabelFrame(right, text="🌸 Skoor", padding=8)
        score_box.pack(fill="x", pady=(0, 8))
        self.score_label = tk.Label(score_box, text="", font=FONT_UI, bg=PANEL_BG, fg=ACCENT_DARK)
        self.score_label.pack(anchor="w")
        self.lead_label = tk.Label(score_box, text="", font=FONT_UI_BOLD, bg=PANEL_BG)
        self.lead_label.pack(anchor="w", pady=(4, 0))

        # ---- AI arvutuskoormus ("mahtu") ----
        load_box = ttk.LabelFrame(right, text="🌸 AI arvutuskoormus", padding=8)
        load_box.pack(fill="x", pady=(0, 8))

        tk.Label(load_box, text="Viimane käik:", bg=PANEL_BG, fg=ACCENT_DARK, font=FONT_UI).grid(row=0, column=0, sticky="w")
        self.ai_nodes_label = tk.Label(load_box, text="0 seisu", bg=PANEL_BG, fg=ACCENT_DARK, font=FONT_UI)
        self.ai_nodes_label.grid(row=0, column=1, sticky="e")

        tk.Label(load_box, text="Aeg:", bg=PANEL_BG, fg=ACCENT_DARK, font=FONT_UI).grid(row=1, column=0, sticky="w")
        self.ai_time_label = tk.Label(load_box, text="0 ms", bg=PANEL_BG, fg=ACCENT_DARK, font=FONT_UI)
        self.ai_time_label.grid(row=1, column=1, sticky="e")

        self.ai_load_bar = ttk.Progressbar(
            load_box, orient="horizontal", length=200, mode="determinate",
            style="Petal.Horizontal.TProgressbar",
        )
        self.ai_load_bar.grid(row=2, column=0, columnspan=2, pady=(6, 0), sticky="ew")

        tk.Label(load_box, text="Kokku selles mängus:", bg=PANEL_BG, fg=ACCENT_DARK, font=FONT_UI).grid(
            row=3, column=0, sticky="w", pady=(6, 0)
        )
        self.ai_total_label = tk.Label(load_box, text="0 seisu", bg=PANEL_BG, fg=ACCENT_DARK, font=FONT_UI)
        self.ai_total_label.grid(row=3, column=1, sticky="e", pady=(6, 0))

        # ---- Ajalugu ----
        hist_box = ttk.LabelFrame(right, text=f"🌸 Viimased {VISIBLE_HISTORY} mängu", padding=8)
        hist_box.pack(fill="both", expand=True)

        self.history_list = tk.Listbox(
            hist_box, width=38, height=10, font=FONT_LIST,
            bg=CELL_BG, fg=ACCENT_DARK, selectbackground=ACCENT,
            selectforeground="white", relief="flat", highlightthickness=1,
            highlightbackground=ACCENT_SOFT,
        )
        self.history_list.pack(fill="both", expand=True)

        ttk.Button(hist_box, text="Näita kogu ajalugu...", command=self._open_full_history).pack(
            fill="x", pady=(6, 0)
        )

        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=1)

        # ---- Parem kaunistusriba ----
        right_petals = tk.Canvas(self, width=42, height=560, bg=BG_LIGHT, highlightthickness=0)
        right_petals.grid(row=1, column=2, sticky="ns")
        PetalField(right_petals, count=8)

        # Pealkiri joondatakse täpselt mängulaua kohale, kui mõõdud on teada.
        self.update_idletasks()
        board_center_x = (
            board_frame.winfo_rootx() - banner.winfo_rootx() + board_frame.winfo_width() / 2
        )
        banner.coords(title_item, board_center_x, banner.winfo_height() / 2)

    def _on_cell_hover(self, idx, entering):
        if self.game_over or self.board[idx] != " ":
            return
        self.buttons[idx].config(bg=ACCENT_SOFT if entering else CELL_BG)

    # ---------- Mängu loogika ----------
    def _new_game(self):
        self.board = [" "] * 9
        self.game_over = False
        self.stats.reset_game()
        for btn in self.buttons:
            btn.config(text=" ", state="normal", bg=CELL_BG, fg=ACCENT_DARK)
        self._refresh_score()
        self._refresh_ai_load()
        self._refresh_history_box()

        if self.starter == AI:
            self.status_label.config(text="Arvuti alustab... 🌸")
            self.after(300, self._ai_move)
        else:
            self.status_label.config(text="Sinu käik (X)")

    def _on_cell_click(self, idx):
        if self.game_over or self.board[idx] != " ":
            return
        self.board[idx] = PLAYER
        self.buttons[idx].config(text=PLAYER, fg=ACCENT_DARK)
        result = check_winner(self.board)
        if result:
            self._finish_game(result)
            return
        self.status_label.config(text="Arvuti mõtleb... 🌸")
        self.update_idletasks()
        self.after(150, self._ai_move)

    def _ai_move(self):
        if self.game_over:
            return
        depth_limit = self._current_depth_limit()
        nodes = [0]
        start = time.perf_counter()
        _, move = self._minimax(self.board, AI, depth_limit, nodes)
        elapsed_ms = (time.perf_counter() - start) * 1000

        self.stats.record_move(nodes[0], elapsed_ms)
        self._refresh_ai_load()

        if move is None:
            return
        self.board[move] = AI
        self.buttons[move].config(text=AI, fg=ACCENT)

        result = check_winner(self.board)
        if result:
            self._finish_game(result)
        else:
            self.status_label.config(text="Sinu käik (X)")

    def _current_depth_limit(self):
        choice = self.difficulty.get()
        if choice.startswith("Lihtne"):
            return 2
        if choice.startswith("Keskmine"):
            return 4
        return None  # piiramatu = täis minimax

    def _minimax(self, board, turn, depth_limit, nodes, depth=0):
        nodes[0] += 1
        result = check_winner(board)
        if result == AI:
            return 10 - depth, None
        if result == PLAYER:
            return depth - 10, None
        if result == "DRAW":
            return 0, None
        if depth_limit is not None and depth >= depth_limit:
            return self._heuristic(board), None

        empties = [i for i, v in enumerate(board) if v == " "]
        best_move = empties[0]

        if turn == AI:
            best_score = -999
            for i in empties:
                board[i] = AI
                score, _ = self._minimax(board, PLAYER, depth_limit, nodes, depth + 1)
                board[i] = " "
                if score > best_score:
                    best_score, best_move = score, i
            return best_score, best_move
        else:
            best_score = 999
            for i in empties:
                board[i] = PLAYER
                score, _ = self._minimax(board, AI, depth_limit, nodes, depth + 1)
                board[i] = " "
                if score < best_score:
                    best_score, best_move = score, i
            return best_score, best_move

    @staticmethod
    def _heuristic(board):
        """Lihtne hinnang piiratud sügavusega otsingu jaoks (ridade potentsiaal)."""
        score = 0
        for a, b, c in WIN_LINES:
            line = [board[a], board[b], board[c]]
            if line.count(PLAYER) == 0:
                score += line.count(AI)
            if line.count(AI) == 0:
                score -= line.count(PLAYER)
        return score

    def _finish_game(self, result):
        self.game_over = True
        for btn in self.buttons:
            btn.config(state="disabled")

        if result == PLAYER:
            self.status_label.config(text="Sa võitsid! 🎉🌸")
            outcome = "player"
        elif result == AI:
            self.status_label.config(text="Arvuti võitis. 🌸")
            outcome = "ai"
        else:
            self.status_label.config(text="Viik! 🌸")
            outcome = "draw"

        line = find_winning_line(self.board)
        if line:
            for idx in line:
                self.buttons[idx].config(bg=ACCENT, fg="white", disabledforeground="white")

        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "result": outcome,
            "ai_nodes_total": self.stats.total_nodes,
            "ai_time_ms_last": round(self.stats.last_time_ms, 2),
            "difficulty": self.difficulty.get(),
        }
        self.history.append(entry)
        self.save_history()

        # vahetame alustaja järgmiseks mänguks, et mäng oleks ausam
        self.starter = AI if self.starter == PLAYER else PLAYER

        self._refresh_score()
        self._refresh_history_box()

    # ---------- Vaadete värskendamine ----------
    def _refresh_score(self):
        wins = sum(1 for h in self.history if h["result"] == "player")
        losses = sum(1 for h in self.history if h["result"] == "ai")
        draws = sum(1 for h in self.history if h["result"] == "draw")
        total = wins + losses + draws

        self.score_label.config(
            text=f"Sa: {wins}   Arvuti: {losses}   Viigid: {draws}   (kokku {total})"
        )

        if wins > losses:
            self.lead_label.config(text="🌸 Sa oled ülekaalus!", fg=ACCENT_DARK, bg=PANEL_BG)
        elif losses > wins:
            self.lead_label.config(text="🥀 Arvuti on ülekaalus.", fg=ACCENT, bg=PANEL_BG)
        else:
            self.lead_label.config(text="🌱 Täpselt viigis.", fg=DRAW_TEXT, bg=PANEL_BG)

    def _refresh_ai_load(self):
        self.ai_nodes_label.config(text=f"{self.stats.last_nodes:,} seisu")
        self.ai_time_label.config(text=f"{self.stats.last_time_ms:.1f} ms")
        self.ai_total_label.config(text=f"{self.stats.total_nodes:,} seisu")

        pct = min(100, int(100 * self.stats.last_nodes / self.stats.max_seen_nodes))
        self.ai_load_bar["value"] = pct

    def _refresh_history_box(self):
        self.history_list.delete(0, tk.END)
        labels = {"player": "Sina", "ai": "Arvuti", "draw": "Viik"}
        for entry in reversed(self.history[-VISIBLE_HISTORY:]):
            when = entry["timestamp"][11:16]  # HH:MM
            self.history_list.insert(
                tk.END,
                f"{when}  {labels.get(entry['result'], '?'):<6} "
                f"(AI seise: {entry['ai_nodes_total']})",
            )

    def _open_full_history(self):
        win = tk.Toplevel(self)
        win.title("🌸 Kõik mängude tulemused")
        win.geometry("480x420")
        win.configure(bg=BG_LIGHT)

        wins = sum(1 for h in self.history if h["result"] == "player")
        losses = sum(1 for h in self.history if h["result"] == "ai")
        draws = sum(1 for h in self.history if h["result"] == "draw")

        summary = tk.Label(
            win,
            text=f"Kokku {len(self.history)} mängu   —   Sina: {wins}  Arvuti: {losses}  Viigid: {draws}",
            font=FONT_UI_BOLD, bg=BG_LIGHT, fg=ACCENT_DARK,
        )
        summary.pack(pady=(10, 4))

        frame = tk.Frame(win, bg=BG_LIGHT)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(frame, orient="vertical")
        listbox = tk.Listbox(
            frame, font=FONT_LIST, yscrollcommand=scrollbar.set,
            bg=CELL_BG, fg=ACCENT_DARK, selectbackground=ACCENT, selectforeground="white",
            relief="flat", highlightthickness=1, highlightbackground=ACCENT_SOFT,
        )
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)

        labels = {"player": "Sina võitsid", "ai": "Arvuti võitis", "draw": "Viik"}
        for entry in reversed(self.history):
            listbox.insert(
                tk.END,
                f"{entry['timestamp']}  |  {labels.get(entry['result'], '?'):<13} |  "
                f"AI seise: {entry['ai_nodes_total']:>6}  |  {entry.get('difficulty', '')}",
            )

        ttk.Button(win, text="Sulge", command=win.destroy).pack(pady=(0, 10))


if __name__ == "__main__":
    app = MinimaxApp()
    app.mainloop()
