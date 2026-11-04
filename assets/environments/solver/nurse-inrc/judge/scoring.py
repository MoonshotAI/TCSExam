"""Shared scoring logic for the nurse-inrc task (INRC-I nurse rostering).

Used by BOTH sides so the formula and the validity check cannot diverge:
  - agent side:  /app/score_public.py   (public instances, public reference)
  - judge side:  /tests/checker.py      (hidden instances, hidden reference)

Pipeline: run `bash /app/build.sh` (must produce /app/solver) -> for each
instance, run `solver < instance.xml` with the per-instance wall-clock
budget in env NURSE_INSTANCE_SECONDS (the process group is hard-killed at
the limit) -> validate the roster printed on stdout and recompute its soft
constraint penalty with check_roster() below -> A = penalty of the (valid)
roster -> per-instance gap ratio r = (B - A) / (B - K), unclipped -> arithmetic mean over participating instances (B > K).

Instance/solution formats: the official INRC-I XML formats (First
International Nurse Rostering Competition 2010). The solver reads an
instance (<SchedulingPeriod> ...) on stdin and writes a solution
(<Solution> ... <Assignment><Date/><Employee/><ShiftType/></Assignment> ...)
on stdout.

VALIDITY (hard rules — an invalid roster scores 0 for that instance):
  1. The output parses as one <Solution> element whose SchedulingPeriodID
     matches the instance ID, and every <Assignment> names a known employee,
     a known shift type, and a date inside the planning period.
  2. Exact coverage: for every (day, shift type), the number of assignments
     equals the required number (cover requirements are hard in INRC-I;
     over-covering is as invalid as under-covering — this matches the
     official competition evaluator).
  3. One shift per nurse per day (the second INRC-I hard constraint).

PENALTY SEMANTICS: the soft-constraint penalty is recomputed from scratch
with a faithful port of the official INRC-I competition evaluator
(validatorINRC.jar, the numbering-based evaluation method of the
competition spec). The port was validated against the official jar on
thousands of generated rosters (see tests/calibration/fuzz_report.md).
Two contract elements exist in the instance files but are NOT evaluated by
the official evaluator (parsed, then ignored: NoNightShiftBeforeFreeWeekend
and MaxWorkingWeekendsInFourWeeks), and DayOn/ShiftOn requests are
evaluated to zero by the official evaluator; this port reproduces the
official behaviour exactly, because the best-known values K were computed
with that evaluator. None of the 60 competition instances use
DateSpecificCover, DayOn/ShiftOn requests or TwoFreeDaysAfterNightShifts.

Time budget (aligned with the official INRC-I medium track):
EACH INSTANCE gets its own wall-clock limit of PER_INSTANCE_SECONDS
(600 s — the INRC-I medium track's approximately-10-minute target; the
sprint track's ~10-second and the long track's ~10-hour targets are
impractical as a single uniform budget, so the medium official tier is
the alignment target).
There is no shared pool and no redistribution — the solver sees one
instance at a time and may use the full per-instance budget on it.
Instances are evaluated in parallel (JUDGE_JOBS workers, each pinned to a
core with taskset). Validity checking does not consume the limit.

The raw unclipped values are reported per instance; raw > 1 means the
submission beat the best-known published value and is investigated, never silently dropped;
under the finalized formula it counts unclipped (r > 1).

Formula finalized 2026-09-20: the judged score is the pure gap ratio r —
A=B -> 0, A=K -> 1, beating K -> r > 1, worse than B -> r < 0, with no
[0, 1] clip — averaged over the participating instances by the unified
metric engine (tests/metric/engine.py) from the per-instance raw values
and anchors this file reports. This file's local `score` field still
clips r to [0, 1] and `reward` stays that clipped mean; both are kept
for the retired local-judging pipeline only and are not the judged score.
"""

import json
import os
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
# Per-instance wall-clock budget (INRC-I medium-track official target:
# approximately 10 minutes = 600 s).
PER_INSTANCE_SECONDS = float(os.environ.get("PER_INSTANCE_SECONDS", "600"))


