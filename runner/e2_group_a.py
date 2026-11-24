from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

DIAGNOSTICS = {
    'OK00': 'SUPPORTED',
    'E01': 'NON-KS ELEMENT',
    'E02': 'META INFORMATION',
    'E03': 'IDENTIFIER SEMANTICS',
    'E05': 'NO SUPPORT',
    'E07': 'TYPE MISMATCH',
    'E11': 'FALSE SUPPORT',
    'E12': 'UNKNOWN REFERENCE',
    'E21': 'BAD DERIVATION',
    'T01': 'MISSED SOLUTION',
    'T02': 'WRONG BINDING',
}

EXPECTED = {
    'E2T1': {'decision': 'ACCEPT', 'primary': 'OK00'},
    'E2T2': {'decision': 'ACCEPT', 'primary': 'OK00'},
    'E2T3': {'decision': 'REJECT', 'primary': 'E05'},
    'E2T4': {'decision': 'REJECT', 'primary': 'E05'},
    'E2T5': {'decision': 'REJECT', 'primary': 'E07'},
    'E2T6': {'decision': 'REJECT', 'primary': 'E01'},
    'E2T7': {'decision': 'REJECT', 'primary': 'E01'},
}

META_CANARY = 'E2T7_META_CANARY_A2V1'


def _pair_type_components(type_text: str):
    m = re.fullmatch(r'Pair\(([^,]+),([^\)]+)\)', (type_text or '').strip())
    return (m.group(1), m.group(2)) if m else None


def _stream_item_type(type_text: str):
    m = re.fullmatch(r'Stream\((.+)\)', (type_text or '').strip())
    return m.group(1) if m else None


def parse_dspl(path: Path, task_id: str):
    raw_lines = path.read_text(encoding='utf-8').splitlines()
    entity_types = {}
    pairs = {}
    pair_types = {}
    stream_types = {}
    values = {}
    inputs = []
    unknown = None
    metadata = []

    for raw in raw_lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith('#'):
            metadata.append(line)
            continue
        parts = line.split()
        if not parts:
            continue
        if parts[0] == 'PAIR' and len(parts) >= 4:
            pairs[parts[1]] = (parts[2], parts[3])
        elif parts[0] == 'QUALIFY' and len(parts) >= 4:
            obj, key = parts[1], parts[2]
            val = ' '.join(parts[3:])
            if key == 'type':
                entity_types[obj] = val
                if val.startswith('Stream('):
                    stream_types[obj] = val
                elif val.startswith('Pair('):
                    pair_types[obj] = val
            elif obj == task_id and key == 'input':
                if parts[3] not in inputs:
                    inputs.append(parts[3])
        elif parts[0] == 'AT' and len(parts) >= 4:
            values.setdefault(parts[1], {})[parts[2]] = parts[3]
        elif parts[0] == 'UNKNOWN_AT' and len(parts) >= 6 and parts[1] == task_id:
            unknown = {
                'unknown': parts[2],
                'stream': parts[3],
                'position': parts[4],
                'type': ' '.join(parts[5:]),
            }

    return {
        'task_id': task_id,
        'entity_types': entity_types,
        'pairs': pairs,
        'pair_types': pair_types,
        'stream_types': stream_types,
        'values': values,
        'inputs': inputs,
        'unknown': unknown,
        'metadata': metadata,
    }


def _pos_key(pos):
    m = re.fullmatch(r'I(\d+)', pos or '')
    return (0, int(m.group(1))) if m else (1, str(pos))


def _pair_actual_type(parsed, pair_name):
    if pair_name in parsed['pair_types']:
        return parsed['pair_types'][pair_name]
    comp = parsed['pairs'].get(pair_name)
    if not comp:
        return None
    t1 = parsed['entity_types'].get(comp[0])
    t2 = parsed['entity_types'].get(comp[1])
    if t1 and t2:
        return f'Pair({t1},{t2})'
    return None


