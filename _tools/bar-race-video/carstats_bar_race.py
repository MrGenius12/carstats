"""
CarStats.ie bar chart race video (BY MODEL, ONE MAKE)
=====================================================
Replaces the Flourish step. One command goes from BigQuery (or a CSV) to a
finished MP4 in the CarStats.ie style.

    # straight from BigQuery (needs the same Google login as your old script)
    python carstats_bar_race.py --make NISSAN

    # from an existing Flourish-style CSV (one row per model, one column per month)
    python carstats_bar_race.py --csv flourish_data_TOYOTA.csv --make TOYOTA

    # also make a vertical 9:16 version for Reels / TikTok / Shorts
    python carstats_bar_race.py --make NISSAN --format both

Useful options
    --notes notes.json       pop-up captions, e.g. {"2019-01": "Auris renamed Corolla"}
    --no-fade                keep discontinued models blue (default: they turn grey)
    --seconds-per-year 3     speed of the race
    --top 25                 show only the top N models (default: all)
    --question "Which Toyota did your family drive?"   text under the vertical video
    --brand-logo logos/toyota.png   brand badge (PNG, transparent background) before the brand name

Rows called UNIDENTIFIED are always removed.

Requirements:
    pip install pandas numpy pillow imageio-ffmpeg
    pip install google-cloud-bigquery db-dtypes      # only for --make without --csv
Keep the "fonts" folder next to this script.
"""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent

# ---- BigQuery config (same as the old Flourish export script) ---------------
PROJECT_ID = "simi-dashboard-496509"
DATASET = "simi_data"
TABLE = "registrations"
MAKE_COL, MODEL_COL, DATE_COL, VALUE_COL = "make", "model", "date", "count"

MODEL_MERGES = {
    "IX35": "TUCSON (IX35)",
    "TUCSON": "TUCSON (IX35)",
    "PASSAT ESTATE": "PASSAT",
    "PASSAT SALOON": "PASSAT",
    "GOLF CABRIO": "GOLF",
    "GOLF EST": "GOLF",
    "GOLF SV": "GOLF",
}

EXCLUDE_MODELS = {"UNIDENTIFIED"}

# Brand names that should not be written as Title Case
BRAND_DISPLAY = {
    "BMW": "BMW", "MG": "MG", "DS": "DS", "MINI": "MINI", "SEAT": "SEAT",
    "BYD": "BYD", "KGM": "KGM", "GWM": "GWM", "CUPRA": "Cupra",
}

# ---- Style ------------------------------------------------------------------
BG = (255, 255, 255)
BAR = (59, 111, 221)
BAR_OLD = (190, 196, 205)
TEXT = (51, 51, 51)
MUTED = (120, 120, 120)
DATE = (200, 200, 200)
GRID = (226, 226, 226)
LOGO_DARK = (17, 17, 17)
LOGO_BLUE = (79, 140, 255)
LOGO_GREY = (139, 148, 158)
NOTE_BG = (59, 111, 221)

SS = 2  # supersampling factor for smooth motion


@lru_cache(maxsize=None)
def font(weight: str, size: float) -> ImageFont.FreeTypeFont:
    path = HERE / "fonts" / f"SourceSansPro-{weight}.ttf"
    try:
        return ImageFont.truetype(str(path), int(size))
    except OSError:
        return ImageFont.load_default(int(size))


