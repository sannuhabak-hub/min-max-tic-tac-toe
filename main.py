"""Min-Max (XOX) mäng AI vastu, koos skoori, ajaloo ja AI arvutuskoormuse näitajaga.

Käivitamine: py main.py  (või topeltklõps Kaivita_mang.bat failil)
"""

import json
import os
import time
import tkinter as tk
from tkinter import ttk
from datetime import datetime

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ajalugu.json")
MAX_HISTORY = 200          # kui palju tulemusi failis säilitada
VISIBLE_HISTORY = 10        # kui palju viimast mängu näidatakse akna peal

PLAYER = "X"
AI = "O"

WIN_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
]


def check_winner(board):
    for a, b, c in WIN_LINES:
        if board[a] != " " and board[a] == board[b] == board[c]:
            return board[a]
    if " " not in board:
        return "DRAW"
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


class MinimaxApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Min-Max XOX mäng")
        self.resizable(False, False)

        self.board = [" "] * 9
        self.buttons = []
        self.game_over = False
        self.starter = PLAYER  # kes alustab järgmist mängu (vahetub iga mängu järel)
        self.stats = AIStats()
        self.difficulty = tk.StringVar(value="Raske (täis minimax)")
        self.history = self.load_history()

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

    # ---------- UI ----------
    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.grid(row=0, column=0, sticky="nsew")

        # ---- Vasak: mängulaud ----
        board_frame = ttk.Frame(root)
        board_frame.grid(row=0, column=0, rowspan=3, padx=(0, 16))

        for i in range(9):
            btn = tk.Button(
                board_frame, text=" ", font=("Segoe UI", 28, "bold"),
                width=4, height=2,
                command=lambda i=i: self._on_cell_click(i),
            )
            btn.grid(row=i // 3, column=i % 3, padx=3, pady=3)
            self.buttons.append(btn)

        self.status_label = ttk.Label(board_frame, text="", font=("Segoe UI", 11, "bold"))
        self.status_label.grid(row=3, column=0, columnspan=3, pady=(10, 0))

        controls = ttk.Frame(board_frame)
        controls.grid(row=4, column=0, columnspan=3, pady=(8, 0), sticky="ew")
        ttk.Label(controls, text="Raskusaste:").pack(side="left")
        diff_box = ttk.Combobox(
            controls, textvariable=self.difficulty, state="readonly", width=20,
            values=["Lihtne (2 käiku ette)", "Keskmine (4 käiku ette)", "Raske (täis minimax)"],
        )
        diff_box.pack(side="left", padx=6)
        diff_box.current(2)

        ttk.Button(board_frame, text="Uus mäng", command=self._new_game).grid(
            row=5, column=0, columnspan=3, pady=(10, 0), sticky="ew"
        )

        # ---- Parem: skoor + juhtseis ----
        right = ttk.Frame(root)
        right.grid(row=0, column=1, sticky="nsew")

        score_box = ttk.LabelFrame(right, text="Skoor", padding=8)
        score_box.pack(fill="x", pady=(0, 8))
        self.score_label = ttk.Label(score_box, text="", font=("Segoe UI", 11))
        self.score_label.pack(anchor="w")
        self.lead_label = ttk.Label(score_box, text="", font=("Segoe UI", 12, "bold"))
        self.lead_label.pack(anchor="w", pady=(4, 0))

        # ---- AI arvutuskoormus ("mahtu") ----
        load_box = ttk.LabelFrame(right, text="AI arvutuskoormus", padding=8)
        load_box.pack(fill="x", pady=(0, 8))

        ttk.Label(load_box, text="Viimane käik:").grid(row=0, column=0, sticky="w")
        self.ai_nodes_label = ttk.Label(load_box, text="0 seisu")
        self.ai_nodes_label.grid(row=0, column=1, sticky="e")

        ttk.Label(load_box, text="Aeg:").grid(row=1, column=0, sticky="w")
        self.ai_time_label = ttk.Label(load_box, text="0 ms")
        self.ai_time_label.grid(row=1, column=1, sticky="e")

        self.ai_load_bar = ttk.Progressbar(load_box, orient="horizontal", length=200, mode="determinate")
        self.ai_load_bar.grid(row=2, column=0, columnspan=2, pady=(6, 0), sticky="ew")

        ttk.Label(load_box, text="Kokku selles mängus:").grid(row=3, column=0, sticky="w", pady=(6, 0))
        self.ai_total_label = ttk.Label(load_box, text="0 seisu")
        self.ai_total_label.grid(row=3, column=1, sticky="e", pady=(6, 0))

        # ---- Ajalugu ----
        hist_box = ttk.LabelFrame(right, text=f"Viimased {VISIBLE_HISTORY} mängu", padding=8)
        hist_box.pack(fill="both", expand=True)

        self.history_list = tk.Listbox(hist_box, width=38, height=10, font=("Consolas", 9))
        self.history_list.pack(fill="both", expand=True)

        ttk.Button(hist_box, text="Näita kogu ajalugu...", command=self._open_full_history).pack(
            fill="x", pady=(6, 0)
        )

        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=1)

    # ---------- Mängu loogika ----------
    def _new_game(self):
        self.board = [" "] * 9
        self.game_over = False
        self.stats.reset_game()
        for btn in self.buttons:
            btn.config(text=" ", state="normal", bg="SystemButtonFace")
        self._refresh_score()
        self._refresh_ai_load()
        self._refresh_history_box()

        if self.starter == AI:
            self.status_label.config(text="Arvuti alustab...")
            self.after(300, self._ai_move)
        else:
            self.status_label.config(text="Sinu käik (X)")

    def _on_cell_click(self, idx):
        if self.game_over or self.board[idx] != " ":
            return
        self.board[idx] = PLAYER
        self.buttons[idx].config(text=PLAYER)
        result = check_winner(self.board)
        if result:
            self._finish_game(result)
            return
        self.status_label.config(text="Arvuti mõtleb...")
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
        self.buttons[move].config(text=AI)

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
            self.status_label.config(text="Sa võitsid! 🎉")
            outcome = "player"
        elif result == AI:
            self.status_label.config(text="Arvuti võitis.")
            outcome = "ai"
        else:
            self.status_label.config(text="Viik!")
            outcome = "draw"

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
            self.lead_label.config(text="🟢 Sa oled ülekaalus!", foreground="#1a7a1a")
        elif losses > wins:
            self.lead_label.config(text="🔴 Arvuti on ülekaalus.", foreground="#b00020")
        else:
            self.lead_label.config(text="⚪ Täpselt viigis.", foreground="#555555")

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
        win.title("Kõik mängude tulemused")
        win.geometry("480x420")

        wins = sum(1 for h in self.history if h["result"] == "player")
        losses = sum(1 for h in self.history if h["result"] == "ai")
        draws = sum(1 for h in self.history if h["result"] == "draw")

        summary = ttk.Label(
            win,
            text=f"Kokku {len(self.history)} mängu   —   Sina: {wins}  Arvuti: {losses}  Viigid: {draws}",
            font=("Segoe UI", 10, "bold"),
        )
        summary.pack(pady=(10, 4))

        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(frame, orient="vertical")
        listbox = tk.Listbox(frame, font=("Consolas", 9), yscrollcommand=scrollbar.set)
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
