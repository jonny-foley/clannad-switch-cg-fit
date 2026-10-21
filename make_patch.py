"""
Builds the CLANNAD (Switch) "CG fit" exefs patches for Atmosphere.

Usage:
    python make_patch.py <path to exefs 'main'> [output dir]

Two patch sets are produced:

  full          (default, installed under atmosphere/exefs_patches/clannad_cg_fit)
                4:3 event CGs are shown whole everywhere: in the story as soon
                as they appear, in story scroll mode, and in the CG gallery.
                Backgrounds keep the vanilla 16:9 crop, and the port's
                crop-compensating pans on fitted CGs are disabled.

  scroll_only   (fallback, written to alternatives/scroll_only/...)
                The first version: only the gallery and story scroll mode open
                zoomed out; story CGs still start cropped.

How it works
------------
The engine's event-CG scroller (cEvScroll) already has a zoom-out mode: a zoom
tween at +0xd50 holding z in [-1, 0]; its per-frame renderer draws the CG with
scale = 1 + z*(1 - screenH/imageH) and offset*(1 + z) around a top-centre pivot,
so z = -1 is the full 4:3 frame.

A routine in the zero padding after .text (text+0x19d2e0) decides which images
are "fitted CGs": an EVENTCG.PAK image (id 1001-1632) that is not a background
(ids 1018-1360 are backgrounds) and not id 1016, is about 4:3, and is taller
than the screen.

  1. cEvScroll::Start() (text+0x100d88): start fitted CGs with z = -1 and force
     a redraw; everything else starts at z = 0 as in vanilla.
  2. fit_image(): for a fitted CG, crop offset +0x5b4 = 0 and the transform at
     +0xf2c = scale screenH/imageH around (screenW/2, 0).
  3. The story's CG setup calls (text+0x1794fc, +0x17992c) run fit_image right
     after handing the image to cEvScroll, so CGs appear fitted immediately.
  4. The two places that restore the image when scroll mode ends
     (text+0x103c1c, +0x104658) re-fit it in story mode, folding the crop the
     game writes back into the image's Y tween so the position is unchanged.
  5. The exit "zoom back in" animation is skipped in story mode
     (text+0x103894, +0x1038e4, +0x1038fc).
  6. The port's scripted pans are disabled for fitted CGs: the CG table lookup
     (text+0x1a690) returns neutral focus points (columns 5-8), and the image
     load-with-position (text+0x94fa0) and move (text+0x95bf0) helpers get a
     target position of 0. These hooks use a bitmap (text+0x19d800) of the 188
     fitted ids: the 147 full-size 4:3 CGs plus the 41 expression/diff parts
     whose CZ3 canvas is one of those CGs (a pan aimed at a slot holding a diff
     part still moves the base CG underneath it).
  7. The image move driver's two arming functions (text+0x3a1d0, text+0x39e50)
     get a target of (0, 0) when the image is a fitted CG (marked, fitted id,
     not a linked diff part). The port re-arms a per-image move every frame for
     some pans (e.g. FGKT01A before its cross-fade, from text+0x37ab0), which
     this catches at the source without touching draw positions, so
     expression parts stay aligned.

Every site's original bytes are checked before anything is written.
"""
import os
import struct
import sys

try:
    import lz4.block
except ImportError:
    sys.exit("This script needs the 'lz4' package:  python -m pip install lz4")

SUPPORTED_BUILD = "BDF5162CD1682C0941137CF0A5A456DD"  # CLANNAD v1.0.1 main

START_PATCH = (
    0x100d88,
    "68f23591e9031f32090100f968b2369169d236917fca06f93f0100f91f0100f9",
    "49008052697e0db900103e1e60820dbd68b236917fca06f91f7d00a975123b39",
)