# ---- Data -------------------------------------------------------------------
def load_from_bigquery(make: str) -> pd.DataFrame:
    from google.cloud import bigquery  # imported here so CSV mode needs no Google libs

    whens = "\n    ".join(f"WHEN {MODEL_COL} = '{o}' THEN '{n}'" for o, n in MODEL_MERGES.items())
    model_expr = f"CASE\n    {whens}\n    ELSE {MODEL_COL}\n  END" if MODEL_MERGES else MODEL_COL
    query = f"""
    SELECT model, FORMAT_DATE('%Y-%m', date) AS year_month,
           SUM(count) OVER (PARTITION BY model ORDER BY date
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum
    FROM (
      SELECT {model_expr} AS model, {DATE_COL} AS date, SUM({VALUE_COL}) AS count
      FROM `{PROJECT_ID}.{DATASET}.{TABLE}`
      WHERE {MAKE_COL} = @make
      GROUP BY model, date
    )
    ORDER BY model, year_month
    """
    client = bigquery.Client(project=PROJECT_ID)
    cfg = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("make", "STRING", make)]
    )
    df = client.query(query, job_config=cfg).to_dataframe()
    if df.empty:
        raise SystemExit(f"No rows for make = '{make}'. Check the spelling (e.g. 'VOLKSWAGEN').")
    wide = df.pivot(index="model", columns="year_month", values="cum").sort_index(axis=1)
    return wide.ffill(axis=1).fillna(0)


def load_from_csv(path: Path) -> pd.DataFrame:
    wide = pd.read_csv(path)
    wide = wide.set_index(wide.columns[0])
    wide = wide[sorted(wide.columns)]
    return wide.ffill(axis=1).fillna(0)


def clean(wide: pd.DataFrame) -> pd.DataFrame:
    wide.index = wide.index.astype(str).str.strip()
    drop = [m for m in wide.index if m.upper() in EXCLUDE_MODELS]
    if drop:
        print(f"Removed rows: {', '.join(drop)}")
    wide = wide.drop(index=drop)
    wide = wide[wide.iloc[:, -1] > 0]
    return wide.astype(float)


# ---- Helpers ----------------------------------------------------------------
def ease(x: float) -> float:
    return x * x * (3 - 2 * x)


def nice_step(maxv: float) -> float:
    if maxv <= 0:
        return 1
    raw = maxv / 2.6
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def fmt(v: float) -> str:
    return f"{int(round(v)):,}"


def brand_name(make: str) -> str:
    up = make.upper()
    return BRAND_DISPLAY.get(up, make.title())


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def period_text(months: list[str]) -> str:
    y0, (y1, m1) = months[0][:4], months[-1].split("-")
    return f"{y0} - {y1} ({MONTHS[int(m1) - 1]})"


# ---- Precomputed state per month --------------------------------------------
class Race:
    def __init__(self, wide: pd.DataFrame, fade: bool, top: int | None):
        self.models = list(wide.index)
        self.months = list(wide.columns)
        self.v = wide.to_numpy()  # models x months
        n_mod, n_mon = self.v.shape
        # rank per month: higher value first, ties alphabetical
        self.rank = np.zeros_like(self.v)
        for j in range(n_mon):
            order = sorted(range(n_mod), key=lambda i: (-self.v[i, j], self.models[i]))
            for r, i in enumerate(order):
                self.rank[i, j] = r
        # greyness: models with < 10 registrations over the last 12 months fade to grey
        self.grey = np.zeros_like(self.v)
        if fade:
            for i in range(n_mod):
                streak = 0
                for j in range(n_mon):
                    gain = self.v[i, j] - self.v[i, max(0, j - 12)]
                    inactive = j >= 12 and self.v[i, j] > 0 and gain < 10
                    streak = streak + 1 if inactive else 0
                    self.grey[i, j] = min(1.0, streak / 4)
        self.top = min(top or n_mod, n_mod)


# ---- Drawing ----------------------------------------------------------------
@lru_cache(maxsize=None)
def load_image(path: str, height: int) -> Image.Image | None:
    p = Path(path)
    if not p.is_absolute():
        p = HERE / p if (HERE / p).exists() else p
    if not p.exists():
        return None
    im = Image.open(p).convert("RGBA")
    im = im.crop(im.getbbox() or (0, 0, *im.size))
    w = max(1, round(im.width * height / im.height))
    return im.resize((w, height), Image.LANCZOS)


