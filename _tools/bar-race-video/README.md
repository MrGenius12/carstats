# Bar chart race video maker

Builds the CarStats.ie "<Brand> Irish Car New Registrations" bar chart race
videos straight from BigQuery. Replaces the old Flourish workflow.

## Use

1. Double-click `CarStats Video.bat`.
2. Pick a make (the list comes from BigQuery, biggest first).
3. Check the question for the vertical video, press **Create videos**.
4. The `videos` folder opens with two files:
   - `<Brand>_2010-YYYY-MM_Ireland.mp4` (square, 1080x1080)
   - `<Brand>_2010-YYYY-MM_Ireland_vertical.mp4` (9:16 for Reels, TikTok, Shorts)

## First-time setup

```
pip install -r requirements.txt
```
BigQuery uses the same Google login as the other CarStats scripts.

## Command line (optional)

```
python carstats_bar_race.py --make NISSAN --format both
python carstats_bar_race.py --make TOYOTA --csv flourish_data_TOYOTA.csv   # from a CSV
python carstats_bar_race.py --make TOYOTA --preview 2019-03                # one PNG frame
```
Other options: `--notes notes.json` (pop-up captions by month), `--no-fade`,
`--top N`, `--seconds-per-year`, `--workers`, `--brand-logo`.

## What it does

- Removes the `UNIDENTIFIED` model row.
- Merges renamed models listed in `MODEL_MERGES`.
- Models with fewer than 10 registrations in the last 12 months fade to grey.
- The title always shows the last month in the data, e.g. `2010 - 2026 (Sep)`.
- Frames are drawn in parallel on all CPU cores but one.

Fonts: Source Sans Pro (SIL Open Font License). Logo: same artwork as the site header.
