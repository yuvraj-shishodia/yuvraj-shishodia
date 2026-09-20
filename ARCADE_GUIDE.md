# 🕹 Arcade Profile Guide

Pick **any of the 6 games** for the **header** and for the **body**, in any combination, by editing **one file**: `arcade.config`.

---

## 1. How it works

```
 arcade.config  ──►  GitHub Action  ──►  output branch  ──►  README shows the images
 (you edit this)     (runs by itself)    header.svg
                                         body-1.svg / body-1-dark.svg
                                         body-2.svg / body-2-dark.svg
```

- **Header:** an animated SVG built from the `header` game, plus your name and text.
- **Body:** the chosen game(s) playing on your real contribution graph.
- Your `README.md` always points to the same image names (`header.svg`, `body-1.svg`, `body-2.svg`), so **you never edit the README to change games**. The Action swaps what those images contain.

Files in your repo:

```
yuvraj-shishodia/
├── README.md                      ← your profile (static, edit freely)
├── arcade.config                  ← ⭐ the file you edit
├── ARCADE_GUIDE.md                ← this guide
├── scripts/build_arcade.py        ← builds the header and body slots (don't need to touch)
└── .github/workflows/main.yml     ← runs everything (don't need to touch)
```

---

## 2. The 6 games

Use these names exactly (lowercase, hyphen where shown). Both the header and the body support all six.

| Game name | In the **header** | In the **body** (on your contribution graph) |
|---|---|---|
| `pacman` | Pac-Man eats dots while two ghosts chase him | Pac-Man eats your contributions |
| `galaga` | A fighter shoots a row of aliens, with a starfield | A ship shoots lasers at your contribution grid |
| `breakout` | A ball and paddle smash a row of bricks | A ball breaks your contribution squares |
| `puzzle-bobble` | A launcher pops groups of matching bubbles | A cannon pops clusters of contributions |
| `bomberman` | A bomber blows up soft blocks with cross-shaped flames | Bombers blast contribution cells |
| `minesweeper` | A solver opens a row of cells, flagging mines | A solver clears your contribution cells |

---

## 3. Change your games

1. Open `arcade.config` in your repo and click the **pencil icon** (Edit).
2. Change the `header` and/or `body` lines (see recipes below).
3. Click **Commit changes**.
4. Open the **Actions** tab. A run called "build arcade profile" starts by itself. Wait about 1-2 minutes for the green tick.
5. Hard refresh your profile (Ctrl+Shift+R). If the old game still shows, wait a few minutes: images are cached.

### Recipes

```ini
# Galaga in the header, Pac-Man on the graph
header = galaga
body = pacman
```

```ini
# Pac-Man in the header, two games on the graph (stacked, first one on top)
header = pacman
body = galaga, breakout
```

```ini
# Same game in both places (matching theme)
header = bomberman
body = bomberman
```

```ini
# Minesweeper header, Puzzle Bobble body
header = minesweeper
body = puzzle-bobble
```

### Rules

- `header` takes **one** game.
- `body` takes **one or two** games, separated by a comma. More than two is rejected (the page gets too long).
- Spelling matters. A wrong name makes the run fail with a clear message listing the valid names.
- The header game and the body games are independent. You can pick any header with any body.

---

## 4. Change the text and numbers in the header

Also in `arcade.config`:

```ini
name = Yuvraj Shishodia
subtitle = Software Engineer · Full-Stack Developer
tagline = SDE @ YNV Solutions | Exploring DevOps

score = 001337
high_score = 999999
credit = 01
```

- Text is shown in capital letters automatically and shrinks to fit if it is long.
- Leave `tagline =` empty to hide that line.
- `score`, `high_score` and `credit` are the arcade numbers at the top (1UP, HIGH SCORE, CREDIT). Set them to anything you like.

---

## 5. One-time setup

Do this once. After that, you only ever edit `arcade.config`.

1. **Allow the workflow to write:** repo **Settings → Actions → General → Workflow permissions → Read and write permissions → Save**.
2. **Add the new files** to your repo (Add file → Create new file, paste the contents, commit). The name box accepts slashes, so typing a path creates the folders:
   - `arcade.config`
   - `scripts/build_arcade.py`
   - `.github/workflows/main.yml` (replace the old contents)
   - `README.md` (replace the old contents)
   - `ARCADE_GUIDE.md` (optional, this guide)
3. **Delete the old files** you no longer need: the `assets/` folder (old header SVGs) and `GAMES_GUIDE.md`.
4. **Run it once:** Actions tab → "build arcade profile" → **Run workflow**. Wait for the green tick.
5. Open your profile and hard refresh.

Until step 4 finishes, the header and graphs will show as broken images.

---

## 6. Editing your README

`README.md` is a normal file now. Nothing overwrites it, so add sections (like Projects) whenever you want. Just leave these three image URLs alone, since they are what displays the games:

- `.../output/header.svg`
- `.../output/body-1.svg` (and `body-1-dark.svg`)
- `.../output/body-2.svg` (and `body-2-dark.svg`)

If you list only one body game, slot 2 becomes a 1×1 transparent image, so it takes up no visible space.

---

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| Images are broken right after setup | The workflow hasn't finished a run yet. Check the Actions tab. |
| Run fails with "Unknown game" | A game name in `arcade.config` is misspelled. Use the names from section 2. |
| Run fails with "can list at most 2 games" | `body` has 3 or more games. Remove one. |
| Run fails with "Expected ...-contribution-graph.svg ... not generated" | The graph generator didn't produce that game. Re-run once. If it repeats, open the failed step's log and send it to me. |
| Run fails with a permissions error | Do setup step 1 (Read and write permissions), then re-run. |
| Old game still showing after a green run | Cache. Hard refresh, or wait a few minutes. |
| Graph looks empty or low | The graph uses your contribution data. Check that "Private contributions" is on in your contribution settings. |
| Header doesn't animate | Some viewers don't play SVG animation. It should play in a normal browser on github.com. |

---

## 8. Cheat sheet

- **Change any game** → edit `header =` / `body =` in `arcade.config`, commit.
- **Two body games** → `body = pacman, galaga`.
- **Change your name or text** → edit `name`, `subtitle`, `tagline` in `arcade.config`.
- **Games:** `pacman`, `galaga`, `breakout`, `puzzle-bobble`, `bomberman`, `minesweeper`.
