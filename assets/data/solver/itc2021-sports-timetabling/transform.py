"""Frozen input-only transformation extracted from the original task implementation."""
import argparse
import hashlib
import json
import os
import random
import re
import sys
TRANSFORM_ID = 'itc2021-team-relabel-form2-v1'
SEED_PREFIX = 'tcshard-form2-itc2021-260920:'
SEED_RULE = 'seed = int.from_bytes(sha256("tcshard-form2-itc2021-260920:" + stem).digest()[:8], "big"); rng = random.Random(seed); one shuffle of the team-id list 0..n-1; transformed file name hNN assigned in sorted official-name order'
TEAM_RE = re.compile('<team\\b[^>]*/>')
TEAMREF_RE = re.compile('\\b(teams|teams1|teams2)="([^"]*)"')
MEETINGS_RE = re.compile('\\bmeetings="([^"]*)"')
INAME_RE = re.compile('<InstanceName>[^<]*</InstanceName>')
ATTR_RE = re.compile('(\\w+)="([^"]*)"')
HOME_RE = re.compile('\\bhome="(\\d+)"')
AWAY_RE = re.compile('\\baway="(\\d+)"')
TEAMID_RE = re.compile('<team\\b[^>]*\\bid="(\\d+)"')
TESTS = os.path.dirname(os.path.abspath(__file__))

def remap_idlist(value, pi):
    if not value:
        return value
    return ';'.join((str(pi[int(t)]) for t in value.split(';') if t != '')) + (';' if value.endswith(';') else '')

def remap_meetings(value, pi):
    out = []
    for pair in value.split(';'):
        if not pair:
            continue
        (a, b) = pair.split(',')
        out.append(f'{pi[int(a)]},{pi[int(b)]};')
    return ''.join(out)

def transform_text(text, pi, neutral_name):

    def fix_team(m):
        attrs = dict(ATTR_RE.findall(m.group(0)))
        old = int(attrs['id'])
        attrs['id'] = str(pi[old])
        if 'name' in attrs:
            attrs['name'] = f'Team {pi[old]}'
        return '<team ' + ' '.join((f'{k}="{v}"' for (k, v) in attrs.items())) + '/>'
    out = TEAM_RE.sub(fix_team, text)
    out = TEAMREF_RE.sub(lambda m: f'{m.group(1)}="{remap_idlist(m.group(2), pi)}"', out)
    out = MEETINGS_RE.sub(lambda m: f'meetings="{remap_meetings(m.group(1), pi)}"', out)
    out = INAME_RE.sub(f'<InstanceName>{neutral_name}</InstanceName>', out, count=1)
    return out