def paste(img: Image.Image, im: Image.Image, x: float, y: float) -> None:
    """Paste RGBA image with its top-left corner at (x, y)."""
    img.paste(im, (round(x), round(y)), im)


def draw_logo(img, d, x: float, y: float, size: float, anchor_right=False):
    """CarStats.ie logo (same artwork as the website). y is the vertical centre."""
    logo = load_image("carstats_logo.png", round(size * 0.66))
    if logo is not None:
        lx = x - logo.width if anchor_right else x - logo.width / 2
        paste(img, logo, lx, y - logo.height / 2)
        return
    f = font("Bold", size)
    parts = [("Car", LOGO_DARK), ("Stats", LOGO_BLUE), (".ie", LOGO_GREY)]
    total = sum(d.textlength(t, font=f) for t, _ in parts)
    cx = x - total if anchor_right else x - total / 2
    for t, c in parts:
        d.text((cx, y), t, font=f, fill=c, anchor="lm")
        cx += d.textlength(t, font=f)


def draw_chart(img, d, race: Race, t: float, box, s, show_logo=True, show_date=True):
    """box = (x0, y0, x1, y1) in final pixels; s = supersample factor."""
    x0, y0, x1, y1 = [c * s for c in box]
    j = int(math.floor(t))
    f = t - j
    j2 = min(j + 1, len(race.months) - 1)
    vals = race.v[:, j] * (1 - f) + race.v[:, j2] * f
    pos = race.rank[:, j] + (race.rank[:, j2] - race.rank[:, j]) * ease(f)
    grey = race.grey[:, j] * (1 - f) + race.grey[:, j2] * f

    n = race.top
    axis_h = 46 * s
    top = y0 + axis_h
    row = (y1 - top) / n
    bar_h = row * 0.78
    lab_size = max(11, min(26, row / s * 0.62)) * s
    f_lab = font("Regular", lab_size)
    f_val = font("Regular", lab_size)

    label_w = max(d.textlength(m, font=f_lab) for m in race.models) + 14 * s
    bx = x0 + label_w
    val_room = d.textlength("000,000", font=f_val) + 16 * s
    bw_max = x1 - bx - val_room

    shown_max = max(np.max(np.where(pos < n, vals, 0)), 1)
    step = nice_step(shown_max)
    f_axis = font("Regular", 26 * s)
    k = 0
    while k * step <= shown_max * 1.02:
        gx = bx + bw_max * (k * step) / shown_max
        d.line([(gx, top - 6 * s), (gx, y1)], fill=GRID, width=max(1, s))
        d.text((gx, top - 12 * s), fmt(k * step), font=f_axis, fill=MUTED, anchor="ms")
        k += 1
    d.line([(bx, top - 6 * s), (bx, y1)], fill=(200, 200, 200), width=max(1, s))

    if show_date:
        f_date = font("Bold", 150 * s)
        f_tot = font("Regular", 46 * s)
        label = race.months[j2 if f > 0.5 else j]
        d.text((x1, y1 - 60 * s), label, font=f_date, fill=DATE, anchor="rs")
        d.text((x1, y1 - 8 * s), f"Total: {fmt(vals.sum())}", font=f_tot, fill=DATE, anchor="rs")
    if show_logo:
        draw_logo(img, d, x1 - 40 * s, y0 + (y1 - y0) * 0.56, 64 * s, anchor_right=True)

    for i in np.argsort(-pos):  # draw lower rows first
        p = pos[i]
        if p > n - 0.5:
            continue
        cy = top + (p + 0.5) * row
        w = bw_max * vals[i] / shown_max
        g = grey[i]
        col = tuple(int(BAR[c] * (1 - g) + BAR_OLD[c] * g) for c in range(3))
        if w > 0.5:
            d.rectangle([bx, cy - bar_h / 2, bx + w, cy + bar_h / 2], fill=col)
        d.text((bx - 10 * s, cy), race.models[i], font=f_lab, fill=TEXT, anchor="rm")
        d.text((bx + w + 8 * s, cy), fmt(vals[i]), font=f_val, fill=TEXT, anchor="lm")


