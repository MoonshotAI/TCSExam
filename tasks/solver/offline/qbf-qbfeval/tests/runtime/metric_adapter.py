# SPDX-License-Identifier: Apache-2.0
"""Match the existing judge's status normalization and anchor filtering."""
import math


def numeric(value):
    return isinstance(value, (int,float)) and not isinstance(value,bool) and math.isfinite(value)


def prepare(records, anchors, config):
    adapted={'B':{},'K':{}}
    issues=[]
    for key in sorted(set(anchors['B']) | set(anchors['K'])):
        b,k=anchors['B'].get(key),anchors['K'].get(key)
        reason=None
        if not numeric(b) or not numeric(k):
            reason='anchor_not_numeric'
        elif config['shape']=='solve_rate' and bool(k)<bool(b):
            reason='anchor_inverted'
        elif config['shape']=='gap_ratio' and ((config['direction']=='max' and k<b) or
                                               (config['direction']=='min' and k>b)):
            reason='anchor_direction_mismatch'
        if reason:
            issues.append(dict(instance=key,reason=reason,B=b,K=k))
        else:
            adapted['B'][key],adapted['K'][key]=b,k
    clean=[]
    for key,rec in sorted(records.items()):
        if key not in adapted['B']:
            continue
        a=rec.get('A')
        status='ok' if str(rec.get('status','')).startswith('ok') else 'invalid'
        if status=='ok' and not numeric(a):
            status='error'
        clean.append(dict(instance=key,A=a if status=='ok' else None,status=status,
                          detail=str(rec.get('status',''))))
    return clean,adapted,issues