def _cpu_quota():
    """Effective CPU count honoring cgroup limits (the judge container gets
    cpus=4; os.cpu_count() would report the HOST's cores and oversubscribe).
    Reads cgroup v2 cpu.max and cpuset, falls back to os.cpu_count()."""
    quota = None
    try:
        with open("/sys/fs/cgroup/cpu.max") as f:
            parts = f.read().split()
        if parts[0] != "max":
            quota = max(1, int(float(parts[0]) // float(parts[1])))
    except (OSError, ValueError, IndexError, ZeroDivisionError):
        pass
    try:
        with open("/sys/fs/cgroup/cpuset.cpus.effective") as f:
            cpus = f.read().strip()
        if cpus:
            n = 0
            for chunk in cpus.split(","):
                if "-" in chunk:
                    lo, hi = chunk.split("-", 1)
                    n += int(hi) - int(lo) + 1
                else:
                    n += 1
            quota = min(quota, n) if quota else n
    except (OSError, ValueError):
        pass
    return quota or (os.cpu_count() or 1)


JUDGE_JOBS = int(os.environ.get("JUDGE_JOBS", "0")) or _cpu_quota()

U = 0x3FFFFFFF  # "undefined" marker of the numbering method

WEEKDAY_NAME = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                "Saturday", "Sunday"]


# ---------------------------------------------------------------------------
# Instance parsing
# ---------------------------------------------------------------------------

def _bool(s):
    return str(s).strip() in ("true", "1")


class Instance:
    def __init__(self):
        self.id = None
        self.num_days = 0
        self.dates = []               # list of date, index = day index
        self.shifts = []              # shift IDs in XML order (index matters)
        self.shift_skills = {}        # shift ID -> set of required skills
        self.night_index = -1         # index of shift crossing midnight (info)
        self.patterns = {}            # pattern ID -> (weight, [(shiftSel, daySel)])
        self.contracts = {}           # contract ID -> dict of parameters
        self.employees = []           # employee IDs
        self.emp_contract = {}        # employee ID -> contract ID
        self.emp_skills = {}          # employee ID -> set of skills
        self.cover = {}               # (day index, shift index) -> required
        self.day_off = {}             # employee ID -> list of (day index, weight)
        self.shift_off = {}           # employee ID -> list of (day index, shift index, weight)
        self.day_on = {}
        self.shift_on = {}
        # weekend layout helpers (per contract weekend definition)
        self.first_saturday = -1
        self.num_weekends = 0


def load_instance(path):
    """Parse an INRC-I XML instance into an Instance."""
    root = ET.parse(path).getroot()
    if root.tag != "SchedulingPeriod":
        raise ValueError("root element is not SchedulingPeriod")
    sp = Instance()
    sp.id = root.get("ID")
    y, m, d = map(int, root.findtext("StartDate").split("-"))
    start = date(y, m, d)
    y, m, d = map(int, root.findtext("EndDate").split("-"))
    end = date(y, m, d)
    sp.num_days = (end - start).days + 1
    sp.dates = [start + timedelta(days=i) for i in range(sp.num_days)]
    for i, dd in enumerate(sp.dates[:7]):
        if dd.weekday() == 5:
            sp.first_saturday = i
            break
    n = sp.first_saturday
    while 0 <= n < sp.num_days:
        sp.num_weekends += 1
        n += 7

    st = root.find("ShiftTypes")
    for s in st.findall("Shift"):
        sid = s.get("ID")
        sp.shifts.append(sid)
        sk = s.find("Skills")
        sp.shift_skills[sid] = set(e.text for e in sk) if sk is not None else set()
        t1 = s.findtext("StartTime")
        t2 = s.findtext("EndTime")
        if t2 <= t1:  # crosses midnight -> night shift (informational only)
            sp.night_index = len(sp.shifts) - 1

    pats = root.find("Patterns")
    if pats is not None:
        for p in pats.findall("Pattern"):
            entries = []
            for e in p.find("PatternEntries").findall("PatternEntry"):
                entries.append((e.findtext("ShiftType"), e.findtext("Day")))
            sp.patterns[p.get("ID")] = (int(p.get("weight")), entries)

    cons = root.find("Contracts")
    for c in cons.findall("Contract"):
        cid = c.get("ID")
        ct = {}
        for tag in ("MaxNumAssignments", "MinNumAssignments",
                    "MaxConsecutiveWorkingDays", "MinConsecutiveWorkingDays",
                    "MaxConsecutiveFreeDays", "MinConsecutiveFreeDays",
                    "MaxConsecutiveWorkingWeekends",
                    "MinConsecutiveWorkingWeekends",
                    "MaxWorkingWeekendsInFourWeeks"):
            el = c.find(tag)
            if el is None:
                ct[tag] = (False, 0, 0)
            else:
                ct[tag] = (_bool(el.get("on", "false")),
                           int(el.get("weight", "0")),
                           int(el.text.strip()))
        for tag in ("SingleAssignmentPerDay", "CompleteWeekends",
                    "IdenticalShiftTypesDuringWeekend",
                    "NoNightShiftBeforeFreeWeekend",
                    "TwoFreeDaysAfterNightShifts", "AlternativeSkillCategory"):
            el = c.find(tag)
            if el is None:
                ct[tag] = (False, 0)
            else:
                ct[tag] = (_bool(el.text), int(el.get("weight", "0")))
        wk = c.find("WeekendDefinition")
        ct["WeekendDefinition"] = wk.text.strip() if wk is not None else "SaturdaySunday"
        up = c.find("UnwantedPatterns")
        ct["UnwantedPatterns"] = [p.text for p in up.findall("Pattern")] if up is not None else []
        sp.contracts[cid] = ct

    emps = root.find("Employees")
    for e in emps.findall("Employee"):
        eid = e.get("ID")
        sp.employees.append(eid)
        sp.emp_contract[eid] = e.findtext("ContractID")
        sk = e.find("Skills")
        sp.emp_skills[eid] = set(x.text for x in sk) if sk is not None else set()
        sp.day_off[eid] = []
        sp.shift_off[eid] = []
        sp.day_on[eid] = []
        sp.shift_on[eid] = []

    # Cover requirements: day-of-week cover, overridden per (day, shift) by
    # date-specific cover. (None of the 60 INRC-I instances uses
    # DateSpecificCover; the override rule follows the spec.)
    dow = {}   # (weekday name, shift ID) -> required
    specific = {}  # (date, shift ID) -> required
    cr = root.find("CoverRequirements")
    if cr is not None:
        for ch in cr:
            if ch.tag == "DayOfWeekCover":
                dname = ch.findtext("Day")
                for cv in ch.findall("Cover"):
                    dow[(dname, cv.findtext("Shift"))] = int(cv.findtext("Preferred"))
            elif ch.tag == "DateSpecificCover":
                dtext = ch.findtext("Date")
                for cv in ch.findall("Cover"):
                    specific[(dtext, cv.findtext("Shift"))] = int(cv.findtext("Preferred"))
    shift_index = {s: i for i, s in enumerate(sp.shifts)}
    for di, dd in enumerate(sp.dates):
        wname = WEEKDAY_NAME[dd.weekday()]
        dtext = dd.isoformat()
        for sid in sp.shifts:
            req = specific.get((dtext, sid), dow.get((wname, sid), 0))
            if req:
                sp.cover[(di, shift_index[sid])] = req

    def _parse_requests(tag, sing, store, with_shift):
        r = root.find(tag)
        if r is None:
            return
        for el in r.findall(sing):
            w = int(el.get("weight", "0"))
            eid = el.findtext("EmployeeID")
            dt = el.findtext("Date")
            y, m, d = map(int, dt.split("-"))
            di = (date(y, m, d) - sp.dates[0]).days
            if with_shift:
                store.setdefault(eid, []).append(
                    (di, shift_index[el.findtext("ShiftTypeID")], w))
            else:
                store.setdefault(eid, []).append((di, w))

    _parse_requests("DayOffRequests", "DayOff", sp.day_off, False)
    _parse_requests("DayOnRequests", "DayOn", sp.day_on, False)
    _parse_requests("ShiftOffRequests", "ShiftOff", sp.shift_off, True)
    _parse_requests("ShiftOnRequests", "ShiftOn", sp.shift_on, True)
    return sp


# ---------------------------------------------------------------------------
# Solution parsing
# ---------------------------------------------------------------------------

def parse_solution(text):
    """Parse a <Solution> document. Returns (period_id, [(emp, daystr, shift)])
    or raises ValueError."""
    root = ET.fromstring(text)
    if root.tag != "Solution":
        raise ValueError("root element is not Solution")
    pid = root.findtext("SchedulingPeriodID")
    out = []
    for a in root.findall("Assignment"):
        emp = a.findtext("Employee")
        dtx = a.findtext("Date")
        stx = a.findtext("ShiftType")
        if emp is None or dtx is None or stx is None:
            raise ValueError("an Assignment misses Date/Employee/ShiftType")
        out.append((emp.strip(), dtx.strip(), stx.strip()))
    return (pid.strip() if pid else None), out


# ---------------------------------------------------------------------------
# Penalty evaluation — faithful port of the official INRC-I evaluator's
# numbering method (initialise/intermediate/final phases).
# ---------------------------------------------------------------------------

class _Cond:
    def __init__(self, size):
        self.numbering = [U] * size
        self.last_nr_history = U
        self.future_nr = U
        self.max_total = -1
        self.min_total = -1
        self.max_between = -1
        self.min_between = -1
        self.max_consecutive = -1
        self.min_consecutive = -1
        self.cost_max_total = 0
        self.cost_min_total = 0
        self.cost_max_between = 0
        self.cost_min_between = 0
        self.cost_max_consecutive = 0
        self.cost_min_consecutive = 0
        self.max_pert = [0] * size
        self.min_pert = [0] * size
        self.cost_max_pert = [0] * size
        self.cost_min_pert = [0] * size


def _weekend_layout(sp, weekend_def):
    """(begin day index, days-in-weekend) replicating the official evaluator:
    weekends anchor at the first Saturday; Friday* definitions start one day
    earlier; if day 0 itself is a Saturday the first weekend is skipped for
    the weekend-run and identical-weekend conditions (quirk of the official
    code, reproduced; not triggered by the 60 instances)."""
    fs = sp.first_saturday
    begin = fs
    if weekend_def == "SaturdaySunday":
        ln = 2
    elif weekend_def == "FridaySaturdaySunday":
        begin -= 1
        ln = 3
    elif weekend_def == "FridaySaturdaySundayMonday":
        begin -= 1
        ln = 4
    elif weekend_def == "SaturdaySundayMonday":
        ln = 3
    else:
        raise ValueError(f"unknown weekend definition {weekend_def}")
    return begin, ln


def _build_conditions(sp, emp):
    """Build every soft condition for one employee (official evaluator port)."""
    D = sp.num_days
    S = len(sp.shifts)
    size = D * S
    ct = sp.contracts[sp.emp_contract[emp]]
    conds = []

    # --- max/min consecutive working days (day numbering, events = work days)
    c = _Cond(size)
    c.numbering = [i // S for i in range(size)]
    on, w, v = ct["MaxConsecutiveWorkingDays"]
    if on:
        c.max_consecutive, c.cost_max_consecutive = v, w
    on, w, v = ct["MinConsecutiveWorkingDays"]
    if on:
        c.min_consecutive, c.cost_min_consecutive = v, w
    conds.append(c)

    # --- max/min consecutive free days (gaps between work-day events;
    #     virtual work events at day -1 and day num_days)
    c = _Cond(size)
    c.numbering = [i // S for i in range(size)]
    c.last_nr_history = -1
    c.future_nr = D
    on, w, v = ct["MaxConsecutiveFreeDays"]
    if on:
        c.max_between, c.cost_max_between = v, w
    on, w, v = ct["MinConsecutiveFreeDays"]
    if on:
        c.min_between, c.cost_min_between = v, w
    conds.append(c)

    # --- max/min total assignments
    c = _Cond(size)
    c.numbering = list(range(size))
    on, w, v = ct["MaxNumAssignments"]
    if on:
        c.max_total, c.cost_max_total = v, w
    on, w, v = ct["MinNumAssignments"]
    if on:
        c.min_total, c.cost_min_total = v, w
    conds.append(c)

    # (The official evaluator never enables the one-shift-per-day condition —
    # its parser reads a nonexistent element name. We enforce one-shift-per-day
    # as a hard validity rule instead, per the INRC-I spec.)

    # --- identical shift types during weekend (min pert per (weekend, shift))
    begin, ln = _weekend_layout(sp, ct["WeekendDefinition"])
    begin_w = begin  # Saturday anchor for this contract's weekend definition
    c = _Cond(size)
    on, w = ct["IdenticalShiftTypesDuringWeekend"]
    if on:
        b = begin_w
        if sp.first_saturday == 0:
            b += 7
        getal = 1
        for i in range(sp.num_weekends):
            for k in range(S):
                for j in range(ln):
                    pos = (b + i * 7 + j) * S + k
                    if 0 <= b + i * 7 + j < D:
                        c.numbering[pos] = getal
                c.min_pert[getal] = ln
                c.cost_min_pert[getal] = w
                getal += 1
            getal += ln + 1
    conds.append(c)

    # --- complete weekends (min consecutive = days in weekend)
    c = _Cond(size)
    on, w = ct["CompleteWeekends"]
    if on:
        counter = 0
        for i in range(sp.num_weekends):
            for j in range(ln):
                day = begin_w + i * 7 + j
                if 0 <= day < D:
                    for k in range(S):
                        c.numbering[day * S + k] = counter
                counter += 1
            counter += 2
        c.min_consecutive = ln
        c.cost_min_consecutive = w
    conds.append(c)

    # --- requested days off (max pert 0 per request)
    c = _Cond(size)
    for counter, (di, w) in enumerate(sp.day_off.get(emp, [])):
        for k in range(S):
            c.numbering[di * S + k] = counter
        c.max_pert[counter] = 0
        c.cost_max_pert[counter] = w
    conds.append(c)

    # --- requested shifts off
    c = _Cond(size)
    for counter, (di, si, w) in enumerate(sp.shift_off.get(emp, [])):
        c.numbering[di * S + si] = counter
        c.max_pert[counter] = 0
        c.cost_max_pert[counter] = w
    conds.append(c)

    # (RequestedDayOn / RequestedShiftOn exist in the official evaluator but
    # with min_pert = 0, i.e. they can never fire; and none of the 60
    # instances contains such requests. Not built.)

    # --- max/min consecutive working weekends (weekend numbering)
    c = _Cond(size)
    b = begin_w + (7 if sp.first_saturday == 0 else 0)
    for i in range(sp.num_weekends):
        for j in range(ln):
            day = b + i * 7 + j
            if 0 <= day < D:
                for k in range(S):
                    c.numbering[day * S + k] = i
    on, w, v = ct["MinConsecutiveWorkingWeekends"]
    if on:
        c.min_consecutive, c.cost_min_consecutive = v, w
    on, w, v = ct["MaxConsecutiveWorkingWeekends"]
    if on:
        c.max_consecutive, c.cost_max_consecutive = v, w
    conds.append(c)

    # --- alternative skill (per assignment lacking a required skill)
    c = _Cond(size)
    on, w = ct["AlternativeSkillCategory"]
    if on:
        nr = 0
        have = sp.emp_skills.get(emp, set())
        for pos in range(size):
            sid = sp.shifts[pos % S]
            if not sp.shift_skills[sid] <= have:
                c.numbering[pos] = nr
                c.max_pert[nr] = 0
                c.cost_max_pert[nr] = w
                nr += 1
    conds.append(c)

    # --- unwanted patterns (three shapes occur in the 60 instances:
    #     all-specific any-day chains via buildSTSTST_Any; the fixed-day
    #     None(Friday)-Any(Saturday)-Any(Sunday) via buildFWW_Fixed;
    #     all-specific fixed-first-day chains via buildSTSTST_Fixed)
    for pid in ct["UnwantedPatterns"]:
        weight, entries = sp.patterns[pid]
        plen = len(entries)
        types = ["S" if st not in ("Any", "None") else st for st, _ in entries]
        first_day = entries[0][1]
        if all(t == "S" for t in types) and first_day == "Any":
            # one condition per phase w in 0..plen-1
            for w0 in range(plen):
                c = _Cond(size)
                counter = 0
                j = 0
                while w0 + j * plen + plen - 1 < D:
                    daypos = w0 + j * plen
                    for i in range(plen):
                        sid = entries[i][0]
                        si = sp.shifts.index(sid)
                        c.numbering[(daypos + i) * S + si] = counter
                        counter += 1
                    counter += 2
                    j += 1
                c.max_consecutive = plen - 1
                c.cost_max_consecutive = weight
                conds.append(c)
        elif types[0] == "None" and all(t == "Any" for t in types[1:]) and first_day != "Any":
            # fixed-day FWW (None(Friday)-Any(Saturday)-Any(Sunday))
            target = WEEKDAY_NAME.index(first_day)  # Monday=0..Sunday=6
            first_occ = None
            for i, dd in enumerate(sp.dates[:7]):
                if dd.weekday() == target:
                    first_occ = i
                    break
            num_weeks = -(-D // 7)
            for j in range(num_weeks):
                daypos = first_occ + j * 7
                if daypos >= D:
                    continue
                c = _Cond(size)
                c.last_nr_history = 0
                for k in range(S):
                    c.numbering[daypos * S + k] = 3
                for i in range(1, plen):
                    if daypos + i < D:
                        for k in range(S):
                            c.numbering[(daypos + i) * S + k] = 4
                c.max_between = 2
                c.cost_max_between = weight
                conds.append(c)
        elif all(t == "S" for t in types) and first_day != "Any":
            # fixed first day chain (not present in the 60 instances; ported
            # from buildSTSTST_Fixed for completeness)
            target = WEEKDAY_NAME.index(first_day)
            first_occ = None
            for i, dd in enumerate(sp.dates[:7]):
                if dd.weekday() == target:
                    first_occ = i
                    break
            c = _Cond(size)
            counter = 0
            num_weeks = -(-D // 7)
            for j in range(num_weeks):
                daypos = first_occ + j * 7
                if daypos + plen - 1 >= D:
                    continue
                for i in range(plen):
                    si = sp.shifts.index(entries[i][0])
                    c.numbering[(daypos + i) * S + si] = counter + i
                counter += plen + 2
            c.max_consecutive = plen - 1
            c.cost_max_consecutive = weight
            conds.append(c)
        else:
            raise ValueError(f"unsupported pattern shape in pattern {pid}: {entries}")

    # (NoNightShiftBeforeFreeWeekend and MaxWorkingWeekendsInFourWeeks are
    # parsed by the official evaluator but never evaluated; not built.
    # TwoFreeDaysAfterNightShifts is absent from all 60 instances; the
    # reference build asserts this.)
    return conds


def _run_condition(cond, worked):
    """Port of the official intermediate+final evaluation for one condition.
    worked[pos] = True iff the employee has an assignment at that time unit."""
    pen = 0
    total = 0
    consecutive = 1
    last_nr = cond.last_nr_history
    event = False
    pert = [0] * len(cond.numbering)
    for pos, w in enumerate(worked):
        if not w:
            continue
        nr = cond.numbering[pos]
        if nr == U:
            continue
        event = True
        total += 1
        if nr == last_nr + 1:
            consecutive += 1
        elif nr > last_nr + 1:
            if 0 < consecutive < cond.min_consecutive and cond.cost_min_consecutive > 0:
                pen += cond.cost_min_consecutive * (cond.min_consecutive - consecutive)
            if consecutive > cond.max_consecutive and cond.cost_max_consecutive > 0:
                pen += cond.cost_max_consecutive * (consecutive - cond.max_consecutive)
            g = nr - last_nr - 1
            if g < cond.min_between and cond.cost_min_between > 0:
                pen += cond.cost_min_between * (cond.min_between - g)
            if g > cond.max_between and cond.cost_max_between > 0:
                pen += cond.cost_max_between * (g - cond.max_between)
            consecutive = 1
        pert[nr] += 1
        last_nr = nr
    # final phase
    if total > cond.max_total and cond.cost_max_total > 0:
        pen += cond.cost_max_total * (total - cond.max_total)
    if total < cond.min_total and cond.cost_min_total > 0:
        pen += cond.cost_min_total * (cond.min_total - total)
    if cond.future_nr != U and last_nr == cond.future_nr - 1:
        consecutive += 1
    if event and consecutive > cond.max_consecutive and cond.cost_max_consecutive > 0:
        pen += cond.cost_max_consecutive * (consecutive - cond.max_consecutive)
    if last_nr != U and consecutive < cond.min_consecutive and cond.cost_min_consecutive > 0:
        pen += cond.cost_min_consecutive * (cond.min_consecutive - consecutive)
    if last_nr != U and cond.future_nr != U and cond.cost_max_between > 0:
        val = cond.future_nr - last_nr - 1
        if val > cond.max_between:
            pen += cond.cost_max_between * (val - cond.max_between)
    if last_nr != U and cond.future_nr != U and cond.cost_min_between > 0:
        val = cond.future_nr - last_nr - 1
        if 0 < val < cond.min_between:
            pen += cond.cost_min_between * (cond.min_between - val)
    for t in range(len(pert)):
        if pert[t] != 0 and pert[t] > cond.max_pert[t] and cond.cost_max_pert[t] > 0:
            pen += cond.cost_max_pert[t] * (pert[t] - cond.max_pert[t])
        if pert[t] == 0 or pert[t] >= cond.min_pert[t] or cond.cost_min_pert[t] <= 0:
            continue
        pen += cond.cost_min_pert[t] * (cond.min_pert[t] - pert[t])
    return pen


def evaluate_roster(sp, assignments):
    """Penalty of a roster given as {(emp, day_index): shift_index}.
    Does NOT check validity — callers use check_roster for that."""
    total = 0
    per_emp = {}
    for emp in sp.employees:
        per_emp[emp] = {}
    for (emp, di), si in assignments.items():
        per_emp[emp][di] = si
    for emp in sp.employees:
        worked = [False] * (sp.num_days * len(sp.shifts))
        for di, si in per_emp[emp].items():
            worked[di * len(sp.shifts) + si] = True
        for cond in _build_conditions(sp, emp):
            total += _run_condition(cond, worked)
    return total


def check_roster(instance_path, out_path):
    """Validate the solver output and recompute its penalty from scratch.
    Returns (penalty, None) for a valid roster, else (None, reason)."""
    try:
        sp = load_instance(instance_path)
    except (ValueError, OSError, ET.ParseError) as e:
        return None, f"could not load instance: {e}"
    try:
        with open(out_path, errors="replace") as f:
            text = f.read()
    except OSError as e:
        return None, f"could not read solver output: {e}"
    try:
        pid, raw = parse_solution(text)
    except (ValueError, ET.ParseError) as e:
        return None, f"solution XML does not parse: {e}"
    if pid != sp.id:
        return None, f"SchedulingPeriodID {pid!r} does not match instance {sp.id!r}"
    shift_index = {s: i for i, s in enumerate(sp.shifts)}
    emp_set = set(sp.employees)
    assignments = {}
    per_day_count = {}
    per_emp_day = {}
    for emp, dtx, stx in raw:
        if emp not in emp_set:
            return None, f"unknown employee {emp!r}"
        if stx not in shift_index:
            return None, f"unknown shift type {stx!r}"
        try:
            y, m, d = map(int, dtx.split("-"))
            di = (date(y, m, d) - sp.dates[0]).days
        except ValueError:
            return None, f"unparseable date {dtx!r}"
        if not (0 <= di < sp.num_days):
            return None, f"date {dtx} outside the planning period"
        si = shift_index[stx]
        assignments[(emp, di)] = assignments.get((emp, di), -1)
        if assignments[(emp, di)] != -1:
            return None, f"employee {emp} has more than one assignment on {dtx}"
        assignments[(emp, di)] = si
        per_day_count[(di, si)] = per_day_count.get((di, si), 0) + 1
        per_emp_day[(emp, di)] = True
    # exact coverage
    need = set(sp.cover)
    have = set(per_day_count)
    for key in need | have:
        req = sp.cover.get(key, 0)
        got = per_day_count.get(key, 0)
        if got != req:
            di, si = key
            return None, (f"coverage mismatch on {sp.dates[di].isoformat()} "
                          f"shift {sp.shifts[si]}: required {req}, assigned {got}")
    return evaluate_roster(sp, assignments), None


# ---------------------------------------------------------------------------
# Judging pipeline (shared by the public self-score and the hidden judge)
# ---------------------------------------------------------------------------

def build_solver(app_dir, timeout=BUILD_TIMEOUT):
    """Run the agent-visible build script; require /app/solver afterwards."""
    script = os.path.join(app_dir, "build.sh")
    if not os.path.exists(script):
        return None, "no /app/build.sh found"
    try:
        p = subprocess.run(
            ["bash", script], cwd=app_dir, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, f"build.sh timed out after {timeout}s"
    solver = os.path.join(app_dir, "solver")
    if not (os.path.exists(solver) and os.access(solver, os.X_OK)):
        tail = ((p.stdout or "") + (p.stderr or ""))[-3000:]
        return None, (f"build.sh finished (exit {p.returncode}) but did not "
                      f"produce an executable /app/solver\n{tail}")
    return solver, None


def run_solver(solver, instance_path, out_path, limit_seconds, core=None):
    """Run solver < instance > out_path with a hard per-instance wall-clock
    limit, optionally pinned to a core via taskset.

    The solver learns the limit via env NURSE_INSTANCE_SECONDS (and, for
    backward compatibility with the shipped baseline's safety-cap
    computation, NURSE_TIME_POOL is set to the same value) and is free to
    use as much of it as it wants on this instance. Returns
    (seconds, None) on success, (seconds, reason) otherwise.
    """
    env = dict(os.environ)
    env["NURSE_INSTANCE_SECONDS"] = f"{limit_seconds:.3f}"
    env["NURSE_TIME_POOL"] = f"{limit_seconds:.3f}"
    cmd = [solver] if core is None else ["taskset", "-c", str(core), solver]
    t0 = time.time()
    with open(instance_path) as fin, open(out_path, "w") as fout:
        p = subprocess.Popen(
            cmd, stdin=fin, stdout=fout, env=env,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        try:
            p.wait(timeout=limit_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            return time.time() - t0, "time limit exhausted during this instance"
    seconds = time.time() - t0
    if p.returncode != 0:
        return seconds, f"solver exited with code {p.returncode}"
    return seconds, None


def evaluate(solver, instances_dir, reference, work_dir, limit_seconds,
             jobs):
    """Run + check every instance in the reference, in parallel: each
    instance gets its own wall-clock limit and its own core."""
    ncores = _cpu_quota()
    jobs = max(1, min(jobs, ncores))

    def one(name, core):
        inst_path = os.path.join(instances_dir, name)
        out_path = os.path.join(work_dir, name + ".out")
        B, K = reference[name]["B"], reference[name]["K"]
        rec = {"B": B, "K": K, "A": None, "raw": None, "score": 0.0,
               "status": "ok", "seconds": 0.0}
        if not os.path.exists(inst_path):
            rec["status"] = "instance file missing on judge side"
            return name, rec
        seconds, err = run_solver(solver, inst_path, out_path,
                                  limit_seconds, core)
        rec["seconds"] = round(seconds, 2)
        if err is None:
            cost, cerr = check_roster(inst_path, out_path)
            if cerr is None:
                rec["A"] = cost
            else:
                rec["status"] = f"invalid solution ({cerr})"
        else:
            rec["status"] = err
        if rec["A"] is not None and B > K:
            rec["raw"] = (B - rec["A"]) / (B - K)
            rec["score"] = min(1.0, max(0.0, rec["raw"]))
        return name, rec

    results = {}
    spent = 0.0
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futures = [ex.submit(one, name, i % jobs)
                   for i, name in enumerate(sorted(reference))]
        for fut in futures:
            name, rec = fut.result()
            spent += rec["seconds"]
            results[name] = rec
    return results, spent


def summarize(results, reference, limit_seconds, spent, jobs):
    """Mean of the legacy clipped local `score` over participating (B > K)
    instances — not the judged score (the judged score is the unclipped
    gap-ratio mean computed by the metric engine; see module docstring)."""
    part = [n for n in results if reference[n]["B"] > reference[n]["K"]]
    total = sum(results[n]["score"] for n in part) / len(part) if part else 0.0
    raws = [results[n]["raw"] for n in part if results[n]["raw"] is not None]
    return {
        "reward": total,
        "participating": len(part),
        "excluded_B_equals_K": sorted(n for n in results if n not in part),
        "mean_raw_unclipped": (sum(raws) / len(raws)) if raws else None,
        "per_instance_seconds": limit_seconds,
        "judge_jobs": jobs,
        "beat_known_best": sorted(
            n for n in part
            if results[n]["A"] is not None and results[n]["A"] < reference[n]["K"]
        ),
    }


def load_reference(path):
    with open(path) as f:
        data = json.load(f)
    return data["instances"]


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON",
              file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1], argv[2], argv[3]
    reference = load_reference(ref_path)
    work_dir = os.path.join("/tmp", f"nurse-score-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)
    limit_seconds = float(os.environ.get("PER_INSTANCE_SECONDS",
                                         str(PER_INSTANCE_SECONDS)))

    solver, err = build_solver(app_dir)
    if err:
        return {"reward": 0.0, "build_error": err, "per_instance": {}}
    results, spent = evaluate(solver, instances_dir, reference, work_dir,
                              limit_seconds, JUDGE_JOBS)
    out = summarize(results, reference, limit_seconds, spent,
                    max(1, min(JUDGE_JOBS, _cpu_quota())))
    out["per_instance"] = results
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv), indent=1, sort_keys=True))
