"""Assess SSH algorithms on the controller: JSON stdin in, JSON stdout out.

Credentials and device login remain in ssh_connectivity.yml.
"""

import json, re, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

def names(entries):
    values = [entry['algorithm'] if isinstance(entry, dict) else entry for entry in entries]
    if not all(isinstance(v, str) for v in values):
        raise ValueError('Invalid algorithm list')
    return values

def classify(offered, rules):
    levels = {}
    for family in ('kex', 'key', 'enc', 'mac'):
        levels[family] = next((level for level in ('modern', 'legacy', 'very_old')
            if set(offered[family]) & set(rules[level][family])), 'unknown')
    if any('-gcm@' in c or c == 'chacha20-poly1305@openssh.com' for c in offered['enc']):
        levels['mac'] = 'modern'
    overall = next((level for level in ('unknown', 'very_old', 'legacy') if level in levels.values()), 'modern')
    return {'classification': overall, 'family_classes': levels, 'offered_algorithms': offered}

def preferred_options(offered, rules):
    options = {}
    for family, option in [('kex','KexAlgorithms'),('key','HostKeyAlgorithms'),('enc','Ciphers'),('mac','MACs')]:
        ranked = sum((rules[level][family] for level in ('modern','legacy','very_old')), []) + offered[family]
        values = list(dict.fromkeys(v for v in ranked if v in offered[family]
            and re.fullmatch(r'[A-Za-z0-9@._+-]+', v)))
        if values:
            options[option] = ','.join(values)
    return options

def run(payload):
    row = payload['device']
    record = {'inventory_hostname': row['hostname'], 'management_ip': row['management_ip'],
        'site': (row.get('site') or '').strip() or 'other',
        'store_type': (row.get('store_type') or '').strip() or 'other',
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'status': 'failure', 'reason': '', 'login_attempted': False, 'ssh_options': {},
        'ssh_assessment': {'classification': 'unknown', 'error': None}, 'assessment_source': 'fresh scan'}
    offered = None
    try:
        def folder(value):
            return quote(value, safe='').replace('.', '%2E')
        saved = Path(payload['assessment_root']) / folder(record['store_type']) / record['site'] / (row['hostname'] + '.json')
        if payload['reuse_assessment'] and saved.is_file():
            previous = json.loads(saved.read_text())
            if previous.get('management_ip') != row['management_ip']:
                raise ValueError('Saved assessment address differs from input')
            raw = previous['ssh_assessment']['offered_algorithms']
            record['assessment_source'] = 'saved: ' + str(previous.get('collected_at', 'unknown date'))
        else:
            scan = subprocess.run(['ssh-audit', '--json', '--skip-rate-test', '--timeout=10',
                row['management_ip']], capture_output=True, text=True, timeout=payload['scan_timeout'])
            raw = json.loads(scan.stdout)
        offered = {family: names(raw[family]) for family in ('kex','key','enc','mac')}
        record['ssh_assessment'] = classify(offered, payload['rules'])
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        record['ssh_assessment']['error'] = 'Assessment unavailable: ' + type(error).__name__
        record['assessment_source'] += '; trying client defaults'
        offered = None
    if record['assessment_source'].startswith('fresh scan'):
        time.sleep(payload['scan_delay'])
    if offered is not None:
        record['ssh_options'] = preferred_options(offered, payload['rules'])
    return record

if __name__ == '__main__':
    print(json.dumps(run(json.load(sys.stdin))))
