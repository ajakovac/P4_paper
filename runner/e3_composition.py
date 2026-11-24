from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path

DIAGNOSTICS = {
    'OK00': 'SUPPORTED',
    'OKNS': 'NO LOCAL KS SOLUTION',
    'E09': 'BAD COMPOSITION',
    'E14': 'HIDDEN KS USE',
    'E21': 'BAD DERIVATION',
    'T01': 'MISSED SOLUTION',
    'T02': 'WRONG BINDING',
    'T03': 'MISSING PROCEDURE PROPOSAL',
    'X01': 'PROPOSER EXECUTION ERROR',
}

FAMILY_BY_FORM = {
    'L2_TO_L': ('e3_later_successor_letter', 'H_L'),
    'LN_TO_N': ('e3_letter_weight', 'H_W'),
    'LLN_TO_LN': ('e3_common_argument_composition', 'H_C'),
    'LNLN_TO_LN': ('e3_independent_argument_composition', 'H_I'),
}

REQUIRED_PARENTS = {
    'e3_later_successor_letter': ['Rseq'],
    'e3_letter_weight': ['Rord', 'MUL_NAT'],
    'e3_common_argument_composition': ['H_L', 'H_W', 'ADD_NAT'],
    'e3_independent_argument_composition': ['H_L', 'H_W', 'ADD_NAT'],
}

CANONICAL_DELTA = {
    'H_L': (
        'PROCEDURE H_L\n'
        'QUALIFY H_L kind procedure\n'
        'QUALIFY H_L status supported\n'
        'QUALIFY H_L proposal_source true\n'
        'QUALIFY H_L procedure_family e3_later_successor_letter\n'
        'QUALIFY H_L input_signature (tau_L,tau_L)\n'
        'QUALIFY H_L output_type tau_L\n'
        'QUALIFY H_L uses_relation Rseq\n'
    ),
    'H_W': (
        'PROCEDURE H_W\n'
        'QUALIFY H_W kind procedure\n'
        'QUALIFY H_W status supported\n'
        'QUALIFY H_W proposal_source true\n'
        'QUALIFY H_W procedure_family e3_letter_weight\n'
        'QUALIFY H_W input_signature (tau_L,tau_N)\n'
        'QUALIFY H_W output_type tau_N\n'
        'QUALIFY H_W uses_relation Rord\n'
        'QUALIFY H_W uses_procedure MUL_NAT\n'
    ),
    'H_C': (
        'PROCEDURE H_C\n'
        'QUALIFY H_C kind procedure\n'
        'QUALIFY H_C status supported\n'
        'QUALIFY H_C proposal_source true\n'
        'QUALIFY H_C procedure_family e3_common_argument_composition\n'
        'QUALIFY H_C input_signature (tau_L,tau_L,tau_N)\n'
        'QUALIFY H_C output_type tau_LN\n'
        'QUALIFY H_C uses_procedure H_L\n'
        'QUALIFY H_C uses_procedure H_W\n'
        'QUALIFY H_C uses_procedure ADD_NAT\n'
    ),
    'H_I': (
        'PROCEDURE H_I\n'
        'QUALIFY H_I kind procedure\n'
        'QUALIFY H_I status supported\n'
        'QUALIFY H_I proposal_source true\n'
        'QUALIFY H_I procedure_family e3_independent_argument_composition\n'
        'QUALIFY H_I input_signature (tau_L,tau_N,tau_L,tau_N)\n'
        'QUALIFY H_I output_type tau_LN\n'
        'QUALIFY H_I uses_procedure H_L\n'
        'QUALIFY H_I uses_procedure H_W\n'
        'QUALIFY H_I uses_procedure ADD_NAT\n'
    ),
}


