# CLANNAD (Switch) – event CGs in full 4:3

An [Atmosphere](https://github.com/Atmosphere-NX/Atmosphere) exefs patch for **CLANNAD on Nintendo Switch** (title ID `010030E00F7C0000`, version **1.0.1**).

The Switch release crops its 4:3 event CGs to fill a 16:9 screen, and the full image only shows if you scroll it with the stick. This patch shows them whole instead, in their original 4:3 framing with black bars at the sides:

- in the story, as soon as a CG appears
- in the stick-scroll view
- in the CG gallery (Extras)

Backgrounds, sprites and the 16:9 CGs are left as they are.

> This is an unofficial fan patch. It is not affiliated with Key, Visual Arts, Prototype or Sekai Project. No game data is included: the patch only changes the game's code in memory, and you need your own copy of the game.

## Requirements

- A Switch running custom firmware with **Atmosphere**
- CLANNAD updated to **version 1.0.1**. To check, highlight CLANNAD on the HOME menu, press **+**, and look at the version. Atmosphere ignores the patch on any other version.

## Install

1. Download the `clannad-cg-fit-*.zip` file from the [latest release](https://github.com/jonny-foley/clannad-switch-cg-fit/releases/latest).
2. Extract it to the root of your SD card, merging its `atmosphere` folder with the one already there. You should end up with:
   ```
   sd:/atmosphere/exefs_patches/clannad_cg_fit/BDF5162CD1682C0941137CF0A5A456DD00000000.ips
   ```
3. Boot into Atmosphere and start the game.

To uninstall, delete `sd:/atmosphere/exefs_patches/clannad_cg_fit/`. Atmosphere applies the patch in memory each time the game starts, so no game files are modified.

### Yuzu and other emulators

Put the same `.ips` file at `load/010030E00F7C0000/clannad_cg_fit/exefs/BDF5162CD1682C0941137CF0A5A456DD00000000.ips` in the emulator's user folder. In Yuzu, right-click the game and choose **Open Mod Data Location**. The game must be on update 1.0.1.

### Lighter alternative

`alternatives/scroll_only/` in this repository holds a smaller patch. It only changes the CG gallery and the stick-scroll view, which open zoomed out to the full image; story CGs still start cropped until you tilt the stick. To use it, download that `.ips` file and put it at the same SD card path instead of the main one.

## What changes

| Where | Unpatched | Patched |
|---|---|---|
| Story, when a 4:3 event CG appears | Cropped to 16:9 | Whole 4:3 image with side bars, from the first frame |
| Story, camera pans the Switch port adds over a CG | Pans across the cropped CG | No pan. The CG stays whole and still, so you only see a short pause where the pan would have been. |
| Story, tilting the stick on a CG | Scrolls the cropped view | Stays on the full view, and stays that way when you leave the scroll view |
| CG gallery | Cropped, scroll with the stick | Opens on the whole image |
| Backgrounds, sprites, 16:9 CGs | — | Unchanged |

The original PC release of CLANNAD is 4:3, so its event CGs never panned. The pans the patch removes were added in the Switch port to show parts of the image hidden by the crop.

## How it works

The game runs on Prototype's LUCA System engine, the same engine as the PC release of *Little Busters! English Edition*. Event CGs are 1920×1440 and are handed to the engine's CG scroller (`cEvScroll`). The scroller already has a zoom-out mode: a zoom value `z` from −1 to 0, where `z = −1` draws the whole image scaled to fit the screen. On Switch only the gallery can reach it, and nothing starts zoomed out.

The patch adds a small routine in the unused padding after the game's code (`main+0x19d2e0`). It "fits" a CG by clearing the CG's crop offset and giving it a scale of `screenH / imageH` (0.75) around the top-centre of the screen. The routine is called from a few places in the engine:

| Site (`main+`) | Change |
|---|---|
| `0x19d2e0` | New code. `is_fit_cg` decides whether an image is a 4:3 event CG; `fit_image` fits it, using the engine's own transform setter. |
| `0x19d800` | A bitmap of the 188 fitted IDs in `EVENTCG.PAK`: the 147 full-size 4:3 CGs, plus the 41 expression parts drawn on top of one of them. Backgrounds (IDs 1018–1360) are excluded. |
| `0x100d88` | The CG scroller starts fitted CGs fully zoomed out (`z = −1`). |
| `0x1794fc`, `0x17992c` | When the story shows a CG, it's fitted straight away. |
| `0x103c1c`, `0x104658` | When the stick-scroll view closes, the CG is fitted again and keeps its position. |
| `0x103894`, `0x1038e4`, `0x1038fc` | The scroll view's "zoom back in" animation is skipped in the story. |
| `0x1a690` | The per-CG camera table returns neutral focus points for fitted CGs. |
| `0x94fa0`, `0x95bf0` | The engine's "place image" and "move image" helpers keep fitted CGs at position (0, 0), which disables the port's pans. |
| `0x3a1d0`, `0x39e50` | The per-image move driver: any move armed on a fitted CG gets a target of (0, 0). Some of the port's pans re-arm a move every frame (for example on FGKT01A just before its cross-fade), and this stops them at the source. |

`fit_image` tags each CG it fits with an invisible marker in the low bits of its scale (about 0.002%), and the move-driver hooks only act on tagged images, so the gallery's own zoom and expression parts are never affected. Loading a new image into the same slot resets its transform, so a fitted CG can't leave a shrunken background behind. Expression parts inherit the CG's transform and position every frame, so they stay aligned with it.

## Building the patch yourself

`make_patch.py` rebuilds both `.ips` files from your own dump of the game's 1.0.1 exefs `main`. Before writing anything it checks the original bytes at every patch site, and it refuses any other build.

```bash
python -m pip install lz4
```
```bash
python make_patch.py "path/to/exefs/main" .
```

It also writes IPSwitch-style `.pchtxt` files listing the same patches.

## Status

Tested on a Switch OLED with Atmosphere and CLANNAD 1.0.1 across several CG scenes. The fixes for expression overlays and the FGKT01A pan were checked in Yuzu with a debugger attached. If you find a CG that's mis-framed or mis-aligned, please open an issue and include the scene or CG.

## License

[MIT](LICENSE)
