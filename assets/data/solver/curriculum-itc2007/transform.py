"""Frozen input-only transformation extracted from the original task implementation."""
import argparse
import hashlib
import json
import os
import random
import sys
TRANSFORM_ID = 'ctt-relabeling-form2-v1'
SEED_PREFIX = 'tcshard-form2-curriculum-260920:'
SEED_RULE = 'seed = int.from_bytes(sha256("tcshard-form2-curriculum-260920:" + stem).digest()[:8], "big"); rng = random.Random(seed); consumption order: sorted-label shuffles of courses, rooms, teachers, curricula (labels permuted within class); transformed file name hNN assigned in sorted official-name order'
NEUTRAL_NAME = 'instance'
HEADER_KEYS = ('Name', 'Courses', 'Rooms', 'Days', 'Periods_per_day', 'Curricula', 'Constraints')
TESTS = os.path.dirname(os.path.abspath(__file__))

def derive_seed(stem):
    h = hashlib.sha256((SEED_PREFIX + stem).encode()).digest()
    return int.from_bytes(h[:8], 'big')

def load_ctt(path):
    """Parse a .ctt instance. Returns a dict with header + sections."""
    inst = {'header': {}, 'courses': [], 'rooms': [], 'curricula': [], 'unavail': []}
    section = None
    with open(path, errors='replace') as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line == 'COURSES:':
                section = 'courses'
                continue
            if line == 'ROOMS:':
                section = 'rooms'
                continue
            if line == 'CURRICULA:':
                section = 'curricula'
                continue
            if line == 'UNAVAILABILITY_CONSTRAINTS:':
                section = 'unavail'
                continue
            if line == 'END.':
                break
            if section is None:
                (k, _, v) = line.partition(':')
                if k.strip() in HEADER_KEYS:
                    inst['header'][k.strip()] = v.strip()
                continue
            parts = line.split()
            if section == 'courses':
                if len(parts) != 5:
                    raise ValueError(f'{path}: bad COURSES line: {line!r}')
                inst['courses'].append(parts)
            elif section == 'rooms':
                if len(parts) != 2:
                    raise ValueError(f'{path}: bad ROOMS line: {line!r}')
                inst['rooms'].append(parts)
            elif section == 'curricula':
                if len(parts) < 2 or int(parts[1]) != len(parts) - 2:
                    raise ValueError(f'{path}: bad CURRICULA line: {line!r}')
                inst['curricula'].append(parts)
            else:
                if len(parts) != 3:
                    raise ValueError(f'{path}: bad UNAVAILABILITY line: {line!r}')
                inst['unavail'].append(parts)
    h = inst['header']
    for (k, sec) in {'Courses': 'courses', 'Rooms': 'rooms', 'Curricula': 'curricula', 'Constraints': 'unavail'}.items():
        if k in h and int(h[k]) != len(inst[sec]):
            raise ValueError(f'{path}: header {k}={h[k]} but {len(inst[sec])} lines')
    return inst

def emit(inst):
    """规范化布局重发：各区行已排序；各区之间一个空行，END. 前空行
    （官方 CPSolver 解析器按空行断区，空行是承载语义的，不可丢）。"""
    h = inst['header']
    out = []
    for k in HEADER_KEYS:
        out.append(f'{k}: {h[k]}')
    out.append('')
    out.append('COURSES:')
    out += [' '.join(c) for c in inst['courses']]
    out.append('')
    out.append('ROOMS:')
    out += [' '.join(r) for r in inst['rooms']]
    out.append('')
    out.append('CURRICULA:')
    out += [' '.join(q) for q in inst['curricula']]
    out.append('')
    out.append('UNAVAILABILITY_CONSTRAINTS:')
    out += [' '.join(u) for u in inst['unavail']]
    out.append('')
    out.append('END.')
    return ('\n'.join(out) + '\n').encode()

def _perm_map(labels, rng):
    """Return {old_label: new_label} permuting the label multiset."""
    labs = sorted(labels)
    shuffled = labs[:]
    rng.shuffle(shuffled)
    return dict(zip(labs, shuffled))

def transform_instance(stem, inst):
    """Return (new_inst, maps)。maps = course/room/teacher/curriculum 四张
    旧->新标识符映射。天/时段不动。"""
    seed = derive_seed(stem)
    rng = random.Random(seed)
    cmap = _perm_map([c[0] for c in inst['courses']], rng)
    rmap = _perm_map([r[0] for r in inst['rooms']], rng)
    tmap = _perm_map(sorted({c[1] for c in inst['courses']}), rng)
    qmap = _perm_map([q[0] for q in inst['curricula']], rng)
    new = {'header': dict(inst['header']), 'courses': [], 'rooms': [], 'curricula': [], 'unavail': []}
    new['header']['Name'] = NEUTRAL_NAME
    new['courses'] = sorted(([cmap[c[0]], tmap[c[1]], c[2], c[3], c[4]] for c in inst['courses']))
    new['rooms'] = sorted(([rmap[r[0]], r[1]] for r in inst['rooms']))
    new['curricula'] = sorted(([qmap[q[0]], q[1]] + sorted((cmap[c] for c in q[2:])) for q in inst['curricula']))
    new['unavail'] = sorted(([cmap[u[0]], u[1], u[2]] for u in inst['unavail']), key=lambda u: (u[0], int(u[1]), int(u[2])))
    maps = {'course_map': cmap, 'room_map': rmap, 'teacher_map': tmap, 'curriculum_map': qmap}
    return (new, maps)
