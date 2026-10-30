"""Parametric sliced-plywood coffee table, 36" x 36" (914.4 x 914.4 mm).

The table is a stack of CNC-cut plywood ribs threaded onto steel rods with
spacers between them, like the parametric chair it is based on. Every rib
has the same flat top, but its legs bow in and out and the tunnel underneath
shifts from rib to rib, so the sides read as a flowing wave.

Run `python generate.py` to rebuild everything in ./output:
  coffee_table_3d.stl            3D model of the assembled table (mm)
  coffee_table_all_ribs.dxf      every rib, laid out flat with its rib number
  coffee_table_sheet_NN.dxf      ribs nested on 4x8 ft (1220 x 2440 mm) sheets
  coffee_table_drawing.dxf/.pdf  plan, front and side views with dimensions
  cut_list.csv                   rib list with sizes and hardware

Change the parameters below (measure your real sheet thickness first) and
run it again. Units are millimetres throughout.
"""

import csv
import math
from pathlib import Path

import ezdxf
import numpy as np
import trimesh
from ezdxf.enums import TextEntityAlignment
from shapely import affinity
from shapely.geometry import Point, Polygon, box

# --- Parameters -------------------------------------------------------------

INCH = 25.4
WIDTH = 36 * INCH            # across the ribs (rib profile width)
DEPTH = 36 * INCH            # along the stack of ribs
HEIGHT = 16 * INCH           # finished table height
RIB_T = 18.0                 # measured plywood thickness
RIB_COUNT = 30               # gap between ribs is solved to hit DEPTH exactly

TOP_BAND = 60.0              # straight vertical band at the top of each side
LEG_W = 110.0                # leg width measured across the rib
WAIST = (25.0, 175.0)        # how far the legs bow inward (min, max)
TUNNEL_H = (255.0, 305.0)    # height of the tunnel under the top (min, max)
TOP_CORNER_R = (25.0, 130.0) # top corner radius, middle rib -> end ribs
END_DROP = 22.0              # end ribs sit this much lower, rounding the top edge
TUNNEL_FILLET = 70.0         # radius where the legs meet the top
EDGE_RADIUS = 20.0           # rounding of the outer corners
INNER_RADIUS = 8.0           # min inside radius (>= cutter radius)

ROD_D = 8.0                  # M8 threaded rod
ROD_HOLE_D = 8.5
COUNTERBORE_D = 22.0         # on the outside face of the two end ribs
COUNTERBORE_DEPTH = 10.0
SPACER_OD = 16.0

SHEET = (1220.0, 2440.0)     # 4 x 8 ft
SHEET_MARGIN = 15.0
PART_SPACING = 14.0          # >= 2x cutter diameter

OUT = Path(__file__).parent / "output"

GAP = (DEPTH - RIB_COUNT * RIB_T) / (RIB_COUNT - 1)


# --- Rib geometry -----------------------------------------------------------

def wave(t, cycles, phase):
    """Smooth 0..1 wave across the stack of ribs."""
    return 0.5 + 0.5 * math.sin(2 * math.pi * cycles * t + phase)


def rib_params(i):
    t = i / (RIB_COUNT - 1)
    lerp = lambda rng, f: rng[0] + (rng[1] - rng[0]) * f
    s = abs(2 * t - 1)  # 0 at the middle rib, 1 at the end ribs
    return {
        "top": HEIGHT - END_DROP * s ** 6,
        "corner_r": lerp(TOP_CORNER_R, s ** 3),
        "waist_l": lerp(WAIST, wave(t, 1.0, -0.6)),
        "waist_r": lerp(WAIST, wave(t, 1.0, 2.4)),
        "tunnel_h": lerp(TUNNEL_H, wave(t, 0.75, 1.2) * (1 - s ** 4)),
    }


def side_inset(z, waist):
    """How far an outer side curves inward at height z (0 at floor and top band)."""
    u = z / (HEIGHT - TOP_BAND)
    if u <= 0 or u >= 1:
        return 0.0
    return waist * math.sin(math.pi * u) ** 2