def draw_note(d, notes, race: Race, t: float, xr, y, s, months_visible=10):
    """Pop-up caption at month index from notes {"YYYY-MM": "text"}."""
    for ym, text in notes.items():
        if ym not in race.months:
            continue
        start = race.months.index(ym)
        age = t - start
        if 0 <= age <= months_visible:
            alpha = min(1, age / 1.5, (months_visible - age) / 1.5)
            if alpha <= 0:
                continue
            f = font("Semibold", 34 * s)
            tw = d.textlength(text, font=f)
            pad = 18 * s
            x0 = xr - tw - 2 * pad
            col = tuple(int(255 * (1 - alpha) + NOTE_BG[c] * alpha) for c in range(3))
            d.rounded_rectangle([x0, y - 32 * s, xr, y + 32 * s], radius=14 * s, fill=col)
            d.text((xr - pad, y), text, font=f, fill=(255, 255, 255), anchor="rm")


def render_frame(race, t, fmt_name, title_parts, notes, question, brand_logo=None):
    s = SS
    if fmt_name == "square":
        W, H = 1080, 1080
    else:
        W, H = 1080, 1920
    img = Image.new("RGB", (W * s, H * s), BG)
    d = ImageDraw.Draw(img)

    brand, rest, period = title_parts
    if fmt_name == "square":
        draw_chart(img, d, race, t, (24, 8, W - 24, H - 74), s)
        # bottom title: [logo] **Brand** Irish Car New Registrations **2010 - 2026 (Sep)**
        fb, fr = font("Bold", 38 * s), font("Regular", 38 * s)
        pieces = [(brand + " ", fb), (rest + " ", fr), (period, fb)]
        icon = load_image(brand_logo, 44 * s) if brand_logo else None
        gap = 10 * s
        tw = sum(d.textlength(p, font=f) for p, f in pieces) + (icon.width + gap if icon else 0)
        cx = (W * s - tw) / 2
        base = (H - 30) * s
        if icon:
            paste(img, icon, cx, base - 13 * s - icon.height / 2)
            cx += icon.width + gap
        for p, f in pieces:
            d.text((cx, base), p, font=f, fill=LOGO_DARK, anchor="ls")
            cx += d.textlength(p, font=f)
        if notes:
            draw_note(d, notes, race, t, (W - 64) * s, H * 0.42 * s, s)
    else:
        fb = font("Bold", 96 * s)
        icon = load_image(brand_logo, 100 * s) if brand_logo else None
        gap = 24 * s
        tw = d.textlength(brand, font=fb) + (icon.width + gap if icon else 0)
        cx = (W * s - tw) / 2
        if icon:
            paste(img, icon, cx, 118 * s - icon.height / 2)
            cx += icon.width + gap
        d.text((cx, 118 * s), brand, font=fb, fill=LOGO_DARK, anchor="lm")
        d.text((W / 2 * s, 222 * s), f"{rest} {period}", font=font("Regular", 44 * s),
               fill=TEXT, anchor="ms")
        draw_chart(img, d, race, t, (24, 290, W - 24, 1600), s, show_logo=False)
        if notes:
            draw_note(d, notes, race, t, (W - 64) * s, 1100 * s, s)
        if question:
            d.text((W / 2 * s, 1700 * s), question, font=font("Semibold", 46 * s),
                   fill=TEXT, anchor="ms")
        draw_logo(img, d, W / 2 * s, 1810 * s, 64 * s)

    if s != 1:
        img = img.resize((W, H), Image.LANCZOS)
    return img


# ---- Video ------------------------------------------------------------------
def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


_JOB = {}


def _init_worker(job):
    _JOB.update(job)


def _render_t(t):
    j = _JOB
    return render_frame(j["race"], t, j["fmt"], j["title"], j["notes"], j["question"], j["brand_logo"]).tobytes()


