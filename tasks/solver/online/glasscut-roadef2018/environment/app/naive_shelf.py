#!/usr/bin/env python3
"""Naive baseline solver for the 2D guillotine glass cutting task.

A deliberately simple constructive heuristic — the shipped scoring anchor B:

  * items are produced in batch file order (always a valid linear
    extension of the per-stack sequences);
  * each used plate carries one or two vertical strips (1-cut branches)
    side by side, plus a trailing waste strip when the second strip does
    not fit the branch width limits; strip boundaries never cross a
    defect;
  * shelves (2-cut branches) are stacked inside a strip from bottom to
    top; items enter the current shelf left to right in file order; an
    item that does not fit closes the shelf (and then the strip, and
    then the plate);
  * every item sits in its own 3-cut box, with a waste rectangle on top
    when the shelf is taller than the item (the 4th / trimming cut);
  * defects: a shelf's y-band grows until no defect crosses its top edge,
    boxes never overlap a defect, and every defect ends up inside exactly
    one waste leaf.

The solver is deterministic (no randomness, no wall-clock dependence) and
single-threaded; it constructs the pattern in a single pass and finishes
in well under a second per run, so it never comes near either tier's time
limit. It writes the output file once, at the end.

Contract: solver <instance_prefix> <output_csv>
  <instance_prefix>_batch.csv / <instance_prefix>_defects.csv and a
  global_param.csv next to them describe the instance; the cutting
  patterns are written to <output_csv> in the task's solution format.
"""
import os
import re
import sys

WASTE, BRANCH = -1, -2


def atoi(s):
    """C atoi semantics (leading whitespace, sign, leading digits) — the
    same truncation the judge's checker applies to every CSV field."""
    m = re.match(r"\s*([+-]?\d+)", s)
    return int(m.group(1)) if m else 0


def read_rows(path):
    rows = []
    with open(path, errors="replace") as f:
        lines = f.read().splitlines()
    for line in lines[1:]:
        if line.strip():
            rows.append(line.split(";"))
    return rows


def parse_instance(prefix):
    gpath = os.path.join(os.path.dirname(prefix), "global_param.csv")
    vals = [atoi(r[1]) for r in read_rows(gpath)]
    names = ["nPlates", "widthPlates", "heightPlates", "min1Cut", "max1Cut",
             "min2Cut", "minWaste"]
    p = dict(zip(names, vals[:len(names)]))
    if p["nPlates"] <= 0 or p["widthPlates"] <= 0 or p["heightPlates"] <= 0:
        raise ValueError("bad global_param.csv")

    items = []  # file order; h = LENGTH_ITEM, w = WIDTH_ITEM (checker axes)
    for r in read_rows(prefix + "_batch.csv"):
        items.append({"id": atoi(r[0]), "h": atoi(r[1]), "w": atoi(r[2])})

    defects = {}  # plate id -> list of (x, y, w, h), sorted for determinism
    for r in read_rows(prefix + "_defects.csv"):
        d = (atoi(r[2]), atoi(r[3]), atoi(r[4]), atoi(r[5]))
        defects.setdefault(atoi(r[1]), []).append(d)
    for pid in defects:
        defects[pid].sort()
    return p, items, defects