def rib_profile(i):
    """Rib outline in the (y, z) plane: y across the table, z up."""
    p = rib_params(i)
    zs = np.linspace(-1, HEIGHT + 1, 240)
    left = [(side_inset(z, p["waist_l"]), z) for z in zs]
    right = [(WIDTH - side_inset(z, p["waist_r"]), z) for z in zs]
    shape = Polygon(left + right[::-1])

    # Tunnel between the two legs, following the legs' inner edges. It is
    # extended below the floor so rounding it only affects the top corners.
    th = p["tunnel_h"]
    tz = np.linspace(-TUNNEL_FILLET - 20, th, 160)
    t_left = [(side_inset(max(z, 0), p["waist_l"]) + LEG_W, z) for z in tz]
    t_right = [(WIDTH - side_inset(max(z, 0), p["waist_r"]) - LEG_W, z) for z in tz]
    tunnel = Polygon(t_left + t_right[::-1])
    tunnel = tunnel.buffer(-TUNNEL_FILLET, quad_segs=24).buffer(TUNNEL_FILLET, quad_segs=24)

    top, r = p["top"], p["corner_r"]
    rib = shape.difference(tunnel).intersection(box(0, 0, WIDTH, top))
    for y0, cy in ((0, r), (WIDTH - r, WIDTH - r)):
        corner = box(y0, top - r, y0 + r, top).difference(Point(cy, top - r).buffer(r, quad_segs=48))
        rib = rib.difference(corner)
    # Round convex corners, then make sure every inside corner fits the cutter.
    rib = rib.buffer(-EDGE_RADIUS, quad_segs=12).buffer(EDGE_RADIUS, quad_segs=12)
    rib = rib.buffer(INNER_RADIUS, quad_segs=12).buffer(-INNER_RADIUS, quad_segs=12)
    rib = rib.simplify(0.05)
    assert rib.geom_type == "Polygon", f"rib {i + 1} split into pieces"
    return rib


def rod_positions(ribs):
    """Rod holes shared by every rib: three through the top, one in each foot."""
    top_z = HEIGHT - END_DROP - 40.0
    foot_z = 40.0
    candidates = [
        (WIDTH * 0.22, top_z), (WIDTH * 0.5, top_z), (WIDTH * 0.78, top_z),
        (LEG_W * 0.7, foot_z), (WIDTH - LEG_W * 0.7, foot_z),
    ]
    # Each hole needs solid wood around it in every rib.
    for y, z in candidates:
        keepout = Point(y, z).buffer(SPACER_OD / 2 + 12)
        for n, rib in enumerate(ribs, 1):
            assert rib.contains(keepout), f"rod at ({y:.0f}, {z:.0f}) breaks out of rib {n}"
    return candidates


def rib_x(i):
    return i * (RIB_T + GAP)


# --- Outputs ----------------------------------------------------------------

def new_dxf():
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$MEASUREMENT"] = 1
    for name, color in [("CUT_OUTSIDE", 1), ("CUT_HOLES", 5), ("POCKET_COUNTERBORE_10MM", 3),
                        ("LABEL", 7), ("SHEET", 8), ("DIMENSIONS", 7), ("OUTLINE", 7)]:
        doc.layers.add(name, color=color)
    return doc


def add_rib(msp, i, rib, holes, dx, dy):
    """Draw one rib at (dx, dy) as seen from the rib 30 end of the table.

    The face up on the machine is the one facing rib 30. Rib 01 is mirrored
    so that its counterbores end up on its outside face too.
    """
    mirror = i == 0

    def tf(geom):
        if mirror:
            geom = affinity.scale(geom, xfact=-1, origin=(WIDTH / 2, 0))
        return affinity.translate(geom, dx, dy)

    msp.add_lwpolyline(list(tf(rib).exterior.coords), close=True,
                       dxfattribs={"layer": "CUT_OUTSIDE"})
    for y, z in holes:
        c = tf(Point(y, z))
        msp.add_circle((c.x, c.y), ROD_HOLE_D / 2, dxfattribs={"layer": "CUT_HOLES"})
        if i in (0, RIB_COUNT - 1):
            msp.add_circle((c.x, c.y), COUNTERBORE_D / 2,
                           dxfattribs={"layer": "POCKET_COUNTERBORE_10MM"})
    label = tf(Point(WIDTH * 0.36, HEIGHT - 95))
    text = f"RIB {i + 1:02d}"
    if mirror:
        text += " (MIRRORED - THIS FACE OUT)"
    elif i == RIB_COUNT - 1:
        text += " (THIS FACE OUT)"
    msp.add_text(text, height=14, dxfattribs={"layer": "LABEL"}).set_placement(
        (label.x, label.y), align=TextEntityAlignment.MIDDLE_CENTER)