# Full set: every site, including a replacement for the 8-instruction block in
# cEvScroll::Start() (it now calls start_zoom in the cave).
FULL = [
    (0x100d88, "68f23591e9031f32090100f968b2369169d236917fca06f93f0100f91f0100f9",
     "e00313aaa67102941f2003d51f2003d51f2003d51f2003d51f2003d51f2003d5"),
    (0x1794fc, "e91cfe97",
     "de8f0094"),
    (0x17992c, "dd1bfe17",
     "d28e0014"),
    (0x103c1c, "61d0fd97",
     "21660294"),
    (0x104658, "d2cdfd97",
     "92630294"),
    (0x103894, "0820201e",
     "0e670214"),
    (0x1038e4, "0820201e",
     "fa660214"),
    (0x1038fc, "0820201e",
     "f4660214"),
    (0x01a690, "3f3c0071",
     "950b0614"),
    (0x095bf0, "ffc301d1",
     "5a1e0414"),
    (0x094fa0, "ffc301d1",
     "87210414"),
    (0x03a1d0, "e923bd6d",
     "0a8d0514"),
    (0x039e50, "ea0f1cfc",
     "ff8d0514"),
    (0x19d2e0, None,
     "fd7bbea9fd030091f35301a9f30300aa530300b4684240b909a50f513fdd0971c8020054"
     "09e90f513f590571690200541fe10f71200200541677fa97f403002ae00313aa9b5efa97"
     "a80400d009fd4db91f00096b2d0100548a06140b0b741e534a010b6b4a558a5a5f410071"
     "6c0000542000805202000014e0031f2af35341a9fd7bc2a8c0035fd6fd7bbda9fd030091"
     "f35301a9f51300f9f30300aaf503012ad8ffff9780040034e00313aa815efa97a80400d0"
     "09fd4db9150100346bfe40b97f090071a1000054640241bd65b645bd8438251e640201bd"
     "2001221e0100221e0018211e0c00261e8c5d1812ad1480528c010d2a8001271e0140201e"
     "0af94db94201221e03102c1e4208231ee303271e7fb205b97fb605b960b23c91e1031f2a"
     "e2031f2ae3031f2ae4031f2ae5031f2a646afb97f51340f9f35341a9fd7bc3a8c0035fd6"
     "fd7bbea9fd030091f30b00f9f30300aa49008052697e0db97f820db97fca06f968b23691"
     "1f7d00a9601e46f9a4ffff97a000003400103e1e60820dbd2900805269123b39f30b40f9"
     "fd7bc2a8c0035fd6fd7bbea9fd030091f30b00f9f30302aa078dfd97e00313aae1031f2a"
     "b6ffff97f30b40f9fd7bc2a8c0035fd6fd7bbfa9fd0300913e6afb9768424cb91f050071"
     "81000054601e46f921008052aaffff97fd7bc1a8c0035fd669424cb93f05007160000054"
     "0820201e011eb3543699fd17291400513f0d00712803005409070090298131911f0009eb"
     "a102005449a40f513fdd0971480200540a0000904a0120912b7d03534b496b3829090012"
     "6b25c91a6b0100363f1c0071a90400d0cb0000546000005420fd4db9c0035fd620f94db9"
     "c0035fd6e0031f2ac0035fd63f3c007150f4f917e102f8373f0c0071ac0200545f240071"
     "680200540c8445f90d5f80522c302d9b8d0980524c302d9b8c01407989a50f513fdd0971"
     "480100540a0000904a0120912b7d03534b496b38290900126b25c91a6b000036e4031f2a"
     "e5031f2affc301d18fe1fb17a101f83769a40f513fdd0971480100540a0000904a012091"
     "2b7d03534b496b38290900126b25c91a6b000036e6031f2ae7031f2affc301d16cdefb17"
     "092049f9490200b50c304fb98c1d00129f950271c10100540c4040b98ca50f519fdd0971"
     "480100540d000090ad0120918e7d0353ae496e388c090012ce25cc1a6e000036e003271e"
     "e103271ee923bd6de372fa17092049f9490200b50c304fb98c1d00129f950271c1010054"
     "0c4040b98ca50f519fdd0971480100540d000090ad0120918e7d0353ae496e388c090012"
     "ce25cc1a6e000036e003271ee103271eea0f1cfcee71fa17000000000000000000000000"
     "000000000000000000000000000000000000000000000000000000000000000000000000"
     "000000000000000000000000000000000000000000000000000000000000000000000000"
     "000000000000000000000000000000000000000000000000000000000000000000000000"
     "000000000000000000000000000000000000000000000000000000000000000000000000"
     "000000000000000000000000000000000000000000000000000000000000000000000000"
     "000000000000000000000000000000000000000000000000000000000000000000000000"
     "000000000000000000000000000000000000000000000000000000000000000000000000"
     "000000000000000000000000000000000000000000000000000000000000000000000000"
     "000000000000000000000000000000000000000000000000000000000000000000000000"
     "00000000000000000000000000000000ff7f010000000000000000000000000000000000"
     "000000000000000000000000000000000000000000000000000300feffffffffffffffff"
     "ffffffff0f00000000000000000000ffffffffffffff7f00"),
]