class Layout:
    """Single-pass pattern builder for one instance."""

    def __init__(self, params, defects):
        self.p = params
        self.defects = defects
        self.plates = []  # finished plates: {"strips": [strip, ...]}

    # -- geometry helpers -------------------------------------------------

    def strip_defects(self, pid, x0, c):
        """Defects of plate pid intersecting the strip's x-range [x0, x0+c)."""
        return [(dx, dy, dw, dh) for (dx, dy, dw, dh)
                in self.defects.get(pid, [])
                if dx < x0 + c and dx + dw > x0]

    def strip_candidates(self, pid, item):
        """Candidate widths for the first strip of a fresh plate, widest
        first: max1Cut, the triggering item's dimensions, and defect left
        edges — every value within [min1Cut, max1Cut] that no defect of
        this plate crosses (a defect crosses c iff dx < c < dx+dw). The
        item dims are candidates so that a near-max1Cut-wide item can fill
        its strip exactly instead of leaving an illegal sub-minWaste
        sliver. Two-strip widths (leaving room for a second legal 1-cut
        branch) come first, single-strip widths after."""
        p = self.p
        W = p["widthPlates"]
        defs = self.defects.get(pid, [])
        cands = {p["max1Cut"], item["w"], item["h"]}
        cands.update(dx for (dx, dy, dw, dh) in defs)
        two, one = [], []
        for c in sorted(cands, reverse=True):
            if not (p["min1Cut"] <= c <= p["max1Cut"]):
                continue
            if any(dx < c < dx + dw for (dx, dy, dw, dh) in defs):
                continue
            if p["min1Cut"] <= W - c <= p["max1Cut"]:
                two.append(c)
            else:
                one.append(c)
        return two + one

    def shelf_height(self, pid, strip, sy, heights):
        """Shelf band height for content item heights `heights` starting at
        y=sy inside the strip, or None if no legal band fits above sy."""
        p = self.p
        H, min2, minW = p["heightPlates"], p["min2Cut"], p["minWaste"]
        x0, c = strip["x0"], strip["c"]
        S = max([min2] + heights)
        # Two interacting fixpoints, grown together until stable (S only
        # ever grows, so this terminates):
        #  * box-top wastes must be absent or >= minW: every gap S - h in
        #    {0} U [minW,);
        #  * no defect may cross the band's top edge: every defect
        #    overlapping the band lies fully inside it. (No defect crosses
        #    the band's bottom edge by construction of the previous shelf.)
        for _ in range(10000):
            changed = False
            bad = [h for h in heights if 0 < S - h < minW]
            if bad:
                S = max(bad) + minW
                changed = True
            for (dx, dy, dw, dh) in self.strip_defects(pid, x0, c):
                if not (dy < sy + S and dy + dh > sy):
                    continue
                if dy < sy:
                    return None  # invariant broken; bail out
                if dy + dh > sy + S:
                    S = dy + dh - sy
                    changed = True
            if not changed:
                break
        else:
            return None
        if S > H - sy:
            return None
        # The strip-top waste above this shelf must be absent or >= minW.
        if 0 < H - (sy + S) < minW:
            S = H - sy  # fill to the top: no defect is cut at the plate top
            if any(0 < S - h < minW for h in heights):
                return None  # a bad gap remains and S cannot grow further
        return S

    def lay_boxes(self, pid, strip, sy, S, content):
        """Place oriented content items left to right inside the shelf band
        [x0, x0+c) x [sy, sy+S), avoiding defects. Returns the x positions
        (one per content item) or None if they do not all fit."""
        p = self.p
        minW = p["minWaste"]
        x0, c = strip["x0"], strip["c"]
        x1 = x0 + c
        runs = []  # merged blocked x-runs inside the band, clipped to the strip
        for (dx, dy, dw, dh) in self.strip_defects(pid, x0, c):
            if not (dy < sy + S and dy + dh > sy):
                continue
            lo, hi = max(dx, x0), min(dx + dw, x1)
            if runs and lo < runs[-1][1] + minW:
                runs[-1][1] = max(runs[-1][1], hi)
            else:
                runs.append([lo, hi])
        xs = []
        cur = x0  # end of the last placed element (box or waste)
        for it in content:
            w = it["w"]
            x = cur
            placed = False
            for (r0, r1) in runs:
                if r1 <= x:
                    continue
                # Fits in the free segment before this run. Requiring the
                # trailing fragment to x1 to be 0 or >= minW here too keeps
                # the shelf-trailing waste legal wherever the boxes stop.
                if x + w <= r0 and (x1 - (x + w) == 0
                                    or x1 - (x + w) >= minW):
                    xs.append(x)
                    cur = x + w
                    placed = True
                    break
                # Skip over the run: the waste [cur, x_new) covering it is
                # at least minW wide and never reaches the next run (runs
                # are merged with a minW margin).
                x = max(r1, cur + minW)
            if not placed:
                # Free tail segment [x, x1): the shelf-trailing waste must
                # be absent or >= minW.
                if x + w <= x1 and (x1 - (x + w) == 0
                                    or x1 - (x + w) >= minW):
                    xs.append(x)
                    cur = x + w
                    placed = True
            if not placed:
                return None
        return xs

    # -- construction ------------------------------------------------------

    def build(self, items):
        p = self.p
        W = p["widthPlates"]
        plate = None  # open plate: {"cands", "strips", "cur"}

        def close_plate():
            nonlocal plate
            if plate is not None:
                strips = []
                for st in plate["strips"]:
                    shelves = st["shelves"] + ([st["open"]] if st["open"]
                                               else [])
                    strips.append({"x0": st["x0"], "c": st["c"],
                                   "shelves": shelves})
                self.plates.append({"strips": strips})
                plate = None

        def fresh_strip(x0, c):
            return {"x0": x0, "c": c, "shelves": [], "open": None, "sy": 0}

        for it in items:
            orientations = [(it["w"], it["h"])]
            if it["h"] != it["w"]:
                orientations.append((it["h"], it["w"]))
            placed = False
            while not placed:
                if plate is None:
                    if len(self.plates) >= p["nPlates"]:
                        return False
                    plate = {"cands": self.strip_candidates(
                                 len(self.plates), it),
                             "strips": [], "cur": 0}
                if not plate["strips"]:
                    if not plate["cands"]:
                        # unusable plate: leave it empty, move on
                        self.plates.append({"strips": []})
                        plate = None
                        continue
                    c1 = plate["cands"].pop(0)
                    plate["strips"] = [fresh_strip(0, c1)]
                    if p["min1Cut"] <= W - c1 <= p["max1Cut"]:
                        plate["strips"].append(fresh_strip(c1, W - c1))
                pid = len(self.plates)
                # the current strip: append to its open shelf, else open a
                # fresh shelf above its closed shelves
                st = plate["strips"][plate["cur"]]
                if st["open"] is not None:
                    sh = st["open"]
                    for (w, h) in orientations:
                        oit = {"id": it["id"], "w": w, "h": h}
                        content = sh["content"] + [oit]
                        S = self.shelf_height(pid, st, sh["sy"],
                                              [e["h"] for e in content])
                        if S is None:
                            continue
                        xs = self.lay_boxes(pid, st, sh["sy"], S, content)
                        if xs is None:
                            continue
                        sh["content"], sh["S"], sh["xs"] = content, S, xs
                        placed = True
                        break
                    if placed:
                        break
                    # it fits nowhere in the open shelf: close that shelf
                    st["shelves"].append(sh)
                    st["open"] = None
                    st["sy"] = sh["sy"] + sh["S"]
                for (w, h) in orientations:
                    oit = {"id": it["id"], "w": w, "h": h}
                    S = self.shelf_height(pid, st, st["sy"], [h])
                    if S is None:
                        continue
                    xs = self.lay_boxes(pid, st, st["sy"], S, [oit])
                    if xs is None:
                        continue
                    st["open"] = {"sy": st["sy"], "S": S,
                                  "content": [oit], "xs": xs}
                    placed = True
                    break
                if placed:
                    break
                # the item does not fit the current strip: on a fresh plate
                # retry with the next candidate first-strip width; else
                # advance to the second strip or close the plate
                if plate["cur"] == 0 and not st["shelves"] \
                        and st["open"] is None and len(plate["strips"]) > 0:
                    if plate["cands"]:
                        plate["strips"] = []
                        continue
                if plate["cur"] + 1 < len(plate["strips"]):
                    plate["cur"] += 1
                    continue
                close_plate()
        close_plate()
        return True

    # -- emission -----------------------------------------------------------

    def emit(self, out_path):
        p = self.p
        W, H = p["widthPlates"], p["heightPlates"]
        lines = ["PLATE_ID;NODE_ID;X;Y;WIDTH;HEIGHT;TYPE;CUT;PARENT"]
        nid = 0
        for pid, plate in enumerate(self.plates):
            plate_id = nid
            lines.append(f"{pid};{nid};0;0;{W};{H};{BRANCH};0;")
            nid += 1
            used = [st for st in plate["strips"] if st["shelves"]]
            if not used:
                # safety valve: an unusable or empty plate is one big waste
                lines.append(f"{pid};{nid};0;0;{W};{H};{WASTE};1;{plate_id}")
                nid += 1
                continue
            x = 0
            for st in used:
                x0, c, shelves = st["x0"], st["c"], st["shelves"]
                if x0 > x:  # gap strip before this one (unused candidate)
                    lines.append(
                        f"{pid};{nid};{x};0;{x0 - x};{H};{WASTE};1;"
                        f"{plate_id}")
                    nid += 1
                col_id = nid
                lines.append(
                    f"{pid};{nid};{x0};0;{c};{H};{BRANCH};1;{plate_id}")
                nid += 1
                for sh in shelves:
                    sy, S = sh["sy"], sh["S"]
                    sh_id = nid
                    lines.append(
                        f"{pid};{nid};{x0};{sy};{c};{S};{BRANCH};2;{col_id}")
                    nid += 1
                    # children of the shelf along x: boxes and waste gaps
                    sx = x0
                    for it, bx in zip(sh["content"], sh["xs"]):
                        w, h = it["w"], it["h"]
                        if bx > sx:  # defect-covering waste gap
                            lines.append(
                                f"{pid};{nid};{sx};{sy};{bx - sx};{S};"
                                f"{WASTE};3;{sh_id}")
                            nid += 1
                        box_id = nid
                        lines.append(
                            f"{pid};{nid};{bx};{sy};{w};{S};{BRANCH};3;"
                            f"{sh_id}")
                        nid += 1
                        lines.append(
                            f"{pid};{nid};{bx};{sy};{w};{h};{it['id']};4;"
                            f"{box_id}")
                        nid += 1
                        if S > h:
                            lines.append(
                                f"{pid};{nid};{bx};{sy + h};{w};{S - h};"
                                f"{WASTE};4;{box_id}")
                            nid += 1
                        sx = bx + w
                    if sx < x0 + c:  # shelf-trailing waste
                        lines.append(
                            f"{pid};{nid};{sx};{sy};{x0 + c - sx};{S};"
                            f"{WASTE};3;{sh_id}")
                        nid += 1
                # strip-top waste above the last shelf
                top = shelves[-1]["sy"] + shelves[-1]["S"]
                if top < H:
                    lines.append(
                        f"{pid};{nid};{x0};{top};{c};{H - top};{WASTE};2;"
                        f"{col_id}")
                    nid += 1
                x = x0 + c
            if x < W:  # trailing strip (the residual on the last plate)
                lines.append(
                    f"{pid};{nid};{x};0;{W - x};{H};{WASTE};1;{plate_id}")
                nid += 1
        with open(out_path, "w") as f:
            f.write("\n".join(lines) + "\n")


def main():
    if len(sys.argv) != 3:
        print("usage: solver <instance_prefix> <output_csv>",
              file=sys.stderr)
        return 1
    prefix, out_csv = sys.argv[1], sys.argv[2]
    try:
        params, items, defects = parse_instance(prefix)
    except (OSError, ValueError, IndexError) as e:
        print(f"could not load instance: {e}", file=sys.stderr)
        return 1
    lay = Layout(params, defects)
    if not lay.build(items):
        print("instance could not be laid out within the plate limit",
              file=sys.stderr)
        return 1
    lay.emit(out_csv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