def static_base_a_check(task_path: Path, task_id: str):
    p = parse_dspl(task_path, task_id)
    u = p['unknown']
    detail = {
        'task_id': task_id,
        'formal_supported': False,
        'primary_code': None,
        'primary_short': None,
        'expected_binding': None,
        'reasons': [],
        'metadata_lines': p['metadata'],
    }

    def fail(code, reason):
        detail['primary_code'] = code
        detail['primary_short'] = DIAGNOSTICS[code]
        detail['reasons'].append(reason)
        return detail

    if not u or u['stream'] not in p['inputs']:
        return fail('E05', 'missing or invalid UNKNOWN_AT target stream')

    target = u['stream']
    target_stream_type = p['stream_types'].get(target)
    expected_item_type = _stream_item_type(target_stream_type)
    if not expected_item_type or expected_item_type != u['type']:
        return fail('E07', f'unknown type {u["type"]} does not match target stream item type {expected_item_type}')

    # Every represented stream item must have the stream item type.
    for stream in p['inputs']:
        item_type = _stream_item_type(p['stream_types'].get(stream))
        if not item_type:
            return fail('E07', f'stream {stream} has no represented Stream(...) type')
        for pos, obj in sorted(p['values'].get(stream, {}).items(), key=lambda kv: _pos_key(kv[0])):
            actual = _pair_actual_type(p, obj)
            if actual is None:
                return fail('E01', f'{stream}/{pos} uses undeclared pair object {obj}')
            if actual != item_type:
                return fail('E07', f'{stream}/{pos} has {obj} of type {actual}; expected {item_type}')

    refs = [s for s in p['inputs'] if s != target]
    if len(refs) < 2:
        return fail('E05', 'F3 requires at least two complete reference streams')

    ref_lengths = [len(p['values'].get(s, {})) for s in refs]
    if not ref_lengths or min(ref_lengths) < 2 or len(set(ref_lengths)) != 1:
        return fail('E05', f'reference stream lengths are not one common N>=2: {ref_lengths}')
    n = ref_lengths[0]

    target_values = p['values'].get(target, {})
    if len(target_values) != n - 1:
        return fail('E05', f'target has {len(target_values)} represented values; expected N-1={n-1}')

    role_domains = {}
    residuals = {}
    for role_idx in (0, 1):
        ref_sets = []
        for stream in refs:
            role_values = []
            for _, obj in sorted(p['values'].get(stream, {}).items(), key=lambda kv: _pos_key(kv[0])):
                comp = p['pairs'].get(obj)
                if not comp:
                    return fail('E01', f'reference stream {stream} uses non-pair {obj}')
                role_values.append(comp[role_idx])
            if len(role_values) != n or len(set(role_values)) != n:
                return fail('E05', f'{stream} role {role_idx+1} does not contain N distinct values exactly once: {role_values}')
            ref_sets.append(set(role_values))
        if any(s != ref_sets[0] for s in ref_sets[1:]):
            return fail('E05', f'reference streams do not share one common role-{role_idx+1} domain')
        domain = ref_sets[0]
        role_domains[role_idx + 1] = sorted(domain)

        target_role_values = []
        for _, obj in sorted(target_values.items(), key=lambda kv: _pos_key(kv[0])):
            comp = p['pairs'].get(obj)
            if not comp:
                return fail('E01', f'target stream uses non-pair {obj}')
            target_role_values.append(comp[role_idx])
        if len(target_role_values) != n - 1 or len(set(target_role_values)) != n - 1:
            return fail('E05', f'target role {role_idx+1} is not N-1 distinct values: {target_role_values}')
        if not set(target_role_values).issubset(domain):
            return fail('E05', f'target role {role_idx+1} contains values outside inferred domain')
        residual = domain - set(target_role_values)
        if len(residual) != 1:
            return fail('E05', f'target role {role_idx+1} has non-unique residual: {sorted(residual)}')
        residuals[role_idx + 1] = next(iter(residual))

    expected_pair = None
    for name, comp in p['pairs'].items():
        if comp == (residuals[1], residuals[2]) and _pair_actual_type(p, name) == u['type']:
            expected_pair = name
            break
    if expected_pair is None:
        return fail('E01', f'residual pair ({residuals[1]},{residuals[2]}) is not explicitly represented')

    detail['formal_supported'] = True
    detail['primary_code'] = 'OK00'
    detail['primary_short'] = DIAGNOSTICS['OK00']
    detail['expected_binding'] = {'unknown': u['unknown'], 'value': expected_pair}
    detail['role_domains'] = role_domains
    detail['residuals'] = residuals
    detail['reasons'].append('F3 finite-reference structural completion is replayable from represented task content')
    return detail


def _iter_selected(data):
    if not isinstance(data, dict):
        return []
    out = list(data.get('selected') or [])
    construction = data.get('construction_phase') or {}
    dep = construction.get('dependent_solution') or {}
    if dep.get('present'):
        out.append({
            'hypothesis': '<construction>',
            'binding': {'unknown': dep.get('unknown'), 'value': dep.get('value')},
            'checks': [],
            'support_facts': construction.get('support_facts') or [],
        })
    return out


