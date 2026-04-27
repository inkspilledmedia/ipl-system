"""
Add New Match Results — Run this to update matches.csv

HOW TO USE:
-----------
Double-click this file. A window opens.
1. Select the two teams that played
2. Select who won
3. Type the venue name
4. Click "Add Match"

The match gets added to data/matches.csv immediately.
Run this after every IPL match to keep your data up to date.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import csv
from datetime import date

BASE_DIR = Path(__file__).resolve().parent

TEAMS = ["CSK", "MI", "RCB", "KKR", "SRH", "DC", "LSG", "RR", "GT", "PBKS"]
TEAM_FULL = {
    "CSK": "Chennai Super Kings", "MI": "Mumbai Indians",
    "RCB": "Royal Challengers Bengaluru", "KKR": "Kolkata Knight Riders",
    "SRH": "Sunrisers Hyderabad", "DC": "Delhi Capitals",
    "LSG": "Lucknow Super Giants", "RR": "Rajasthan Royals",
    "GT": "Gujarat Titans", "PBKS": "Punjab Kings",
}
VENUES = {
    "CSK": "Chepauk", "MI": "Wankhede", "RCB": "Chinnaswamy",
    "KKR": "Eden Gardens", "SRH": "Rajiv Gandhi Stadium",
    "DC": "Arun Jaitley Stadium", "LSG": "Ekana Stadium",
    "RR": "Sawai Mansingh", "GT": "Narendra Modi Stadium",
    "PBKS": "PCA Mullanpur",
}


class AddMatchApp:
    def __init__(self, root):
        self.root = root
        root.title("Add IPL Match Result")
        root.geometry("450x420")
        root.resizable(False, False)
        root.configure(bg="#1a1a2e")

        tk.Label(root, text="ADD MATCH RESULT", font=("Arial Black", 18, "bold"),
                 fg="#f6c428", bg="#1a1a2e").pack(pady=(20, 15))

        # Team 1
        f1 = tk.Frame(root, bg="#1a1a2e")
        f1.pack(pady=5)
        tk.Label(f1, text="Team 1:", font=("Arial Bold", 11),
                 fg="white", bg="#1a1a2e", width=10, anchor="e").pack(side="left")
        self.team1 = ttk.Combobox(f1, values=TEAMS, state="readonly",
                                   font=("Arial", 12), width=15)
        self.team1.pack(side="left", padx=5)
        self.team1.set("CSK")

        # Team 2
        f2 = tk.Frame(root, bg="#1a1a2e")
        f2.pack(pady=5)
        tk.Label(f2, text="Team 2:", font=("Arial Bold", 11),
                 fg="white", bg="#1a1a2e", width=10, anchor="e").pack(side="left")
        self.team2 = ttk.Combobox(f2, values=TEAMS, state="readonly",
                                   font=("Arial", 12), width=15)
        self.team2.pack(side="left", padx=5)
        self.team2.set("KKR")

        # Winner
        fw = tk.Frame(root, bg="#1a1a2e")
        fw.pack(pady=5)
        tk.Label(fw, text="Winner:", font=("Arial Bold", 11),
                 fg="white", bg="#1a1a2e", width=10, anchor="e").pack(side="left")
        self.winner = ttk.Combobox(fw, values=TEAMS, state="readonly",
                                    font=("Arial", 12), width=15)
        self.winner.pack(side="left", padx=5)
        self.winner.set("CSK")

        # Venue
        fv = tk.Frame(root, bg="#1a1a2e")
        fv.pack(pady=5)
        tk.Label(fv, text="Venue:", font=("Arial Bold", 11),
                 fg="white", bg="#1a1a2e", width=10, anchor="e").pack(side="left")
        self.venue = tk.Entry(fv, font=("Arial", 12), width=17)
        self.venue.pack(side="left", padx=5)
        self.venue.insert(0, "Chepauk")

        # Date
        fd = tk.Frame(root, bg="#1a1a2e")
        fd.pack(pady=5)
        tk.Label(fd, text="Date:", font=("Arial Bold", 11),
                 fg="white", bg="#1a1a2e", width=10, anchor="e").pack(side="left")
        self.date_entry = tk.Entry(fd, font=("Arial", 12), width=17)
        self.date_entry.pack(side="left", padx=5)
        self.date_entry.insert(0, date.today().strftime("%Y-%m-%d"))

        # Auto-fill venue when teams change
        self.team1.bind("<<ComboboxSelected>>", self._auto_venue)
        self.team2.bind("<<ComboboxSelected>>", self._auto_venue)

        # Add button
        tk.Button(root, text="ADD MATCH", font=("Arial Black", 13, "bold"),
                  fg="#1a1a2e", bg="#2ecc71", activebackground="#27ae60",
                  cursor="hand2", relief="flat", padx=20, pady=8,
                  command=self._add_match).pack(pady=20)

        # Status
        self.status = tk.Label(root, text="", font=("Arial", 10),
                               fg="#666", bg="#1a1a2e")
        self.status.pack()

        # Count existing matches
        self._show_count()

    def _auto_venue(self, event=None):
        t1 = self.team1.get()
        self.venue.delete(0, tk.END)
        self.venue.insert(0, VENUES.get(t1, ""))

    def _show_count(self):
        csv_path = BASE_DIR / "data" / "matches.csv"
        if csv_path.exists():
            with open(csv_path, "r") as f:
                count = sum(1 for _ in f) - 1  # minus header
            self.status.config(text=f"Currently {count} matches in database",
                               fg="#888")

    def _add_match(self):
        t1 = self.team1.get()
        t2 = self.team2.get()
        w = self.winner.get()
        v = self.venue.get().strip()
        d = self.date_entry.get().strip()

        if not t1 or not t2 or not w or not v or not d:
            messagebox.showwarning("Missing Info", "Please fill all fields.")
            return
        if t1 == t2:
            messagebox.showwarning("Same Team", "Team 1 and Team 2 cannot be the same.")
            return
        if w not in (t1, t2):
            messagebox.showwarning("Wrong Winner", f"Winner must be {t1} or {t2}.")
            return

        csv_path = BASE_DIR / "data" / "matches.csv"

        # Get next match_id by counting existing rows
        next_id = 1
        if csv_path.exists():
            with open(csv_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                next_id = len(lines)  # header is line 0, so len = next id

        # Append the new match
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([next_id, "2026", t1, t2, w, v, d])

        self.status.config(
            text=f"Added: {t1} vs {t2} → {w} won at {v}",
            fg="#2ecc71"
        )
        self._show_count()


if __name__ == "__main__":
    root = tk.Tk()
    app = AddMatchApp(root)
    root.mainloop()