def write_all_ribs(ribs, holes):
    doc = new_dxf()
    msp = doc.modelspace()
    cols = 5
    for i, rib in enumerate(ribs):
        r, c = divmod(i, cols)
        add_rib(msp, i, rib, holes, c * (WIDTH + 60), -r * (HEIGHT + 60))
    doc.saveas(OUT / "coffee_table_all_ribs.dxf")


def write_sheets(ribs, holes):
    """Ribs lie across the 1220 mm width of each sheet, stacked along its length."""
    sheet_w, sheet_l = SHEET
    assert WIDTH + 2 * SHEET_MARGIN <= sheet_w
    per_sheet = int((sheet_l - 2 * SHEET_MARGIN + PART_SPACING) // (HEIGHT + PART_SPACING))
    sheets = [list(range(s, min(s + per_sheet, RIB_COUNT))) for s in range(0, RIB_COUNT, per_sheet)]
    for n, idxs in enumerate(sheets, 1):
        doc = new_dxf()
        msp = doc.modelspace()
        msp.add_lwpolyline([(0, 0), (sheet_w, 0), (sheet_w, sheet_l), (0, sheet_l)], close=True,
                           dxfattribs={"layer": "SHEET"})
        for k, i in enumerate(idxs):
            y0 = SHEET_MARGIN + k * (HEIGHT + PART_SPACING)
            add_rib(msp, i, ribs[i], holes, SHEET_MARGIN, y0)
        doc.saveas(OUT / f"coffee_table_sheet_{n:02d}.dxf")
    return sheets


def write_cut_list(ribs, sheets):
    with open(OUT / "cut_list.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["part", "qty", "material", "size_mm", "notes"])
        for i, rib in enumerate(ribs):
            sheet = next(n for n, s in enumerate(sheets, 1) if i in s)
            minx, miny, maxx, maxy = rib.bounds
            note = "end rib: 22 mm counterbores 10 mm deep on outside face" if i in (0, RIB_COUNT - 1) else ""
            w.writerow([f"RIB {i + 1:02d}", 1, f"{RIB_T:g} mm plywood (sheet {sheet})",
                        f"{maxx - minx:.1f} x {maxy - miny:.1f}", note])
        # Rod ends finish inside the counterbores, flush with the nuts.
        rod_len = DEPTH - 2 * COUNTERBORE_DEPTH + 2 * 8.0
        w.writerow(["Threaded rod M8", 5, "zinc or stainless steel", f"{rod_len:.0f} long",
                    "trim flush with nut after tightening"])
        w.writerow(["Spacer tube", 5 * (RIB_COUNT - 1), f"{SPACER_OD:g} OD x 8.5 ID tube",
                    f"{GAP:.1f} long", "aluminium or nylon; cut to measured gap"])
        w.writerow(["Nut M8 + washer", 10, "steel", "", "sits in end-rib counterbores"])
        w.writerow(["Felt pad 12 mm", 2 * RIB_COUNT, "self-adhesive", "", "one under each rib foot"])


def write_stl(ribs):
    meshes = []
    for i, rib in enumerate(ribs):
        m = trimesh.creation.extrude_polygon(rib, RIB_T)
        # extrude_polygon builds in (x, y) and extrudes along z; map to (y, z, x).
        m.apply_transform(np.array([[0, 0, 1, rib_x(i)],
                                    [1, 0, 0, 0],
                                    [0, 1, 0, 0],
                                    [0, 0, 0, 1]], dtype=float))
        meshes.append(m)
    table = trimesh.util.concatenate(meshes)
    table.export(OUT / "coffee_table_3d.stl")
    return table


def write_drawing(ribs, holes):
    """Plan, front and side views on one sheet, with overall dimensions."""
    doc = new_dxf()
    msp = doc.modelspace()
    dimstyle = doc.dimstyles.get("EZDXF")
    dimstyle.dxf.dimtxt = 30
    dimstyle.dxf.dimasz = 18

    def dim(base, p1, p2, angle=0):
        # Write the measurement ourselves: ezdxf drops the decimal point.
        length = abs(p2[1] - p1[1]) if angle == 90 else abs(p2[0] - p1[0])
        msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, text=f"{length:.1f}",
                           dimstyle="EZDXF", dxfattribs={"layer": "DIMENSIONS"}).render()

    # Front view: looking along the stack, every rib outline overlaid.
    fx, fy = 0.0, 0.0
    for i, rib in enumerate(ribs):
        layer = "OUTLINE" if i in (0, RIB_COUNT - 1) else "LABEL"
        msp.add_lwpolyline([(fx + y, fy + z) for y, z in rib.exterior.coords], close=True,
                           dxfattribs={"layer": layer, "color": 7 if layer == "OUTLINE" else 9})
    for y, z in holes:
        msp.add_circle((fx + y, fy + z), ROD_D / 2, dxfattribs={"layer": "OUTLINE"})
    dim((fx, fy - 80), (fx, fy), (fx + WIDTH, fy))
    dim((fx - 80, fy), (fx, fy), (fx, fy + HEIGHT), angle=90)
    msp.add_text("FRONT VIEW (ALL RIBS OVERLAID)", height=22, dxfattribs={"layer": "LABEL"}).set_placement(
        (fx + WIDTH / 2, fy - 170), align=TextEntityAlignment.MIDDLE_CENTER)

    # Side view: the ribs seen edge-on along their width.
    sx, sy = WIDTH + 300, 0.0
    for i, rib in enumerate(ribs):
        x0, top = sx + rib_x(i), rib.bounds[3]
        msp.add_lwpolyline([(x0, sy), (x0 + RIB_T, sy), (x0 + RIB_T, sy + top), (x0, sy + top)],
                           close=True, dxfattribs={"layer": "OUTLINE"})
    dim((sx, sy - 80), (sx, sy), (sx + DEPTH, sy))
    dim((sx, sy + HEIGHT + 70), (sx + RIB_T, sy + HEIGHT), (sx + RIB_T + GAP, sy + HEIGHT))
    msp.add_text("SIDE VIEW", height=22, dxfattribs={"layer": "LABEL"}).set_placement(
        (sx + DEPTH / 2, sy - 170), align=TextEntityAlignment.MIDDLE_CENTER)

    # Plan view: the slatted top.
    px, py = 0.0, HEIGHT + 300
    for i in range(RIB_COUNT):
        x0 = px + rib_x(i)
        msp.add_lwpolyline([(x0, py), (x0 + RIB_T, py), (x0 + RIB_T, py + WIDTH), (x0, py + WIDTH)],
                           close=True, dxfattribs={"layer": "OUTLINE"})
    dim((px - 80, py), (px, py), (px, py + WIDTH), angle=90)
    msp.add_text("PLAN VIEW", height=22, dxfattribs={"layer": "LABEL"}).set_placement(
        (px + DEPTH / 2, py + WIDTH + 60), align=TextEntityAlignment.MIDDLE_CENTER)

    notes = [
        f'PARAMETRIC COFFEE TABLE  36" x 36" x {HEIGHT / INCH:g}"  ({WIDTH:.1f} x {DEPTH:.1f} x {HEIGHT:.1f} mm)',
        f"{RIB_COUNT} RIBS, {RIB_T:g} MM PLYWOOD, {GAP:.1f} MM GAPS",
        f"5 x M8 THREADED RODS THROUGH {ROD_HOLE_D:g} MM HOLES, {SPACER_OD:g} MM OD SPACERS",
        "ALL DIMENSIONS IN MM",
    ]
    for k, line in enumerate(notes):
        msp.add_text(line, height=18, dxfattribs={"layer": "LABEL"}).set_placement(
            (sx, py + WIDTH - k * 40), align=TextEntityAlignment.LEFT)
    doc.saveas(OUT / "coffee_table_drawing.dxf")

    from ezdxf.addons.drawing import matplotlib as dxf_mpl
    dxf_mpl.qsave(msp, str(OUT / "coffee_table_drawing.pdf"), bg="#FFFFFF", size_inches=(17, 11))


def main():
    OUT.mkdir(exist_ok=True)
    ribs = [rib_profile(i) for i in range(RIB_COUNT)]
    holes = rod_positions(ribs)
    write_all_ribs(ribs, holes)
    sheets = write_sheets(ribs, holes)
    write_cut_list(ribs, sheets)
    table = write_stl(ribs)
    write_drawing(ribs, holes)
    print(f"{RIB_COUNT} ribs x {RIB_T:g} mm, gap {GAP:.2f} mm, {len(sheets)} sheets of 4x8 plywood")
    print(f"overall {table.bounds[1][0]:.1f} (D) x {table.bounds[1][1]:.1f} (W) x {table.bounds[1][2]:.1f} (H) mm")


if __name__ == "__main__":
    main()