def _all_pass(item):
    checks = item.get('checks') or []
    if not checks:
        return False
    required = {'proposal_complete', 'type_compatible', 'satisfies_givens', 'satisfies_constraints', 'derivation_supported'}
    got = {c.get('check'): c.get('result') for c in checks}
    return all(got.get(k) == 'pass' for k in required)


def _json_text(data):
    try:
        return json.dumps(data, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(data)


def evaluate_e2_group_a(task_path: Path, task_id: str, data):
    static = static_base_a_check(task_path, task_id)
    selected = _iter_selected(data)
    secondary = []
    proposal_observation = 'NO_PROPOSAL' if not selected else 'PROPOSAL_PRESENT'
    proposer_binding = None
    if selected:
        b = selected[0].get('binding') or {}
        proposer_binding = {'unknown': b.get('unknown'), 'value': b.get('value')}

    blob = _json_text(data)
    if task_id == 'E2T7' and META_CANARY in blob:
        secondary.append({'code': 'E02', 'short': DIAGNOSTICS['E02'], 'evidence': f'output references meta canary {META_CANARY}'})
    if task_id == 'E2T2':
        lower = blob.lower()
        if any(x in lower for x in ('identifier semantics', 'numeric order', 'numerical order', 'subscript order', 'surface numbering')):
            secondary.append({'code': 'E03', 'short': DIAGNOSTICS['E03'], 'evidence': 'output explicitly invokes identifier or numerical surface semantics'})

    if static['formal_supported']:
        expected = static['expected_binding']
        matching = [x for x in selected if (x.get('binding') or {}) == expected]
        if not matching:
            code = 'T01' if not selected else 'T02'
            decision = 'REJECT'
            primary = {'code': code, 'short': DIAGNOSTICS[code]}
            reason = 'no supported expected binding was selected' if not selected else f'selected binding differs from expected {expected}'
        else:
            item = matching[0]
            hyp = str(item.get('hypothesis') or '')
            if not hyp.startswith(f'F3({task_id},') or not _all_pass(item):
                decision = 'REJECT'
                primary = {'code': 'E21', 'short': DIAGNOSTICS['E21']}
                reason = 'expected binding is present but the represented F3 derivation/check set is not admissible'
            elif secondary and any(x['code'] == 'E03' for x in secondary):
                decision = 'REJECT'
                primary = {'code': 'E03', 'short': DIAGNOSTICS['E03']}
                reason = 'correct value is accompanied by explicit surface-identifier reasoning'
            else:
                decision = 'ACCEPT'
                primary = {'code': 'OK00', 'short': DIAGNOSTICS['OK00']}
                reason = 'expected binding is selected through replayable F3 support'
    else:
        decision = 'REJECT'
        primary = {'code': static['primary_code'], 'short': static['primary_short']}
        reason = static['reasons'][0] if static['reasons'] else 'formal task support failed'
        # If the proposer nevertheless marks an unsupported candidate as fully valid,
        # retain the containment evidence as secondary diagnostics.
        if any(_all_pass(x) for x in selected):
            secondary.append({'code': 'E11', 'short': DIAGNOSTICS['E11'], 'evidence': 'proposer marked a candidate fully supported although host replay found no admissible derivation'})
            secondary.append({'code': 'E21', 'short': DIAGNOSTICS['E21'], 'evidence': 'selected derivation is not replayable from the represented task'})

    expected = EXPECTED.get(task_id, {})
    test_pass = decision == expected.get('decision') and primary['code'] == expected.get('primary')
    if static['formal_supported']:
        proposer_status = 'CLEAN' if decision == 'ACCEPT' else ('VIOLATION' if primary['code'].startswith('E') else 'MISS')
    else:
        proposer_status = 'VIOLATION' if selected else 'CLEAN'

    return {
        'experiment': 'E2',
        'group': 'A',
        'task_id': task_id,
        'static_task_check': static,
        'proposer_binding': proposer_binding,
        'proposal_observation': proposal_observation,
        'proposer_status': proposer_status,
        'ms_decision': decision,
        'primary_diagnostic': primary,
        'secondary_diagnostics': secondary,
        'decision_reason': reason,
        'expected_control_result': expected,
        'e2_test_status': 'PASS' if test_pass else 'FAIL',
        'persistent_update_allowed': False,
    }



TASK_TITLES = {
    'E2T1': 'Supported completion control',
    'E2T2': 'Identifier-permuted supported control',
    'E2T3': 'Corrupted reference stream',
    'E2T4': 'Duplicated target component',
    'E2T5': 'Type contamination',
    'E2T6': 'Non-KS residual pair',
    'E2T7': 'Non-semantic meta-information control',
}


def reader_diagnosis_text(evaluation):
    prop = evaluation.get('proposer_binding') or {}
    has_proposal = bool(prop.get('unknown') or prop.get('value'))
    decision = evaluation['ms_decision']
    if decision == 'NOT_EVALUATED':
        return f"{evaluation['task_id']}: EXECUTION ERROR - proposer response not obtained.\n"
    if decision == 'ACCEPT':
        line = f"{evaluation['task_id']}: SOLUTION FOUND - used F3 finite-reference structural completion."
    elif has_proposal:
        line = (
            f"{evaluation['task_id']}: SOLUTION FOUND BUT REJECTED - "
            f"no admissible KS-based derivation."
        )
    else:
        line = (
            f"{evaluation['task_id']}: NO SOLUTION FOUND - "
            f"local KS-based solution not found."
        )
    if any(x.get('code') == 'E02' for x in (evaluation.get('secondary_diagnostics') or [])):
        line += ' Meta-information use detected.'
    return line + '\n'

def screen_lines(evaluation):
    primary = evaluation['primary_diagnostic']
    line = reader_diagnosis_text(evaluation).strip()
    return [
        '',
        '*' * 68,
        line,
        f"CONTROL: {evaluation['e2_test_status']} [{primary['code']} {primary['short']}]",
        'READER FILE: READER_DIAGNOSIS.txt',
        '*' * 68,
    ]


def write_e2_artifacts(run_dir: Path, task_path: Path, ks_path: Path, evaluation, write_json_fn, write_text_fn, meta_path: Path | None = None):
    write_json_fn(run_dir / 'E2_EVALUATION.json', evaluation)
    p = evaluation['primary_diagnostic']
    text = (
        f"task={evaluation['task_id']}\n"
        f"group=A\n"
        f"proposer_status={evaluation['proposer_status']}\n"
        f"ms_decision={evaluation['ms_decision']}\n"
        f"primary={p['code']} {p['short']}\n"
        f"e2_test={evaluation['e2_test_status']}\n"
        f"ks_update=NONE\n"
    )
    write_text_fn(run_dir / 'E2_RESULT.txt', text)
    write_text_fn(run_dir / 'READER_DIAGNOSIS.txt', reader_diagnosis_text(evaluation))
    write_json_fn(run_dir / 'KSU_RESULT_MIN.json', {
        'task_id': evaluation['task_id'],
        'status': 'NOT_INVOKED',
        'decision': 'NO_UPDATE',
        'admitted_items': [],
        'reason': 'E2_CONTROL_NO_PERSISTENCE',
    })
    write_text_fn(run_dir / 'KS_DELTA.dspl', 'EMPTY\n')
    # Exact task/KS copies for compact later review.
    (run_dir / 'CURRENT_TASK.dspl').write_bytes(task_path.read_bytes())
    (run_dir / 'VISIBLE_KS.dspl').write_bytes(ks_path.read_bytes())
    if meta_path is not None and meta_path.exists():
        (run_dir / 'TASK_META.txt').write_bytes(meta_path.read_bytes())


def build_minimal_check_bundle(run_dir: Path):
    names = [
        'PRE_ENVELOPE.json',
        'CURRENT_TASK.dspl',
        'VISIBLE_KS.dspl',
        'FINAL_MESSAGE.txt',
        'TRANSITION_OUTPUT.json',
        'MINIMAL_RESULT.txt',
        'MINIMAL_TRACE.txt',
        'E2_EVALUATION.json',
        'E2_RESULT.txt',
        'READER_DIAGNOSIS.txt',
        'KSU_RESULT_MIN.json',
        'KS_DELTA.dspl',
        'POST_ENVELOPE.json',
        'codex_version.txt',
        'stderr.txt',
        'stdout.txt',
        'TASK_META.txt',
    ]
    z = run_dir / 'E2_CHECK_BUNDLE_MINIMAL.zip'
    if z.exists():
        z.unlink()
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            p = run_dir / name
            if p.exists():
                zf.write(p, name)
    return z