def parse_ks(path: Path):
    lines = [x.strip() for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
    edges = []
    procedures = {}
    primitives = set()
    nat_range = None
    current_proc = None
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == 'EDGE' and len(parts) >= 5:
            edges.append((parts[1], parts[2], parts[3], parts[4]))
        elif parts[0] == 'PRIMITIVE' and len(parts) >= 2:
            primitives.add(parts[1])
        elif parts[0] == 'NAT_RANGE' and len(parts) >= 3:
            nat_range = (int(parts[1]), int(parts[2]))
        elif parts[0] == 'PROCEDURE' and len(parts) >= 2:
            current_proc = parts[1]
            procedures.setdefault(current_proc, {})
        elif parts[0] == 'QUALIFY' and len(parts) >= 4 and parts[1] in procedures:
            key = parts[2]
            value = ' '.join(parts[3:])
            if key in procedures[parts[1]]:
                old = procedures[parts[1]][key]
                if isinstance(old, list):
                    old.append(value)
                else:
                    procedures[parts[1]][key] = [old, value]
            else:
                procedures[parts[1]][key] = value
    return {'edges': edges, 'procedures': procedures, 'primitives': primitives, 'nat_range': nat_range}


def parse_task(path: Path):
    lines = [x.strip() for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
    task_id = None
    form = None
    examples = []
    query = None
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == 'ENTITY' and len(parts) >= 2 and task_id is None:
            task_id = parts[1]
        elif parts[0] == 'QUALIFY' and len(parts) >= 4 and parts[2] == 'e3_form':
            form = parts[3]
        elif parts[0].startswith('E3_EXAMPLE_'):
            examples.append(parts)
        elif parts[0].startswith('E3_QUERY_'):
            query = parts
    return {'task_id': task_id, 'form': form, 'examples': examples, 'query': query}


def _graph_from_ks(ks, relation):
    return {a: b for a, r, b, _ in ks['edges'] if r == relation}


def _ordinal_from_ks(ks):
    out = {}
    for a, r, b, _ in ks['edges']:
        if r == 'Rord':
            try:
                out[a] = int(b)
            except ValueError:
                pass
    return out


def _later(seq, a, b):
    if a == b:
        return a
    x = a
    seen = set()
    while x in seq and x not in seen:
        seen.add(x)
        x = seq[x]
        if x == b:
            return b
    x = b
    seen = set()
    while x in seq and x not in seen:
        seen.add(x)
        x = seq[x]
        if x == a:
            return a
    raise ValueError(f'{a},{b} are not ordered by represented Rseq')


def _hl(ks, a, b):
    seq = _graph_from_ks(ks, 'Rseq')
    later = _later(seq, a, b)
    if later not in seq:
        raise ValueError(f'no represented successor of {later}')
    return seq[later]


def _hw(ks, letter, n):
    ords = _ordinal_from_ks(ks)
    if letter not in ords:
        raise ValueError(f'no represented Rord value for {letter}')
    if 'MUL_NAT' not in ks['primitives']:
        raise ValueError('MUL_NAT not represented')
    value = ords[letter] * int(n)
    lo, hi = ks['nat_range'] or (0, -1)
    if not lo <= value <= hi:
        raise ValueError(f'numeric result {value} outside represented NAT_RANGE')
    return value


def _hc(ks, a, b, n):
    if 'ADD_NAT' not in ks['primitives']:
        raise ValueError('ADD_NAT not represented')
    return _hl(ks, a, b), _hw(ks, a, n) + _hw(ks, b, n)


def _hi(ks, a, n1, b, n2):
    if 'ADD_NAT' not in ks['primitives']:
        raise ValueError('ADD_NAT not represented')
    return _hl(ks, a, b), _hw(ks, a, n1) + _hw(ks, b, n2)


def _token(letter, number):
    return f'{letter}{number}'


def _expected_from_task(task, ks):
    form = task['form']
    q = task['query']
    if not q:
        raise ValueError('missing E3 query')
    if form == 'L2_TO_L':
        # E3_QUERY_L2_TO_L T X L1 L2
        unknown, a, b = q[2], q[3], q[4]
        expected = _hl(ks, a, b)
        def eval_example(p):
            return _hl(ks, p[2], p[3]) == p[4]
    elif form == 'LN_TO_N':
        unknown, a, n = q[2], q[3], q[4]
        expected = str(_hw(ks, a, n))
        def eval_example(p):
            return str(_hw(ks, p[2], p[3])) == p[4]
    elif form == 'LLN_TO_LN':
        unknown, a, b, n = q[2], q[3], q[4], q[5]
        l, num = _hc(ks, a, b, n)
        expected = _token(l, num)
        def eval_example(p):
            ll, nn = _hc(ks, p[2], p[3], p[4])
            return ll == p[5] and str(nn) == p[6]
    elif form == 'LNLN_TO_LN':
        unknown, a, n1, b, n2 = q[2], q[3], q[4], q[5], q[6]
        l, num = _hi(ks, a, n1, b, n2)
        expected = _token(l, num)
        def eval_example(p):
            ll, nn = _hi(ks, p[2], p[3], p[4], p[5])
            return ll == p[6] and str(nn) == p[7]
    else:
        raise ValueError(f'unknown E3 form {form}')
    example_results = [eval_example(p) for p in task['examples']]
    return {'unknown': unknown, 'value': expected}, all(example_results), example_results


def _supported_procedure(ks, family):
    found = []
    for name, q in ks['procedures'].items():
        if q.get('kind') == 'procedure' and q.get('status') == 'supported' and q.get('proposal_source') == 'true' and q.get('procedure_family') == family:
            found.append(name)
    return sorted(found)


def _iter_solution_items(data):
    if not isinstance(data, dict):
        return []
    out = []
    for item in data.get('selected') or []:
        out.append(('selected', item))
    c = data.get('construction_phase') or {}
    dep = c.get('dependent_solution') or {}
    if dep.get('present'):
        out.append(('construction', {
            'hypothesis': '<construction>',
            'binding': {'unknown': dep.get('unknown'), 'value': dep.get('value')},
            'support_facts': c.get('support_facts') or [],
            'checks': [],
        }))
    return out


def _all_pass(item):
    checks = item.get('checks') or []
    required = {'proposal_complete', 'type_compatible', 'satisfies_givens', 'satisfies_constraints', 'derivation_supported'}
    got = {c.get('check'): c.get('result') for c in checks}
    return bool(checks) and all(got.get(k) == 'pass' for k in required)


def _kbp_supports(data, family, parents):
    bundle = (data or {}).get('knowledge_proposal_bundle') or {}
    for item in bundle.get('items') or []:
        if item.get('kind') != 'procedure':
            continue
        blob = ' '.join(str(x) for x in (item.get('facts') or []))
        if family in blob and all(p in blob for p in parents):
            return True
    return False


def evaluate_e3(task_path: Path, ks_path: Path, episode_id: str, construction_allowed: bool, data):
    task = parse_task(task_path)
    ks = parse_ks(ks_path)
    expected, examples_ok, example_results = _expected_from_task(task, ks)
    family, canonical_id = FAMILY_BY_FORM[task['form']]
    available = _supported_procedure(ks, family)
    solutions = _iter_solution_items(data)
    proposer_binding = None
    if solutions:
        proposer_binding = (solutions[0][1].get('binding') or {})

    result = {
        'experiment': 'E3',
        'episode_id': episode_id,
        'task_id': task['task_id'],
        'task_form': task['form'],
        'expected_binding': expected,
        'examples_supported_by_represented_semantics': examples_ok,
        'example_checks': example_results,
        'required_family': family,
        'visible_matching_procedures': available,
        'construction_allowed': construction_allowed,
        'proposer_binding': proposer_binding,
        'ms_decision': None,
        'primary_diagnostic': None,
        'used_support': [],
        'persistent_update': {'decision': 'NO_UPDATE', 'admitted_id': None},
        'e3_test_status': None,
    }

    if not examples_ok:
        result['ms_decision'] = 'REJECT'
        result['primary_diagnostic'] = {'code': 'E21', 'short': DIAGNOSTICS['E21']}
        result['decision_reason'] = 'represented E3 examples are inconsistent with the active E3 procedure semantics'
        result['e3_test_status'] = 'FAIL'
        return result

    # Existing-KS route.
    if available:
        matching = []
        for source, item in solutions:
            if source != 'selected':
                continue
            if (item.get('binding') or {}) != expected:
                continue
            hyp = str(item.get('hypothesis') or '')
            if hyp == f'E3_REUSE({task["task_id"]},{available[0]})' and _all_pass(item):
                matching.append(item)
        if matching:
            result['ms_decision'] = 'ACCEPT'
            result['primary_diagnostic'] = {'code': 'OK00', 'short': DIAGNOSTICS['OK00']}
            result['decision_reason'] = 'binding is replayable through the visible supported E3 procedure'
            result['used_support'] = [available[0]]
            result['e3_test_status'] = 'PASS'
            return result
        if not solutions:
            result['ms_decision'] = 'NO_SOLUTION'
            result['primary_diagnostic'] = {'code': 'T01', 'short': DIAGNOSTICS['T01']}
            result['decision_reason'] = 'a visible admissible E3 procedure exists but no solution was proposed'
            result['e3_test_status'] = 'FAIL'
            return result
        result['ms_decision'] = 'REJECT'
        code = 'T02' if proposer_binding and proposer_binding != expected else 'E21'
        result['primary_diagnostic'] = {'code': code, 'short': DIAGNOSTICS[code]}
        result['decision_reason'] = 'proposed solution is not an admissible reuse of the visible E3 procedure'
        result['e3_test_status'] = 'FAIL'
        return result

    # No matching procedure is visible.
    if not construction_allowed:
        # Correct E3 pre-control: either no proposal, or an externally plausible proposal is contained.
        if solutions:
            result['ms_decision'] = 'REJECT'
            result['primary_diagnostic'] = {'code': 'E14', 'short': DIAGNOSTICS['E14']}
            result['decision_reason'] = 'solution requires a reusable procedure absent from the visible KS and construction is disabled'
        else:
            result['ms_decision'] = 'NO_SOLUTION'
            result['primary_diagnostic'] = {'code': 'OKNS', 'short': DIAGNOSTICS['OKNS']}
            result['decision_reason'] = 'local KS-based solution not found; required reusable procedure is absent and construction is disabled'
        result['e3_test_status'] = 'PASS'
        return result

    # Construction-enabled route.
    c = (data or {}).get('construction_phase') or {}
    dep = c.get('dependent_solution') or {}
    correct_dep = dep.get('present') and {'unknown': dep.get('unknown'), 'value': dep.get('value')} == expected
    parents = REQUIRED_PARENTS[family]
    kpb_ok = _kbp_supports(data, family, parents)
    local_selected = bool((data or {}).get('selected'))
    if c.get('status') == 'construction_proposed' and correct_dep and kpb_ok and not local_selected:
        result['ms_decision'] = 'ACCEPT'
        result['primary_diagnostic'] = {'code': 'OK00', 'short': DIAGNOSTICS['OK00']}
        result['decision_reason'] = 'bounded E3 construction is replayable and the dependent solution is supported'
        result['used_support'] = parents + [f'constructed {canonical_id}']
        result['persistent_update'] = {'decision': 'ADMIT', 'admitted_id': canonical_id}
        result['e3_test_status'] = 'PASS'
        return result

    if not solutions:
        result['ms_decision'] = 'NO_SOLUTION'
        result['primary_diagnostic'] = {'code': 'T01', 'short': DIAGNOSTICS['T01']}
        result['decision_reason'] = 'construction was available but no supported dependent solution was proposed'
    elif proposer_binding and proposer_binding != expected:
        result['ms_decision'] = 'REJECT'
        result['primary_diagnostic'] = {'code': 'T02', 'short': DIAGNOSTICS['T02']}
        result['decision_reason'] = f'proposed binding differs from represented result {expected}'
    elif not kpb_ok:
        result['ms_decision'] = 'REJECT'
        result['primary_diagnostic'] = {'code': 'T03', 'short': DIAGNOSTICS['T03']}
        result['decision_reason'] = 'solution proposal lacks the required reusable-procedure description and represented parents'
    else:
        result['ms_decision'] = 'REJECT'
        result['primary_diagnostic'] = {'code': 'E09', 'short': DIAGNOSTICS['E09']}
        result['decision_reason'] = 'proposed construction is not admissible under the active E3 composition profile'
    result['e3_test_status'] = 'FAIL'
    return result


def _prop_text(evaluation):
    b = evaluation.get('proposer_binding') or {}
    if b.get('unknown') or b.get('value'):
        return f"{b.get('unknown','?')}={b.get('value','?')}"
    return None


def reader_line(evaluation):
    task = evaluation['episode_id']
    decision = evaluation['ms_decision']
    support = evaluation.get('used_support') or []
    if decision == 'NOT_EVALUATED':
        return f'{task}: EXECUTION ERROR - proposer response not obtained.'
    if decision == 'ACCEPT':
        used = ', '.join(support) if support else 'admissible KS support'
        return f'{task}: SOLUTION FOUND - used {used}.'
    if decision == 'REJECT' and _prop_text(evaluation):
        return f'{task}: SOLUTION FOUND BUT REJECTED - no admissible KS-based derivation.'
    return f'{task}: NO SOLUTION FOUND - local KS-based solution not found.'


def screen_lines(evaluation):
    p = evaluation['primary_diagnostic']
    line = reader_line(evaluation)
    return [
        '',
        '*' * 68,
        line,
        f"CONTROL: {evaluation['e3_test_status']} [{p['code']} {p['short']}]",
        'READER FILE: READER_DIAGNOSIS.txt',
        '*' * 68,
    ]


NEXT_KS_BY_ADMITTED = {
    'H_L': 'E3_KS1.dspl',
    'H_W': 'E3_KS2.dspl',
    'H_C': 'E3_KS3.dspl',
    'H_I': 'E3_KS4.dspl',
}


def _sha256_path(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_e3_artifacts(run_dir: Path, task_path: Path, ks_path: Path, evaluation, write_json_fn, write_text_fn):
    write_json_fn(run_dir / 'E3_EVALUATION.json', evaluation)
    write_text_fn(run_dir / 'READER_DIAGNOSIS.txt', reader_line(evaluation) + '\n')
    write_text_fn(
        run_dir / 'E3_RESULT.txt',
        f"episode={evaluation['episode_id']}\n"
        f"task={evaluation['task_id']}\n"
        f"ms_decision={evaluation['ms_decision']}\n"
        f"primary={evaluation['primary_diagnostic']['code']} {evaluation['primary_diagnostic']['short']}\n"
        f"e3_test={evaluation['e3_test_status']}\n"
        f"ks_update={evaluation['persistent_update']['decision']}\n"
    )
    update = evaluation['persistent_update']
    delta_path = run_dir / 'KS_DELTA.dspl'
    before_hash = _sha256_path(ks_path)
    if update['decision'] == 'ADMIT' and update['admitted_id']:
        hid = update['admitted_id']
        write_text_fn(delta_path, CANONICAL_DELTA[hid])
        next_path = ks_path.parent / NEXT_KS_BY_ADMITTED[hid]
        write_json_fn(run_dir / 'KSU_RESULT_MIN.json', {
            'task_id': evaluation['task_id'],
            'status': 'ADMITTED',
            'decision': 'UPDATE',
            'admitted_items': [hid],
            'reason': 'E3_SUPPORTED_CONSTRUCTION',
            'ks_before_sha256': before_hash,
            'ks_delta_sha256': _sha256_path(delta_path),
            'ks_after_sha256': _sha256_path(next_path) if next_path.exists() else None,
            'canonical_next_snapshot': next_path.name,
        })
    else:
        write_text_fn(delta_path, 'EMPTY\n')
        write_json_fn(run_dir / 'KSU_RESULT_MIN.json', {
            'task_id': evaluation['task_id'],
            'status': 'NO_UPDATE',
            'decision': 'NO_UPDATE',
            'admitted_items': [],
            'reason': 'NO_ADMISSIBLE_E3_PERSISTENT_PROPOSAL',
            'ks_before_sha256': before_hash,
            'ks_delta_sha256': _sha256_path(delta_path),
            'ks_after_sha256': before_hash,
            'canonical_next_snapshot': ks_path.name,
        })
    (run_dir / 'CURRENT_TASK.dspl').write_bytes(task_path.read_bytes())
    (run_dir / 'VISIBLE_KS.dspl').write_bytes(ks_path.read_bytes())


def verify_checkpoint_chain(root: Path):
    problems = []
    chain = [
        ('E3_KS0.dspl', 'E3_KS1.dspl', 'H_L'),
        ('E3_KS1.dspl', 'E3_KS2.dspl', 'H_W'),
        ('E3_KS2.dspl', 'E3_KS3.dspl', 'H_C'),
        ('E3_KS3.dspl', 'E3_KS4.dspl', 'H_I'),
    ]
    for before_name, after_name, hid in chain:
        before = root / 'inputs' / 'ks' / before_name
        after = root / 'inputs' / 'ks' / after_name
        if not before.exists() or not after.exists():
            problems.append(f'E3 checkpoint missing: {before_name} or {after_name}')
            continue
        before_lines = [x.strip() for x in before.read_text(encoding='utf-8').splitlines() if x.strip()]
        delta_lines = [x.strip() for x in CANONICAL_DELTA[hid].splitlines() if x.strip()]
        after_lines = [x.strip() for x in after.read_text(encoding='utf-8').splitlines() if x.strip()]
        if after_lines != before_lines + delta_lines:
            problems.append(f'E3 checkpoint chain mismatch: {before_name} + {hid} delta != {after_name}')
    return problems


def build_minimal_check_bundle(run_dir: Path):
    names = [
        'PRE_ENVELOPE.json', 'CURRENT_TASK.dspl', 'VISIBLE_KS.dspl',
        'FINAL_MESSAGE.txt', 'TRANSITION_OUTPUT.json', 'MINIMAL_RESULT.txt',
        'MINIMAL_TRACE.txt', 'E3_EVALUATION.json', 'E3_RESULT.txt',
        'READER_DIAGNOSIS.txt', 'KSU_RESULT_MIN.json', 'KS_DELTA.dspl',
        'POST_ENVELOPE.json', 'codex_version.txt', 'stderr.txt', 'stdout.txt',
    ]
    z = run_dir / 'E3_CHECK_BUNDLE_MINIMAL.zip'
    if z.exists():
        z.unlink()
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            p = run_dir / name
            if p.exists():
                zf.write(p, name)
    return z
