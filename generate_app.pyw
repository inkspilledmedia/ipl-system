"""
IPL Head-to-Head Template Generator — Desktop App
Double-click this file to open. Select teams, click Generate.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os
import threading
from pathlib import Path

# Make sure we're running from the right directory
BASE_DIR = Path(__file__).resolve().parent
os.chdir(str(BASE_DIR))

# Find the correct Python that has Pillow installed
def _find_python():
    """Find python executable that has PIL installed."""
    import shutil
    # Try common paths for pyenv on Windows
    candidates = [
        r"C:\Users\Dell\.pyenv\pyenv-win\versions\3.10.5\python.exe",
        shutil.which("python"),
        shutil.which("python3"),
        sys.executable,
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return "python"

PYTHON_EXE = _find_python()

# IPL 2026 Teams
TEAMS = ["CSK", "MI", "RCB", "KKR", "SRH", "DC", "LSG", "RR", "GT", "PBKS"]
TEAM_FULL = {
    "CSK": "Chennai Super Kings",
    "MI": "Mumbai Indians",
    "RCB": "Royal Challengers Bengaluru",
    "KKR": "Kolkata Knight Riders",
    "SRH": "Sunrisers Hyderabad",
    "DC": "Delhi Capitals",
    "LSG": "Lucknow Super Giants",
    "RR": "Rajasthan Royals",
    "GT": "Gujarat Titans",
    "PBKS": "Punjab Kings",
}


class App:
    def __init__(self, root):
        self.root = root
        root.title("IPL Head-to-Head Generator")
        root.geometry("520x420")
        root.resizable(False, False)
        root.configure(bg="#1a1a2e")

        # Title
        title = tk.Label(root, text="IPL HEAD TO HEAD",
                         font=("Arial Black", 22, "bold"),
                         fg="#f6c428", bg="#1a1a2e")
        title.pack(pady=(25, 5))

        subtitle = tk.Label(root, text="Template Generator",
                            font=("Arial", 12), fg="#aaaaaa", bg="#1a1a2e")
        subtitle.pack(pady=(0, 20))

        # Team A
        frame_a = tk.Frame(root, bg="#1a1a2e")
        frame_a.pack(pady=5)
        tk.Label(frame_a, text="TEAM A:", font=("Arial Bold", 11),
                 fg="white", bg="#1a1a2e", width=10, anchor="e").pack(side="left", padx=5)
        self.team_a = ttk.Combobox(frame_a, values=TEAMS, state="readonly",
                                    font=("Arial", 12), width=18)
        self.team_a.pack(side="left", padx=5)
        self.team_a.set("CSK")
        self.label_a = tk.Label(frame_a, text=TEAM_FULL["CSK"],
                                font=("Arial", 9), fg="#888", bg="#1a1a2e", width=28, anchor="w")
        self.label_a.pack(side="left")
        self.team_a.bind("<<ComboboxSelected>>", self._update_labels)

        # VS label
        tk.Label(root, text="VS", font=("Arial Black", 16, "bold"),
                 fg="#e74c3c", bg="#1a1a2e").pack(pady=8)

        # Team B
        frame_b = tk.Frame(root, bg="#1a1a2e")
        frame_b.pack(pady=5)
        tk.Label(frame_b, text="TEAM B:", font=("Arial Bold", 11),
                 fg="white", bg="#1a1a2e", width=10, anchor="e").pack(side="left", padx=5)
        self.team_b = ttk.Combobox(frame_b, values=TEAMS, state="readonly",
                                    font=("Arial", 12), width=18)
        self.team_b.pack(side="left", padx=5)
        self.team_b.set("KKR")
        self.label_b = tk.Label(frame_b, text=TEAM_FULL["KKR"],
                                font=("Arial", 9), fg="#888", bg="#1a1a2e", width=28, anchor="w")
        self.label_b.pack(side="left")
        self.team_b.bind("<<ComboboxSelected>>", self._update_labels)

        # Generate button
        self.btn = tk.Button(root, text="GENERATE TEMPLATE",
                             font=("Arial Black", 13, "bold"),
                             fg="#1a1a2e", bg="#f6c428",
                             activebackground="#d4a517",
                             cursor="hand2", relief="flat",
                             padx=20, pady=8,
                             command=self._on_generate)
        self.btn.pack(pady=25)

        # Status
        self.status = tk.Label(root, text="Select teams and click Generate",
                               font=("Arial", 10), fg="#666", bg="#1a1a2e")
        self.status.pack(pady=5)

        # Progress bar (hidden until generating)
        self.progress = ttk.Progressbar(root, mode="indeterminate", length=300)

    def _update_labels(self, event=None):
        a = self.team_a.get()
        b = self.team_b.get()
        self.label_a.config(text=TEAM_FULL.get(a, ""))
        self.label_b.config(text=TEAM_FULL.get(b, ""))

    def _on_generate(self):
        a = self.team_a.get()
        b = self.team_b.get()

        if not a or not b:
            messagebox.showwarning("Select Teams", "Please select both Team A and Team B.")
            return
        if a == b:
            messagebox.showwarning("Same Team", "Team A and Team B cannot be the same.")
            return

        # Disable button, show progress
        self.btn.config(state="disabled", text="Generating...")
        self.status.config(text=f"Generating {a} vs {b}...", fg="#f6c428")
        self.progress.pack(pady=5)
        self.progress.start(15)

        # Run in background thread so UI doesn't freeze
        thread = threading.Thread(target=self._run_generate, args=(a, b), daemon=True)
        thread.start()

    def _run_generate(self, team_a, team_b):
        try:
            main_py = str(BASE_DIR / "main.py")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(BASE_DIR)

            result = subprocess.run(
                [PYTHON_EXE, main_py, team_a, team_b],
                capture_output=True, text=True,
                cwd=str(BASE_DIR),
                env=env,
                timeout=120,
            )

            output_file = BASE_DIR / "output" / f"{team_a}vs{team_b}.png"

            if result.returncode == 0 and output_file.exists():
                # Open the image automatically
                try:
                    os.startfile(str(output_file))
                except Exception:
                    pass  # startfile may not work on all systems
                self.root.after(0, self._done_success, team_a, team_b)
            else:
                error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
                self.root.after(0, self._done_error, error_msg)

        except subprocess.TimeoutExpired:
            self.root.after(0, self._done_error, "Generation timed out (>120 seconds)")
        except Exception as e:
            self.root.after(0, self._done_error, str(e))

    def _done_success(self, a, b):
        self.progress.stop()
        self.progress.pack_forget()
        self.btn.config(state="normal", text="GENERATE TEMPLATE")
        self.status.config(
            text=f"Done! {a} vs {b} saved in output folder",
            fg="#2ecc71"
        )

    def _done_error(self, error):
        self.progress.stop()
        self.progress.pack_forget()
        self.btn.config(state="normal", text="GENERATE TEMPLATE")
        self.status.config(text="Error occurred - see popup", fg="#e74c3c")
        messagebox.showerror("Generation Error",
                             f"Something went wrong:\n\n{error[:800]}")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