def write_video(race, out: Path, fmt_name, title_parts, notes, question, fps, spy, hold, workers,
                brand_logo=None):
    W, H = (1080, 1080) if fmt_name == "square" else (1080, 1920)
    frames_per_month = fps * spy / 12
    n_frames = int((len(race.months) - 1) * frames_per_month) + 1
    times = [min(k / frames_per_month, len(race.months) - 1) for k in range(n_frames)]
    cmd = [ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium",
           "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    job = {"race": race, "fmt": fmt_name, "title": title_parts, "notes": notes, "question": question,
           "brand_logo": brand_logo}
    last = None
    # Frames are drawn in parallel on all CPU cores but written to the video in order.
    with mp.Pool(workers, initializer=_init_worker, initargs=(job,)) as pool:
        for k, frame in enumerate(pool.imap(_render_t, times, chunksize=4)):
            proc.stdin.write(frame)
            last = frame
            if k % 50 == 0:
                print(f"  {fmt_name}: frame {k}/{n_frames}", end="\r", flush=True)
    for _ in range(int(hold * fps)):
        proc.stdin.write(last)
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("ffmpeg failed")
    print(f"  {fmt_name}: done -> {out}            ")


def main() -> None:
    ap = argparse.ArgumentParser(description="CarStats.ie bar chart race video")
    ap.add_argument("--make", required=True, help="make as stored in BigQuery, e.g. TOYOTA")
    ap.add_argument("--csv", type=Path, help="use this Flourish-style CSV instead of BigQuery")
    ap.add_argument("--brand", help="brand name for the title (default: from --make)")
    ap.add_argument("--format", choices=["square", "vertical", "both"], default="square")
    ap.add_argument("--notes", type=Path, help='JSON file {"YYYY-MM": "caption"}')
    ap.add_argument("--question", help="text under the chart in the vertical video")
    ap.add_argument("--brand-logo", help="PNG with the brand badge, shown before the brand name")
    ap.add_argument("--no-fade", action="store_true", help="do not grey out discontinued models")
    ap.add_argument("--top", type=int, help="show only the top N models")
    ap.add_argument("--seconds-per-year", type=float, default=3.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--hold", type=float, default=3.0, help="seconds to hold the last frame")
    ap.add_argument("--out-dir", type=Path, default=HERE)
    ap.add_argument("--preview", help="only save a PNG of this month (YYYY-MM) and exit")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1),
                    help="CPU cores to use (default: all but one)")
    a = ap.parse_args()

    wide = load_from_csv(a.csv) if a.csv else load_from_bigquery(a.make.upper())
    wide = clean(wide)
    race = Race(wide, fade=not a.no_fade, top=a.top)
    notes = json.loads(a.notes.read_text(encoding="utf-8")) if a.notes else {}
    title = (a.brand or brand_name(a.make), "Irish Car New Registrations", period_text(race.months))
    print(f"{title[0]}: {len(race.models)} models x {len(race.months)} months, "
          f"final total {fmt(race.v[:, -1].sum())}")

    a.out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{title[0].replace(' ', '_')}_{race.months[0][:4]}-{race.months[-1]}_Ireland"
    formats = ["square", "vertical"] if a.format == "both" else [a.format]

    if a.preview:
        t = race.months.index(a.preview)
        for fm in formats:
            p = a.out_dir / f"{stem}_{fm}_{a.preview}.png"
            render_frame(race, t, fm, title, notes, a.question, a.brand_logo).save(p)
            print(f"  preview -> {p}")
        return

    for fm in formats:
        suffix = "" if fm == "square" else "_vertical"
        write_video(race, a.out_dir / f"{stem}{suffix}.mp4", fm, title, notes, a.question,
                    a.fps, a.seconds_per_year, a.hold, a.workers, a.brand_logo)


if __name__ == "__main__":
    sys.exit(main())