PATCH_SETS = {
    "full": FULL,
    "scroll_only": [START_PATCH],
}

NSO_HEADER_SIZE = 0x100  # IPS offsets for exefs patches are relative to the NSO header


def load_nso_text(path):
    d = open(path, "rb").read()
    if d[:4] != b"NSO0":
        sys.exit(f"{path} is not an NSO file (expected the exefs 'main').")
    flags = struct.unpack_from("<I", d, 0xC)[0]
    file_off, mem_off, size = struct.unpack_from("<III", d, 0x10)
    comp_size = struct.unpack_from("<I", d, 0x60)[0]
    raw = d[file_off:file_off + comp_size]
    if flags & 1:
        raw = lz4.block.decompress(raw, uncompressed_size=size)
    # pad to the page-aligned mapping so the cave (zero padding) can be checked
    raw += bytes((-len(raw)) % 0x1000)
    return raw, mem_off, d[0x40:0x60]


def make_ips(records):
    out = bytearray(b"PATCH")
    for off, data in records:
        if off >= 1 << 24 or off == 0x454F46:
            sys.exit("offset not representable in IPS")
        out += off.to_bytes(3, "big") + len(data).to_bytes(2, "big") + data
    out += b"EOF"
    return bytes(out)


def check(text, patches):
    for addr, orig, new in patches:
        new = bytes.fromhex(new)
        cur = text[addr:addr + len(new)]
        want = bytes(len(new)) if orig is None else bytes.fromhex(orig)
        if cur == new:
            sys.exit("This 'main' already contains the patch.")
        if cur != want:
            sys.exit(f"Unexpected bytes at text+0x{addr:x}; this build is not supported.")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(__file__))

    text, text_mem_off, build_id = load_nso_text(main_path)
    bid_hex = build_id.hex().upper()
    print(f"Build ID : {bid_hex}")
    if not bid_hex.startswith(SUPPORTED_BUILD) or text_mem_off != 0:
        sys.exit("Only CLANNAD v1.0.1 (build " + SUPPORTED_BUILD + ") is supported.")
    bid_name = bid_hex[:40]

    for name, patches in PATCH_SETS.items():
        check(text, patches)
        records = [(a + NSO_HEADER_SIZE, bytes.fromhex(n)) for a, _, n in patches]
        root = out_dir if name == "full" else os.path.join(out_dir, "alternatives", name)
        ips_dir = os.path.join(root, "atmosphere", "exefs_patches", "clannad_cg_fit")
        os.makedirs(ips_dir, exist_ok=True)
        ips_path = os.path.join(ips_dir, bid_name + ".ips")
        open(ips_path, "wb").write(make_ips(records))
        print(f"Wrote    : {ips_path}")

        pch_path = os.path.join(root, f"clannad_cg_fit_{name}.pchtxt")
        with open(pch_path, "w", newline="\n") as f:
            f.write(f"@nsobid-{bid_name}\n\n")
            f.write(f"# CLANNAD - show 4:3 event CGs whole ({name})\n")
            f.write("@flag offset_shift 0x100\n\n")
            f.write("@enabled\n")
            for a, _, n in patches:
                f.write(f"{a:08X} {n.upper()}\n")
            f.write("@stop\n")
        print(f"Wrote    : {pch_path}")


if __name__ == "__main__":
    main()
