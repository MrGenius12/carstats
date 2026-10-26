"""
CarStats.ie video maker: a small window for carstats_bar_race.py.

Double-click "CarStats Video.bat" (or this file), pick a make, press the button.
Both formats (square + vertical) are created in the "videos" folder.
"""

import json
import os
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "carstats_bar_race.py"
OUT_DIR = HERE / "videos"
CACHE = HERE / "makes_cache.json"
TEST_CSV_DIR = os.environ.get("CARSTATS_CSV_DIR")  # for offline testing only

sys.path.insert(0, str(HERE))
import carstats_bar_race as cbr  # noqa: E402


def python_exe() -> str:
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe" and (exe.parent / "python.exe").exists():
        return str(exe.parent / "python.exe")
    return str(exe)


def fetch_makes() -> list[str]:
    """All makes, biggest first. From BigQuery, cached for next start."""
    if TEST_CSV_DIR:
        return sorted(p.stem.replace("flourish_data_", "")
                      for p in Path(TEST_CSV_DIR).glob("flourish_data_*.csv"))
    from google.cloud import bigquery
    q = (f"SELECT {cbr.MAKE_COL} AS make, SUM({cbr.VALUE_COL}) AS n "
         f"FROM `{cbr.PROJECT_ID}.{cbr.DATASET}.{cbr.TABLE}` "
         f"GROUP BY make HAVING n >= 100 ORDER BY n DESC")
    rows = bigquery.Client(project=cbr.PROJECT_ID).query(q).result()
    makes = [r["make"] for r in rows if r["make"]]
    CACHE.write_text(json.dumps(makes), encoding="utf-8")
    return makes


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.events: queue.Queue = queue.Queue()
        self.proc = None
        root.title("CarStats.ie video maker")
        root.resizable(False, False)
        frm = ttk.Frame(root, padding=18)
        frm.grid()

        ttk.Label(frm, text="Make", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.make = tk.StringVar()
        self.combo = ttk.Combobox(frm, textvariable=self.make, width=34)
        self.combo.grid(row=1, column=0, columnspan=2, sticky="we", pady=(2, 10))
        self.combo.bind("<<ComboboxSelected>>", self.on_make)
        self.combo.bind("<KeyRelease>", self.on_make)

        ttk.Label(frm, text="Question under the vertical video",
                  font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w")
        self.question = tk.StringVar()
        ttk.Entry(frm, textvariable=self.question, width=36).grid(
            row=3, column=0, columnspan=2, sticky="we", pady=(2, 14))

        self.btn = ttk.Button(frm, text="Create videos", command=self.start)
        self.btn.grid(row=4, column=0, sticky="w")
        self.open_btn = ttk.Button(frm, text="Open folder", command=self.open_folder)
        self.open_btn.grid(row=4, column=1, sticky="e")

        self.bar = ttk.Progressbar(frm, length=320, maximum=100)
        self.bar.grid(row=5, column=0, columnspan=2, pady=(14, 4), sticky="we")
        self.status = tk.StringVar(value="Loading makes...")
        ttk.Label(frm, textvariable=self.status, wraplength=320).grid(
            row=6, column=0, columnspan=2, sticky="w")

        if CACHE.exists() and not TEST_CSV_DIR:
            self.set_makes(json.loads(CACHE.read_text(encoding="utf-8")), "Ready")
        threading.Thread(target=self.load_makes, daemon=True).start()
        root.after(100, self.poll)

    # ---- makes list --------------------------------------------------------
    def load_makes(self):
        try:
            self.events.put(("makes", fetch_makes()))
        except Exception as e:  # keep cached list, allow typing a make
            self.events.put(("status", f"Could not load makes from BigQuery ({e.__class__.__name__}). "
                                       "You can still type a make."))

    def set_makes(self, makes, msg):
        self.combo["values"] = makes
        if not self.make.get() and makes:
            self.make.set(makes[0])
            self.on_make()
        self.status.set(msg)

    def on_make(self, *_):
        brand = cbr.brand_name(self.make.get().strip()) if self.make.get().strip() else ""
        self.question.set(f"Which {brand} did your family drive?" if brand else "")

    # ---- run ---------------------------------------------------------------
    def start(self):
        make = self.make.get().strip().upper()
        if not make:
            messagebox.showwarning("CarStats.ie", "Choose a make first.")
            return
        cmd = [python_exe(), "-u", str(SCRIPT), "--make", make, "--format", "both",
               "--out-dir", str(OUT_DIR)]
        if self.question.get().strip():
            cmd += ["--question", self.question.get().strip()]
        if TEST_CSV_DIR:
            cmd += ["--csv", str(Path(TEST_CSV_DIR) / f"flourish_data_{make}.csv")]
        self.btn.state(["disabled"])
        self.bar["value"] = 0
        self.status.set(f"Loading {make} data...")
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     cwd=str(HERE), creationflags=flags)
        threading.Thread(target=self.read_output, daemon=True).start()

    def read_output(self):
        buf, log = b"", []
        while True:
            ch = self.proc.stdout.read(1)
            if not ch:
                break
            if ch in b"\r\n":
                line = buf.decode("utf-8", "replace").strip()
                buf = b""
                if line:
                    log.append(line)
                    self.events.put(("line", line))
            else:
                buf += ch
        code = self.proc.wait()
        self.events.put(("done", (code, log[-8:])))

    def poll(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "makes":
                    self.set_makes(data, "Ready")
                elif kind == "status":
                    self.status.set(data)
                elif kind == "line":
                    self.on_line(data)
                elif kind == "done":
                    self.on_done(*data)
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def on_line(self, line):
        m = re.search(r"(square|vertical): frame (\d+)/(\d+)", line)
        if m:
            part = 0 if m.group(1) == "square" else 1
            pct = (part + int(m.group(2)) / int(m.group(3))) / 2 * 100
            self.bar["value"] = pct
            name = "Square video" if part == 0 else "Vertical video"
            self.status.set(f"{name}: {int(m.group(2)) * 100 // int(m.group(3))}%")
        elif "models x" in line:
            self.status.set(line)

    def on_done(self, code, tail):
        self.btn.state(["!disabled"])
        if code == 0:
            self.bar["value"] = 100
            self.status.set(f"Done. Videos are in: {OUT_DIR}")
            self.open_folder()
        else:
            self.status.set("Something went wrong.")
            messagebox.showerror("CarStats.ie", "The video was not created.\n\n" + "\n".join(tail))

    def open_folder(self):
        OUT_DIR.mkdir(exist_ok=True)
        if os.name == "nt":
            os.startfile(OUT_DIR)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(OUT_DIR)])


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
