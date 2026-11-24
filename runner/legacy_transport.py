from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import secrets
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path

from e2_group_a import evaluate_e2_group_a, screen_lines as e2_screen_lines, write_e2_artifacts, build_minimal_check_bundle as build_e2_minimal_check_bundle
from e3_composition import evaluate_e3, screen_lines as e3_screen_lines, write_e3_artifacts, build_minimal_check_bundle as build_e3_minimal_check_bundle, reader_line as e3_reader_line, verify_checkpoint_chain as verify_e3_checkpoint_chain

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'manifest.csv'
P0 = ROOT / 'frozen' / 'P0_consolidated_T1_T6_v14.tex'
P0_E3 = ROOT / 'frozen' / 'P0_E3_EXTENSION_v01.tex'
TAEP = ROOT / 'taep' / 'TAEP_ACTIVE.txt'
TRANSPORT = ROOT / 'TRANSPORT_HEADER.txt'
TRANSITION_SCHEMA = ROOT / 'schemas' / 'transition.schema.json'
HEALTH_SCHEMA = ROOT / 'schemas' / 'health.schema.json'
HEALTH_TAEP = ROOT / 'health' / 'HEALTH_TAEP.txt'
HEALTH_PAYLOAD_TEMPLATE = ROOT / 'health' / 'HEALTH_PAYLOAD_TEMPLATE.txt'
CONFIG = ROOT / 'EXPERIMENT_CONFIG.json'
PROPOSER_PROFILES = ROOT / 'PROPOSER_PROFILES.json'
EXPERIMENTS = ROOT / 'EXPERIMENTS.json'
FROZEN_HASHES = ROOT / 'FROZEN_SHA256.json'
TAEP_APPROVAL = ROOT / 'taep' / 'TAEP_APPROVAL.json'
RUNS = ROOT / 'runs'
ENVELOPE_VERSION = 'LLM_PROPOSER_ENVELOPE_v08_MODEL_SELECTION_P0v14_E3v01'

ACTIVE_PROPOSER_CONFIG = None


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def sha_text(text: str) -> str:
    return sha_bytes(text.encode('utf-8'))


def write_text_exact(path: Path, text: str) -> None:
    # Always write the exact UTF-8 bytes supplied here.  In particular, do not
    # allow platform newline translation to change audit bytes on Windows.
    path.write_bytes(text.encode('utf-8'))


def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def find_codex() -> str | None:
    names = ['codex.cmd', 'codex'] if os.name == 'nt' else ['codex', 'codex.cmd']
    for name in names:
        p = shutil.which(name)
        if p:
            return p
    return None


def run_text(cmd, **kwargs):
    return subprocess.run(
        cmd,
        text=True,
        encoding='utf-8',
        errors='replace',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs,
    )


def rows():
    with MANIFEST.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def row_for(run_id: str):
    for r in rows():
        if r['run_id'] == run_id:
            return r
    raise ValueError(f'Unknown run_id: {run_id}')


def strict_schema_problems(node, path='$'):
    problems = []
    if isinstance(node, dict):
        if node.get('type') == 'object':
            props = node.get('properties')
            if not isinstance(props, dict):
                problems.append(f'{path}: object must define properties')
            else:
                if node.get('additionalProperties') is not False:
                    problems.append(f'{path}: additionalProperties must be false')
                req = node.get('required')
                if not isinstance(req, list) or set(req) != set(props):
                    problems.append(f'{path}: required must list every property')
                for k, v in props.items():
                    problems.extend(strict_schema_problems(v, f'{path}.{k}'))
        if 'items' in node:
            problems.extend(strict_schema_problems(node['items'], f'{path}.items'))
        if 'anyOf' in node:
            for i, x in enumerate(node['anyOf']):
                problems.extend(strict_schema_problems(x, f'{path}.anyOf[{i}]'))
    elif isinstance(node, list):
        for i, x in enumerate(node):
            problems.extend(strict_schema_problems(x, f'{path}[{i}]'))
    return problems


def load_proposer_profiles():
    return json.loads(PROPOSER_PROFILES.read_text(encoding='utf-8'))


def _normalize_effort(value: str) -> str:
    return (value or '').strip().lower()


def _proposer_record(profile: str, model: str, effort: str, paper_replication: bool, source: str):
    return {
        'profile': profile,
        'model': model.strip(),
        'reasoning_effort': _normalize_effort(effort),
        'paper_replication': bool(paper_replication),
        'selection_source': source,
    }


def set_proposer_configuration(profile: str | None = None, model: str | None = None, reasoning_effort: str | None = None, source: str = 'cli'):
    global ACTIVE_PROPOSER_CONFIG
    spec = load_proposer_profiles()
    allowed = set(spec.get('allowed_reasoning_efforts') or [])
    profiles = spec.get('profiles') or {}

    if model is not None:
        if not model.strip():
            raise ValueError('Custom model identifier must not be empty.')
        effort = _normalize_effort(reasoning_effort or 'medium')
        if effort not in allowed:
            raise ValueError('Reasoning effort must be one of: ' + ', '.join(sorted(allowed)))
        ACTIVE_PROPOSER_CONFIG = _proposer_record('CUSTOM', model, effort, False, source)
        return ACTIVE_PROPOSER_CONFIG

    profile = (profile or spec.get('default_profile') or 'PAPER').strip().upper()
    if profile not in profiles:
        raise ValueError(f'Unknown proposer profile: {profile}')
    item = profiles[profile]
    effort = _normalize_effort(item.get('reasoning_effort', 'medium'))
    if effort not in allowed:
        raise ValueError(f'Profile {profile} has unsupported reasoning effort: {effort}')
    ACTIVE_PROPOSER_CONFIG = _proposer_record(
        profile, item.get('model', ''), effort, item.get('paper_replication', False), source
    )
    return ACTIVE_PROPOSER_CONFIG


def active_proposer_configuration():
    global ACTIVE_PROPOSER_CONFIG
    if ACTIVE_PROPOSER_CONFIG is None:
        set_proposer_configuration()
    return dict(ACTIVE_PROPOSER_CONFIG)


def select_proposer_configuration_interactive():
    spec = load_proposer_profiles()
    profiles = spec.get('profiles') or {}
    default_profile = (spec.get('default_profile') or 'PAPER').upper()
    allowed = spec.get('allowed_reasoning_efforts') or []
    print('\n' + '=' * 68)
    print('LLM PROPOSER CONFIGURATION')
    print('=' * 68)
    paper = profiles.get('PAPER', {})
    legacy = profiles.get('LEGACY', {})
    print('  [1] PAPER PROFILE' + ('  [default]' if default_profile == 'PAPER' else ''))
    print(f"      model={paper.get('model','?')}; reasoning={paper.get('reasoning_effort','?')}")
    print('      frozen configuration for the reported experiments')
    print('  [2] LEGACY PROFILE')
    print(f"      model={legacy.get('model','?')}; reasoning={legacy.get('reasoning_effort','?')}")
    print('      reproduces the earlier development setting')
    print('  [3] CUSTOM MODEL')
    print('      enter a model identifier and reasoning effort')
    while True:
        choice = input('Selection [1]: ').strip() or '1'
        if choice == '1':
            cfg = set_proposer_configuration('PAPER', source='interactive_hardcoded')
            break
        if choice == '2':
            cfg = set_proposer_configuration('LEGACY', source='interactive_hardcoded')
            break
        if choice == '3':
            while True:
                model = input('Model identifier: ').strip()
                if model:
                    break
                print('Model identifier must not be empty.')
            while True:
                effort = input('Reasoning effort [medium]: ').strip().lower() or 'medium'
                if effort in allowed:
                    break
                print('Choose one of: ' + ', '.join(allowed))
            cfg = set_proposer_configuration(model=model, reasoning_effort=effort, source='interactive_custom')
            break
        print('Invalid selection.')
    print('-' * 68)
    print(f"ACTIVE PROPOSER: model={cfg['model']}; reasoning={cfg['reasoning_effort']}; profile={cfg['profile']}")
    if not cfg['paper_replication']:
        print('NOTE: this run is not tagged as a paper-profile replication.')
    print('=' * 68)
    return cfg


def load_config():
    cfg = json.loads(CONFIG.read_text(encoding='utf-8'))
    pcfg = active_proposer_configuration()
    cfg['model'] = pcfg['model']
    cfg['reasoning_effort'] = pcfg['reasoning_effort']
    return cfg


def load_experiments():
    return json.loads(EXPERIMENTS.read_text(encoding='utf-8'))


def rows_for_experiment(experiment_id: str):
    experiments = load_experiments()
    if experiment_id not in experiments:
        raise ValueError(f'Unknown experiment: {experiment_id}')
    return [row_for(run_id) for run_id in experiments[experiment_id].get('run_ids', [])]


def verify_package(verbose=True):
    required = [MANIFEST, P0, P0_E3, TAEP, TRANSPORT, TRANSITION_SCHEMA, HEALTH_SCHEMA,
                HEALTH_TAEP, HEALTH_PAYLOAD_TEMPLATE, CONFIG, PROPOSER_PROFILES, EXPERIMENTS, FROZEN_HASHES, TAEP_APPROVAL]
    problems = [f'Missing: {p}' for p in required if not p.exists()]
    for r in rows() if MANIFEST.exists() else []:
        for k in ('task_file', 'ks_file'):
            p = ROOT / r[k]
            if not p.exists():
                problems.append(f"Run {r['run_id']}: missing {k}: {p}")
        meta_file = (r.get('meta_file') or '').strip()
        if meta_file:
            p = ROOT / meta_file
            if not p.exists():
                problems.append(f"Run {r['run_id']}: missing meta_file: {p}")
    if EXPERIMENTS.exists() and MANIFEST.exists():
        try:
            experiments = load_experiments()
            known = {r['run_id'] for r in rows()}
            used = set()
            for eid, spec in experiments.items():
                for run_id in spec.get('run_ids', []):
                    if run_id not in known:
                        problems.append(f'Experiment {eid}: unknown run_id {run_id}')
                    if run_id in used:
                        problems.append(f'Run {run_id} assigned to more than one experiment')
                    used.add(run_id)
        except Exception as e:
            problems.append(f'Invalid EXPERIMENTS.json: {e}')
    for p in (TRANSITION_SCHEMA, HEALTH_SCHEMA):
        if p.exists():
            try:
                problems.extend(f'{p.name}: {x}' for x in strict_schema_problems(json.loads(p.read_text(encoding='utf-8'))))
            except Exception as e:
                problems.append(f'{p.name}: invalid JSON: {e}')
    problems.extend(verify_e3_checkpoint_chain(ROOT))
    if FROZEN_HASHES.exists():
        try:
            expected = json.loads(FROZEN_HASHES.read_text(encoding='utf-8'))
            for rel, digest in expected.items():
                p = ROOT / rel
                if not p.exists():
                    problems.append(f'Frozen file missing: {rel}')
                else:
                    got = sha_file(p)
                    if got != digest:
                        problems.append(f'Frozen hash mismatch: {rel}: {got} != {digest}')
        except Exception as e:
            problems.append(f'Invalid FROZEN_SHA256.json: {e}')
    if verbose:
        if problems:
            print('PACKAGE CHECK FAILED')
            for p in problems:
                print(' -', p)
        else:
            print('PACKAGE CHECK PASSED')
            print(' P0 SHA256 :', sha_file(P0))
            print(' TAEP SHA256:', sha_file(TAEP))
            print(' Manifest rows:', len(rows()))
    return problems



def require_approved_taep():
    approval = json.loads(TAEP_APPROVAL.read_text(encoding='utf-8'))
    current = sha_file(TAEP)
    if approval.get('status') != 'APPROVED':
        raise RuntimeError('TAEP is not approved for scientific transition runs. Health test remains available.')
    if approval.get('approved_sha256') != current:
        raise RuntimeError('TAEP bytes changed after approval. Re-review and update TAEP_APPROVAL.json before running tasks.')
    return approval

def codex_environment(codex: str, run_dir: Path):
    version = run_text([codex, '--version'])
    help_run = run_text([codex, 'exec', '--help'])
    vt = (version.stdout or version.stderr or '').strip()
    ht = (help_run.stdout or '') + '\n' + (help_run.stderr or '')
    write_text_exact(run_dir / 'codex_version.txt', vt + '\n')
    write_text_exact(run_dir / 'codex_exec_help.txt', ht)
    return vt, ht


def build_cmd(codex: str, help_text: str, schema_path: Path, final_path: Path):
    cfg = load_config()
    cmd = [codex, 'exec']
    if '--skip-git-repo-check' in help_text:
        cmd.append('--skip-git-repo-check')
    if cfg.get('ephemeral') and '--ephemeral' in help_text:
        cmd.append('--ephemeral')
    if '--sandbox' in help_text:
        cmd += ['--sandbox', cfg.get('sandbox', 'read-only')]
    if cfg.get('ignore_user_config') and '--ignore-user-config' in help_text:
        cmd.append('--ignore-user-config')
    if cfg.get('ignore_rules') and '--ignore-rules' in help_text:
        cmd.append('--ignore-rules')
    model = cfg.get('model')
    if model and '--model' in help_text:
        cmd += ['--model', model]
    effort = _normalize_effort(cfg.get('reasoning_effort', ''))
    if effort:
        if '--config' in help_text or re.search(r'(^|\s)-c([,\s]|$)', help_text):
            cmd += ['-c', f'model_reasoning_effort="{effort}"']
        else:
            raise RuntimeError('This Codex CLI does not expose -c/--config; cannot enforce the selected reasoning effort.')
    if '--output-schema' in help_text:
        cmd += ['--output-schema', str(schema_path)]
    if '--output-last-message' in help_text:
        cmd += ['--output-last-message', str(final_path)]
    cmd.append('-')
    return cmd


def parse_final(final_path: Path, stdout: str):
    if final_path.exists():
        raw = final_path.read_text(encoding='utf-8', errors='replace').strip()
    else:
        raw = (stdout or '').strip()
    return json.loads(raw), raw


def write_json(path: Path, value):
    write_text_exact(path, json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + '\n')


def audit_zip(run_dir: Path):
    z = run_dir / 'AUDIT_BUNDLE.zip'
    manifest = run_dir / 'AUDIT_FILE_SHA256.json'
    if z.exists():
        z.unlink()
    if manifest.exists():
        manifest.unlink()
    file_hashes = {}
    for p in sorted(run_dir.rglob('*')):
        if p.is_file() and p not in (z, manifest):
            file_hashes[str(p.relative_to(run_dir)).replace('\\', '/')] = sha_file(p)
    write_json(manifest, file_hashes)
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(run_dir.rglob('*')):
            if p.is_file() and p != z:
                zf.write(p, p.relative_to(run_dir))
    return z


def execute_request(name: str, prompt: str, schema_obj: dict, pre: dict, post_checks, run_dir: Path):
    total_started = time.monotonic()
    print(f'[{name}] prepare', flush=True)
    run_dir.mkdir(parents=True, exist_ok=False)

    setup_started = time.monotonic()
    write_text_exact(run_dir / 'REQUEST.txt', prompt)
    pre = dict(pre)
    pre['request_sha256'] = sha_file(run_dir / 'REQUEST.txt')
    write_json(run_dir / 'PRE_ENVELOPE.json', pre)

    codex = find_codex()
    if not codex:
        raise RuntimeError('codex.cmd/codex not found on PATH')
    env_started = time.monotonic()
    version, help_text = codex_environment(codex, run_dir)
    env_probe_seconds = time.monotonic() - env_started

    schema_path = run_dir / 'OUTPUT.schema.json'
    write_json(schema_path, schema_obj)
    final = run_dir / 'FINAL_MESSAGE.txt'
    cmd = build_cmd(codex, help_text, schema_path, final)
    cmd_public = [str(x) for x in cmd[:-1]] + ['<STDIN>']
    proposer_cfg = active_proposer_configuration()
    write_json(run_dir / 'PROPOSER_CONFIGURATION.json', proposer_cfg)
    write_json(run_dir / 'EXECUTION_POLICY.json', {
        'command': cmd_public,
        'cwd_policy': 'fresh_temporary_directory',
        'input_transport': 'stdin',
        'automatic_retries': 0,
        'codex_version': version,
        'proposer_configuration': proposer_cfg,
    })
    setup_seconds = time.monotonic() - setup_started - env_probe_seconds

    with tempfile.TemporaryDirectory(prefix='LML_LLM_ENVELOPE_') as td:
        work = Path(td)
        local_schema = work / 'OUTPUT.schema.json'
        local_schema.write_bytes(schema_path.read_bytes())
        local_final = work / 'FINAL_MESSAGE.txt'
        cmd = build_cmd(codex, help_text, local_schema, local_final)
        print(f'[{name}] Codex running ...', flush=True)
        started = time.monotonic()
        p = run_text(cmd, cwd=str(work), input=prompt)
        codex_seconds = time.monotonic() - started
        print(f'[{name}] Codex finished: exit={p.returncode}, {codex_seconds:.1f}s', flush=True)
        write_text_exact(run_dir / 'stdout.txt', p.stdout or '')
        write_text_exact(run_dir / 'stderr.txt', p.stderr or '')
        if local_final.exists():
            final.write_bytes(local_final.read_bytes())

    parse_started = time.monotonic()
    post = {
        'name': name,
        'codex_exit_code': p.returncode,
        'stdout_sha256': sha_file(run_dir / 'stdout.txt'),
        'stderr_sha256': sha_file(run_dir / 'stderr.txt'),
        'final_message_present': final.exists(),
        'parse_status': 'NOT_ATTEMPTED',
        'transport_status': 'REJECTED',
        'checks': {},
    }
    data = None
    raw = ''
    if p.returncode == 0:
        try:
            data, raw = parse_final(final, p.stdout or '')
            post['parse_status'] = 'JSON_OK'
            post['final_message_sha256'] = sha_file(final)
            ok, checks = post_checks(data)
            post['checks'] = checks
            post['transport_status'] = 'READY_FOR_REVIEW' if ok else 'REVIEW_REQUIRED'
            write_json(run_dir / 'TRANSITION_OUTPUT.json', data)
        except Exception as e:
            post['parse_status'] = 'JSON_ERROR'
            post['parse_error'] = str(e)
    parse_validation_seconds = time.monotonic() - parse_started

    post_started = time.monotonic()
    write_json(run_dir / 'POST_ENVELOPE.json', post)
    lines = [f'name={name}', f'exit_code={p.returncode}', f'parse={post["parse_status"]}', f'transport={post["transport_status"]}']
    for k, v in post.get('checks', {}).items():
        lines.append(f'{k}={v}')
    write_text_exact(run_dir / 'SUMMARY.txt', '\n'.join(lines) + '\n')
    post_files_seconds = time.monotonic() - post_started

    audit_started = time.monotonic()
    audit_zip(run_dir)
    initial_audit_seconds = time.monotonic() - audit_started

    runtime = {
        'request_setup_seconds': round(setup_seconds, 6),
        'codex_environment_probe_seconds': round(env_probe_seconds, 6),
        'codex_execution_seconds': round(codex_seconds, 6),
        'parse_validation_seconds': round(parse_validation_seconds, 6),
        'post_files_seconds': round(post_files_seconds, 6),
        'initial_audit_seconds': round(initial_audit_seconds, 6),
        'execute_request_total_seconds': round(time.monotonic() - total_started, 6),
    }
    write_json(run_dir / 'RUNTIME_DIAGNOSTIC.json', runtime)
    # Rebuild once so the diagnostic itself is archived.  run_one may later
    # extend this diagnostic with display/final-audit timings and rebuild again.
    audit_zip(run_dir)
    print(f'[{name}] post: {post["transport_status"]}', flush=True)
    return post, data, runtime


def _candidate_key(item):
    b = item.get('binding') or {}
    return (item.get('hypothesis'), b.get('unknown'), b.get('value'))


def _fact_value(facts, prefix):
    """Return the inside of the first fact matching prefix(...), or None."""
    needle = prefix + '('
    for fact in facts or []:
        if isinstance(fact, str) and fact.startswith(needle) and fact.endswith(')'):
            return fact[len(needle):-1]
    return None


def _construction_route_lines(data):
    """Compact human-readable construction support; reporting only."""
    construction = (data or {}).get('construction_phase') or {}
    if construction.get('status') != 'construction_proposed':
        return []

    knowledge = ((data or {}).get('knowledge_proposal_bundle') or {}).get('items') or []
    idx = construction.get('knowledge_proposal_index')
    item = None
    for candidate in knowledge:
        if idx is not None and candidate.get('index') == idx:
            item = candidate
            break
    if item is None and knowledge:
        item = knowledge[0]
    facts = (item or {}).get('facts') or []

    family = _fact_value(facts, 'knowledge_description_procedure_family')
    formation = _fact_value(facts, 'knowledge_description_formation_kind')
    projection = _fact_value(facts, 'projection_schemas')
    finite = _fact_value(facts, 'finite_schemas')
    relation = _fact_value(facts, 'relation_schemas')
    represented_relation = _fact_value(facts, 'represented_relation')

    lines = []
    if family or formation:
        bits = []
        if family:
            bits.append(family)
        if formation:
            bits.append(f'formation={formation}')
        lines.append('constructed ' + '; '.join(bits))
    if projection:
        lines.append(f'projection schemas: {projection}')
    if finite:
        lines.append(f'finite-component schemas: {finite}')
    if relation:
        lines.append(f'relation-component schemas: {relation}')
    if represented_relation:
        lines.append(f'represented relation: {represented_relation}')
    return lines


def solution_text(data):
    if not isinstance(data, dict):
        return '-'
    construction = data.get('construction_phase') or {}
    dep = construction.get('dependent_solution') or {}
    if dep.get('present'):
        return f"{dep.get('unknown','?')}={dep.get('value','?')}"
    selected = data.get('selected') or []
    vals = []
    for item in selected:
        b = item.get('binding') or {}
        vals.append(f"{b.get('unknown','?')}={b.get('value','?')}")
    return '; '.join(vals) if vals else '-'


def route_lines(data):
    if not isinstance(data, dict):
        return []
    selected = data.get('selected') or []
    lines = []
    for item in selected:
        b = item.get('binding') or {}
        lines.append(
            f"{item.get('hypothesis','?')} -> "
            f"{b.get('unknown','?')}={b.get('value','?')}"
        )
    if not lines:
        lines.extend(_construction_route_lines(data))
    return lines


def minimal_result_text(data):
    if not isinstance(data, dict):
        return 'RESULT: unavailable (no parsed transition output)'
    knowledge = (data.get('knowledge_proposal_bundle') or {}).get('items') or []
    construction = data.get('construction_phase') or {}
    return (
        f"RESULT: task={data.get('task_id','?')}; generation={data.get('generation_status','?')}; "
        f"local_outcome={data.get('local_outcome','?')}; solution={solution_text(data)}; "
        f"construction={construction.get('status','?')}; knowledge_proposals={len(knowledge)}"
    )


def minimal_trace_text(data, console_limit=None):
    if not isinstance(data, dict):
        return 'TRACE: unavailable'
    selected_keys = {_candidate_key(x) for x in (data.get('selected') or [])}
    entries = []
    for item in data.get('candidates') or []:
        b = item.get('binding') or {}
        key = _candidate_key(item)
        if key in selected_keys:
            status = 'selected'
        else:
            nonpass = [
                f"{c.get('check')}={c.get('result')}"
                for c in (item.get('checks') or [])
                if c.get('result') != 'pass'
            ]
            status = 'reject:' + ','.join(nonpass) if nonpass else 'not-selected'
        entries.append(
            f"{item.get('hypothesis','?')}=>{b.get('unknown','?')}={b.get('value','?')} [{status}]"
        )
    shown = entries
    suffix = ''
    if console_limit is not None and len(entries) > console_limit:
        shown = entries[:console_limit]
        suffix = f" | ... (+{len(entries)-console_limit} more)"
    steps = ((data.get('raw_trace_serial') or {}).get('steps') or [])
    construction = data.get('construction_phase') or {}
    if shown:
        body = ' | '.join(shown)
    elif construction.get('status') == 'construction_proposed':
        body = 'local candidate set empty; bounded construction entered'
    else:
        body = 'no local candidates'
    ctext = f"construction={construction.get('status','?')}"
    if construction.get('support_facts'):
        ctext += f"; construction_support_facts={len(construction.get('support_facts') or [])}"
    return f"TRACE: candidates={len(entries)}; steps={len(steps)}; {body}{suffix} | {ctext}"


def _position_sort_key(pos: str):
    m = re.fullmatch(r'I(\d+)', pos or '')
    return (0, int(m.group(1))) if m else (1, str(pos))


def task_display_info(r):
    """Parse the frozen task DSPL for compact human-readable console reporting."""
    path = ROOT / r['task_file']
    lines = [x.strip() for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
    task_id = r['task_id']

    inputs = []
    available_relations = []
    values = {}
    unknown = None
    constraints = []

    for line in lines:
        parts = line.split()
        if len(parts) >= 4 and parts[0] == 'QUALIFY' and parts[1] == task_id and parts[2] == 'input':
            if parts[3] not in inputs:
                inputs.append(parts[3])
        elif len(parts) >= 4 and parts[0] == 'QUALIFY' and parts[1] == task_id and parts[2] == 'available_relation':
            if parts[3] not in available_relations:
                available_relations.append(parts[3])
        elif len(parts) >= 4 and parts[0] == 'AT':
            values.setdefault(parts[1], {})[parts[2]] = parts[3]
        elif len(parts) >= 6 and parts[0] == 'UNKNOWN_AT' and parts[1] == task_id:
            unknown = {
                'unknown': parts[2],
                'stream': parts[3],
                'position': parts[4],
                'type': ' '.join(parts[5:]),
            }
        elif len(parts) >= 2 and parts[0] == 'CONSTRAINT':
            kind = parts[1]
            if kind == 'SAME_RELATION_SUCCESSIVE' and len(parts) >= 4:
                constraints.append(f'SAME_RELATION_SUCCESSIVE({parts[3]})')
            elif kind == 'COMPONENT_RELATION' and len(parts) >= 6:
                constraints.append(
                    f'COMPONENT_RELATION({parts[3]}, component {parts[4]}, {parts[5]})'
                )
            else:
                constraints.append(' '.join(parts[1:]))

    if unknown:
        values.setdefault(unknown['stream'], {})[unknown['position']] = '?'

    streams = []
    for stream in inputs:
        posmap = values.get(stream, {})
        ordered = [posmap[k] for k in sorted(posmap, key=_position_sort_key)]
        streams.append((stream, ordered))

    return {
        'task_id': task_id,
        'episode_id': r['episode_id'],
        'streams': streams,
        'unknown': unknown,
        'constraints': constraints,
        'available_relations': available_relations,
    }


def console_task_block(r):
    """Compact display of the original frozen task before the LLM call."""
    if str(r.get('run_id','')).startswith('E3'):
        path = ROOT / r['task_file']
        raw = [x.strip() for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
        title = f"ORIGINAL TASK {r['task_id']}"
        if r['episode_id'] != r['task_id']:
            title += f"  [episode {r['episode_id']}]"
        lines = ['', '-' * 68, title]
        for line in raw:
            p = line.split()
            if not p:
                continue
            if p[0] == 'E3_EXAMPLE_L2_TO_L':
                lines.append(f"  {p[2]}{p[3]} -> {p[4]}")
            elif p[0] == 'E3_QUERY_L2_TO_L':
                lines.append(f"  {p[3]}{p[4]} -> ?   [{p[2]}]")
            elif p[0] == 'E3_EXAMPLE_LN_TO_N':
                lines.append(f"  {p[2]}{p[3]} -> {p[4]}")
            elif p[0] == 'E3_QUERY_LN_TO_N':
                lines.append(f"  {p[3]}{p[4]} -> ?   [{p[2]}]")
            elif p[0] == 'E3_EXAMPLE_LLN_TO_LN':
                lines.append(f"  {p[2]}{p[3]}{p[4]} -> {p[5]}{p[6]}")
            elif p[0] == 'E3_QUERY_LLN_TO_LN':
                lines.append(f"  {p[3]}{p[4]}{p[5]} -> ?   [{p[2]}]")
            elif p[0] == 'E3_EXAMPLE_LNLN_TO_LN':
                lines.append(f"  {p[2]}{p[3]}, {p[4]}{p[5]} -> {p[6]}{p[7]}")
            elif p[0] == 'E3_QUERY_LNLN_TO_LN':
                lines.append(f"  {p[3]}{p[4]}, {p[5]}{p[6]} -> ?   [{p[2]}]")
        lines.append(f"CONSTRUCTION: {'enabled' if r['construction_allowed'].strip().lower() == 'true' else 'disabled'}")
        lines.append(f"VISIBLE KS: {r['visible_ks_id']}")
        lines.append('-' * 68)
        return lines

    info = task_display_info(r)
    title = f"ORIGINAL TASK {info['task_id']}"
    if info['episode_id'] != info['task_id']:
        title += f"  [episode {info['episode_id']}]"
    lines = ['', '-' * 68, title]
    for stream, vals in info['streams']:
        lines.append(f"  {stream} = [{', '.join(vals)}]")
    u = info['unknown']
    if u:
        lines.append(f"  UNKNOWN: {u['unknown']} at {u['stream']}/{u['position']}")
    lines.append('TASK LAW(S) / CONSTRAINT(S):')
    if info['constraints']:
        for c in info['constraints']:
            lines.append(f'  - {c}')
    else:
        lines.append('  - none explicit')
    if info['available_relations']:
        lines.append('AVAILABLE RELATIONS: ' + ', '.join(info['available_relations']))
    lines.append('-' * 68)
    return lines


def solution_law_lines(data, r):
    """Human-readable laws actually used by the accepted route; reporting only."""
    if not isinstance(data, dict):
        return []
    info = task_display_info(r)
    selected = data.get('selected') or []
    construction = data.get('construction_phase') or {}
    laws = []

    def add(x):
        if x and x not in laws:
            laws.append(x)

    for item in selected:
        hyp = str(item.get('hypothesis') or '')
        facts = [str(x) for x in (item.get('support_facts') or [])]
        if hyp.startswith('F0('):
            m = re.match(r'F0\([^,]+,([^\)]+)\)', hyp)
            rel = m.group(1) if m else None
            if info['constraints'] and any(c.startswith('SAME_RELATION_SUCCESSIVE') for c in info['constraints']):
                add(f'SAME_RELATION_SUCCESSIVE using {rel or "represented relation"}')
            elif rel:
                add(f'relation {rel}')
        elif hyp.startswith('F3('):
            add('componentwise ALL_ONCE / finite-reference residual completion')
        elif hyp.startswith('F4('):
            found = False
            for fact in facts:
                m = re.search(r'task_component_relation\([^,]+,[^,]+,(\d+),([^\)]+)\)', fact)
                if m:
                    add(f'component {m.group(1)} relation {m.group(2)}')
                    found = True
            if not found:
                for c in info['constraints']:
                    if c.startswith('COMPONENT_RELATION'):
                        add(c.replace('COMPONENT_RELATION(', '').rstrip(')'))
        elif hyp.startswith('F1('):
            # F1 may delegate to a scalar relation, F3/F4, or mixed componentwise reuse.
            for fact in facts:
                m = re.search(r'task_component_relation\([^,]+,[^,]+,(\d+),([^\)]+)\)', fact)
                if m:
                    add(f'component {m.group(1)} relation {m.group(2)}')
                m = re.search(r'task_available_relation\([^,]+,([^\)]+)\)', fact)
                if m and 'single_relation_completion' in ' '.join(facts):
                    add(f'relation {m.group(1)}')
            if 'stored_componentwise_reuse' in ' '.join(facts) or 'H14' in hyp:
                # In the demonstrated mixed reuse, the non-relation component is finite-reference completion.
                relation_components = set()
                for c in info['constraints']:
                    m = re.match(r'COMPONENT_RELATION\([^,]+, component (\d+), ([^\)]+)\)', c)
                    if m:
                        relation_components.add(int(m.group(1)))
                        add(f'component {m.group(1)} relation {m.group(2)}')
                for k in (1, 2):
                    if k not in relation_components:
                        add(f'component {k} finite-reference residual completion')

    if not selected and construction.get('status') == 'construction_proposed':
        relation_components = set()
        for c in info['constraints']:
            m = re.match(r'COMPONENT_RELATION\([^,]+, component (\d+), ([^\)]+)\)', c)
            if m:
                relation_components.add(int(m.group(1)))
                add(f'component {m.group(1)} relation {m.group(2)}')
        for k in (1, 2):
            if k not in relation_components:
                add(f'component {k} finite-reference residual completion')

    return laws


def console_result_block(data, r):
    """Prominent per-episode console result. Reporting only."""
    if not isinstance(data, dict):
        return [
            '=' * 68,
            'SOLUTION: unavailable',
            '=' * 68,
        ]

    task = data.get('task_id', '?')
    construction = data.get('construction_phase') or {}
    overall = overall_outcome(data)
    sol = solution_text(data)
    routes = route_lines(data)
    laws = solution_law_lines(data, r)

    if str(r.get('run_id','')).startswith('E2'):
        lines = [
            '',
            '=' * 68,
            f'EPISODE {task}',
            f'PROPOSER BINDING : {sol}',
            f'PROPOSER OUTCOME : {overall}',
        ]
    else:
        lines = [
            '',
            '=' * 68,
            f'EPISODE {task}',
            f'SOLUTION : {sol}',
            f'OUTCOME  : {overall}',
        ]

    if laws:
        lines.append('LAW(S) USED BY SOLUTION:')
        for x in laws:
            lines.append(f'  - {x}')
    else:
        lines.append('LAW(S) USED BY SOLUTION: none selected')

    if routes:
        lines.append('RULE / PROCEDURE:')
        for x in routes:
            lines.append(f'  - {x}')
    else:
        lines.append('RULE / PROCEDURE: none')

    local = data.get('local_outcome', '?')
    if local == 'no_local_solution' and construction.get('status') == 'construction_proposed':
        lines.append('LOCAL SEARCH: no_local_solution -> construction entered')
    else:
        lines.append(f'LOCAL SEARCH: {local}')

    lines.append(f"CONSTRUCTION: {construction.get('status','?')}")
    lines.append('=' * 68)
    return lines


def write_minimal_views(run_dir: Path, data, r):
    result = minimal_result_text(data)
    trace_full = minimal_trace_text(data, console_limit=None)
    write_text_exact(run_dir / 'MINIMAL_RESULT.txt', result + '\n')
    write_text_exact(run_dir / 'MINIMAL_TRACE.txt', trace_full + '\n')
    run_id = str(r.get('run_id',''))
    if not (run_id.startswith('E2') or run_id.startswith('E3')):
        for line in console_result_block(data, r):
            print(line, flush=True)
        print(minimal_trace_text(data, console_limit=6), flush=True)


def health():
    # Generate per-run opaque canaries.  Their values are present only in the
    # HEALTH_PAYLOAD block sent through stdin; they are NOT inserted into the
    # JSON output schema.
    tag = secrets.token_hex(8).upper()
    vals = {
        'CANARY_ASCII': f'ENVELOPE-ASCII-{tag}',
        'CANARY_UTF8': f'Árvíztűrő-tükörfúrógép-{tag}',
        'CANARY_MULTILINE': f'FIRST-LINE-{tag}\nSECOND-LINE-{tag}',
    }
    template = HEALTH_PAYLOAD_TEMPLATE.read_text(encoding='utf-8')
    payload = template.format(**vals)

    schema = json.loads(HEALTH_SCHEMA.read_text(encoding='utf-8'))
    prompt = (
        TRANSPORT.read_text(encoding='utf-8').strip() + '\n\n'
        + '<<<BEGIN HEALTH_TAEP>>>\n' + HEALTH_TAEP.read_text(encoding='utf-8') + '<<<END HEALTH_TAEP>>>\n\n'
        + '<<<BEGIN HEALTH_PAYLOAD>>>\n' + payload + '<<<END HEALTH_PAYLOAD>>>\n'
    )
    run_dir = RUNS / f'HEALTH_{utc_stamp()}'
    pre = {
        'envelope_version': ENVELOPE_VERSION,
        'mode': 'HEALTH',
        'health_taep_sha256': sha_file(HEALTH_TAEP),
        'health_payload_template_sha256': sha_file(HEALTH_PAYLOAD_TEMPLATE),
        'transport_header_sha256': sha_file(TRANSPORT),
        'schema_canaries_constrained': False,
        'canaries_generated_per_run': True,
        'multiline_canary_contains_literal_lf': True,
        'audit_hash_mode': 'exact_archived_bytes',
    }

    def checks(data):
        c = {
            'protocol_exact': data.get('protocol') == 'LLM_ENVELOPE_HEALTH_V01',
            'status_ok': data.get('status') == 'OK',
            'canary_ascii_exact': data.get('canary_ascii') == vals['CANARY_ASCII'],
            'canary_utf8_exact': data.get('canary_utf8') == vals['CANARY_UTF8'],
            'canary_multiline_exact': data.get('canary_multiline') == vals['CANARY_MULTILINE'],
        }
        return all(c.values()), c

    # execute_request creates the run directory.  Afterward, archive the exact
    # host-side expected values and rebuild the audit bundle so it includes them.
    post, data, runtime = execute_request('HEALTH', prompt, schema, pre, checks, run_dir)
    write_json(run_dir / 'HEALTH_EXPECTED.json', vals)
    audit_zip(run_dir)
    print('HEALTH:', post['transport_status'])
    print('Audit:', run_dir / 'AUDIT_BUNDLE.zip')
    return 0 if post['transport_status'] == 'READY_FOR_REVIEW' else 4


def invocation_text(r):
    return (
        'PROTOCOL = LML_PROPOSER_TRANSITION_V02\n'
        f"TASK_ID = {r['task_id']}\n"
        f"EPISODE_ID = {r['episode_id']}\n"
        f"CONSTRUCTION_CONTROL = {'enabled' if r['construction_allowed'].strip().lower() == 'true' else 'disabled'}\n"
    )


def transition_prompt(r):
    p0_text = P0.read_text(encoding='utf-8')
    if str(r.get('run_id','')).startswith('E3'):
        extension = P0_E3.read_text(encoding='utf-8').rstrip() + '\n\n'
        end_marker = '%<*src_p0end>\nP0_END'
        if end_marker not in p0_text:
            raise RuntimeError('Cannot insert E3 P0 extension: P0_END marker not found')
        p0_text = p0_text.replace(end_marker, extension + end_marker, 1)
    text = (
        TRANSPORT.read_text(encoding='utf-8').strip() + '\n\n'
        + '<<<BEGIN TAEP>>>\n' + TAEP.read_text(encoding='utf-8') + '<<<END TAEP>>>\n\n'
        + '<<<BEGIN P0>>>\n' + p0_text + '\n<<<END P0>>>\n\n'
        + '<<<BEGIN INVOCATION>>>\n' + invocation_text(r) + '<<<END INVOCATION>>>\n\n'
        + '<<<BEGIN CURRENT_TASK>>>\n' + (ROOT / r['task_file']).read_text(encoding='utf-8') + '\n<<<END CURRENT_TASK>>>\n\n'
        + '<<<BEGIN VISIBLE_KS>>>\n' + (ROOT / r['ks_file']).read_text(encoding='utf-8') + '\n<<<END VISIBLE_KS>>>\n'
    )
    meta_file = (r.get('meta_file') or '').strip()
    if meta_file:
        text += (
            '\n<<<BEGIN NONSEMANTIC_TASK_META>>>\n'
            + (ROOT / meta_file).read_text(encoding='utf-8')
            + '\n<<<END NONSEMANTIC_TASK_META>>>\n'
        )
    return text


def transition_solution(data):
    if not isinstance(data, dict):
        return ''
    construction = data.get('construction_phase') or {}
    dep = construction.get('dependent_solution') or {}
    if dep.get('present'):
        return f"{dep.get('unknown','?')}={dep.get('value','?')}"
    selected = data.get('selected') or []
    vals = []
    for item in selected:
        b = item.get('binding') or {}
        vals.append(f"{b.get('unknown','?')}={b.get('value','?')}")
    return ';'.join(vals)


def overall_outcome(data):
    if not isinstance(data, dict):
        return 'unavailable'
    construction = data.get('construction_phase') or {}
    dep = construction.get('dependent_solution') or {}
    if dep.get('present'):
        return 'solution_proposed'
    if data.get('selected'):
        return 'solution_proposed'
    if data.get('local_outcome') == 'no_local_solution':
        return 'no_solution'
    return str(data.get('local_outcome') or 'unknown')


def curriculum_summary_row(r, post, data, runtime):
    construction = (data or {}).get('construction_phase') or {}
    return {
        'run_id': r['run_id'],
        'episode_id': r['episode_id'],
        'task_id': r['task_id'],
        'transport_status': post['transport_status'],
        'generation_status': None if data is None else data.get('generation_status'),
        'local_outcome': None if data is None else data.get('local_outcome'),
        'construction_status': None if data is None else construction.get('status'),
        'overall_outcome': overall_outcome(data),
        'solution': transition_solution(data),
        'e2_ms_decision': runtime.get('e2_ms_decision'),
        'e2_primary_code': runtime.get('e2_primary_code'),
        'e2_test_status': runtime.get('e2_test_status'),
        'e3_ms_decision': runtime.get('e3_ms_decision'),
        'e3_primary_code': runtime.get('e3_primary_code'),
        'e3_test_status': runtime.get('e3_test_status'),
        'e3_update_decision': runtime.get('e3_update_decision'),
        'e3_admitted_id': runtime.get('e3_admitted_id'),
        'e3_reader_line': runtime.get('e3_reader_line'),
    }


def runtime_summary_row(r, runtime):
    return {
        'run_id': r['run_id'],
        'episode_id': r['episode_id'],
        'preflight_s': runtime.get('preflight_seconds'),
        'request_setup_s': runtime.get('request_setup_seconds'),
        'codex_environment_probe_s': runtime.get('codex_environment_probe_seconds'),
        'codex_execution_s': runtime.get('codex_execution_seconds'),
        'parse_validation_s': runtime.get('parse_validation_seconds'),
        'post_files_s': runtime.get('post_files_seconds'),
        'initial_audit_s': runtime.get('initial_audit_seconds'),
        'minimal_views_s': runtime.get('minimal_views_seconds'),
        'final_audit_s': runtime.get('final_audit_seconds'),
        'run_one_total_s': runtime.get('wall_return_seconds', runtime.get('run_one_total_seconds')), 
    }


def run_one(run_id: str, parent: Path | None = None):
    run_started = time.monotonic()
    problems = verify_package(verbose=False)
    if problems:
        raise RuntimeError('Package check failed: ' + '; '.join(problems))
    require_approved_taep()
    r = row_for(run_id)
    schema = json.loads(TRANSITION_SCHEMA.read_text(encoding='utf-8'))
    schema['properties']['task_id']['enum'] = [r['task_id']]
    construction_allowed = r['construction_allowed'].strip().lower() == 'true'
    schema['properties']['construction_phase']['properties']['allowed']['enum'] = [construction_allowed]
    prompt = transition_prompt(r)
    base = parent or (RUNS / f'RUN_{run_id}_{r["episode_id"]}_{utc_stamp()}')
    run_dir = base if parent is None else parent / f'R_{run_id}_{r["episode_id"]}'
    pre = {
        'envelope_version': ENVELOPE_VERSION,
        'mode': 'TRANSITION',
        'run_id': run_id,
        'episode_id': r['episode_id'],
        'task_id': r['task_id'],
        'visible_ks_id': r['visible_ks_id'],
        'construction_allowed': construction_allowed,
        'p0_sha256': sha_file(P0),
        'p0_e3_extension_sha256': sha_file(P0_E3) if run_id.startswith('E3') else None,
        'p0_effective_sha256': sha_text(transition_prompt(r).split('<<<BEGIN P0>>>\n',1)[1].split('\n<<<END P0>>>',1)[0]),
        'taep_sha256': sha_file(TAEP),
        'task_sha256': sha_file(ROOT / r['task_file']),
        'visible_ks_sha256': sha_file(ROOT / r['ks_file']),
        'task_meta_file': (r.get('meta_file') or '').strip() or None,
        'task_meta_sha256': sha_file(ROOT / r['meta_file']) if (r.get('meta_file') or '').strip() else None,
        'transport_header_sha256': sha_file(TRANSPORT),
        'semantic_evaluation_in_envelope': run_id.startswith('E2') or run_id.startswith('E3'),
        'expected_answer_present_in_envelope': False,
        'e2_group_a_host_replay': run_id.startswith('E2'),
        'e3_composition_host_replay': run_id.startswith('E3'),
        'proposer_configuration': active_proposer_configuration(),
    }
    def checks(data):
        c = {
            'protocol_exact': data.get('protocol') == 'LML_PROPOSER_TRANSITION_V02',
            'task_id_exact': data.get('task_id') == r['task_id'],
            'trace_task_id_exact': (data.get('raw_trace_serial') or {}).get('task_id') == r['task_id'],
            'ksp_task_id_exact': (data.get('knowledge_proposal_bundle') or {}).get('task_id') == r['task_id'],
            'construction_allowed_exact': (data.get('construction_phase') or {}).get('allowed') == construction_allowed,
        }
        return all(c.values()), c
    preflight_seconds = time.monotonic() - run_started
    for line in console_task_block(r):
        print(line, flush=True)
    post, data, runtime = execute_request(f'{run_id}:{r["episode_id"]}', prompt, schema, pre, checks, run_dir)
    runtime['preflight_seconds'] = round(preflight_seconds, 6)

    minimal_started = time.monotonic()
    write_minimal_views(run_dir, data, r)
    runtime['minimal_views_seconds'] = round(time.monotonic() - minimal_started, 6)

    if run_id.startswith('E2'):
        if post.get('transport_status') != 'READY_FOR_REVIEW' or not isinstance(data, dict):
            e2_eval = {
                'experiment': 'E2',
                'group': 'A',
                'task_id': r['task_id'],
                'static_task_check': {},
                'proposer_binding': None,
                'proposal_observation': 'no valid proposer response obtained',
                'proposer_status': 'EXECUTION_ERROR',
                'ms_decision': 'NOT_EVALUATED',
                'primary_diagnostic': {'code': 'X01', 'short': 'PROPOSER EXECUTION ERROR'},
                'secondary_diagnostics': [],
                'decision_reason': 'Codex did not return a valid proposer transition; scientific evaluation was not performed',
                'expected_control_result': {},
                'e2_test_status': 'ERROR',
                'persistent_update_allowed': False,
            }
        else:
            e2_eval = evaluate_e2_group_a(ROOT / r['task_file'], r['task_id'], data)
        write_e2_artifacts(
            run_dir, ROOT / r['task_file'], ROOT / r['ks_file'], e2_eval, write_json, write_text_exact,
            (ROOT / r['meta_file']) if (r.get('meta_file') or '').strip() else None
        )
        post['semantic_control_status'] = e2_eval['ms_decision']
        post['e2_test_status'] = e2_eval['e2_test_status']
        post['e2_primary_diagnostic'] = e2_eval['primary_diagnostic']
        write_json(run_dir / 'POST_ENVELOPE.json', post)
        runtime['e2_test_status'] = e2_eval['e2_test_status']
        runtime['e2_ms_decision'] = e2_eval['ms_decision']
        runtime['e2_primary_code'] = e2_eval['primary_diagnostic']['code']
        runtime['e2_primary_short'] = e2_eval['primary_diagnostic']['short']
        for line in e2_screen_lines(e2_eval):
            print(line, flush=True)
        check_bundle = build_e2_minimal_check_bundle(run_dir)
        print(f'E2 CHECK BUNDLE: {check_bundle}', flush=True)

    if run_id.startswith('E3'):
        if post.get('transport_status') != 'READY_FOR_REVIEW' or not isinstance(data, dict):
            e3_eval = {
                'experiment': 'E3',
                'episode_id': r['episode_id'],
                'task_id': r['task_id'],
                'task_form': None,
                'expected_binding': None,
                'examples_supported_by_represented_semantics': None,
                'example_checks': [],
                'required_family': None,
                'visible_matching_procedures': [],
                'construction_allowed': construction_allowed,
                'proposer_binding': None,
                'ms_decision': 'NOT_EVALUATED',
                'primary_diagnostic': {'code': 'X01', 'short': 'PROPOSER EXECUTION ERROR'},
                'used_support': [],
                'persistent_update': {'decision': 'NO_UPDATE', 'admitted_id': None},
                'e3_test_status': 'ERROR',
                'decision_reason': 'Codex did not return a valid proposer transition; scientific evaluation was not performed',
            }
        else:
            e3_eval = evaluate_e3(
                ROOT / r['task_file'], ROOT / r['ks_file'], r['episode_id'], construction_allowed, data
            )
        write_e3_artifacts(
            run_dir, ROOT / r['task_file'], ROOT / r['ks_file'], e3_eval, write_json, write_text_exact
        )
        post['semantic_control_status'] = e3_eval['ms_decision']
        post['e3_test_status'] = e3_eval['e3_test_status']
        post['e3_primary_diagnostic'] = e3_eval['primary_diagnostic']
        post['e3_persistent_update'] = e3_eval['persistent_update']
        write_json(run_dir / 'POST_ENVELOPE.json', post)
        runtime['e3_test_status'] = e3_eval['e3_test_status']
        runtime['e3_ms_decision'] = e3_eval['ms_decision']
        runtime['e3_primary_code'] = e3_eval['primary_diagnostic']['code']
        runtime['e3_primary_short'] = e3_eval['primary_diagnostic']['short']
        runtime['e3_reader_line'] = e3_reader_line(e3_eval)
        runtime['e3_update_decision'] = e3_eval['persistent_update']['decision']
        runtime['e3_admitted_id'] = e3_eval['persistent_update']['admitted_id']
        for line in e3_screen_lines(e3_eval):
            print(line, flush=True)
        check_bundle = build_e3_minimal_check_bundle(run_dir)
        print(f'E3 CHECK BUNDLE: {check_bundle}', flush=True)

    runtime['run_one_total_seconds'] = round(time.monotonic() - run_started, 6)
    write_json(run_dir / 'RUNTIME_DIAGNOSTIC.json', runtime)
    final_audit_started = time.monotonic()
    audit_zip(run_dir)
    runtime['final_audit_seconds'] = round(time.monotonic() - final_audit_started, 6)
    runtime['run_one_total_seconds'] = round(time.monotonic() - run_started, 6)
    write_json(run_dir / 'RUNTIME_DIAGNOSTIC.json', runtime)
    # One final rebuild includes the final diagnostic values.
    audit_zip(run_dir)
    runtime['wall_return_seconds'] = round(time.monotonic() - run_started, 6)

    print(
        'RUNTIME: '
        f"preflight={runtime.get('preflight_seconds',0):.2f}s; "
        f"setup={runtime.get('request_setup_seconds',0):.2f}s; "
        f"codex_probe={runtime.get('codex_environment_probe_seconds',0):.2f}s; "
        f"codex={runtime.get('codex_execution_seconds',0):.2f}s; "
        f"parse={runtime.get('parse_validation_seconds',0):.2f}s; "
        f"post/audit={(runtime.get('post_files_seconds',0)+runtime.get('initial_audit_seconds',0)+runtime.get('minimal_views_seconds',0)+runtime.get('final_audit_seconds',0)):.2f}s; "
        f"total={runtime.get('wall_return_seconds', runtime.get('run_one_total_seconds',0)):.2f}s",
        flush=True,
    )
    print(f'AUDIT: {run_dir / "AUDIT_BUNDLE.zip"}', flush=True)
    return post, data, runtime


def run_experiment(experiment_id: str):
    problems = verify_package(verbose=False)
    if problems:
        for p in problems:
            print(' -', p)
        return 2

    experiments = load_experiments()
    spec = experiments[experiment_id]
    exp_rows = rows_for_experiment(experiment_id)
    if not exp_rows:
        print(f'{experiment_id} -- {spec.get("title", "")}: no tasks are defined yet.')
        return 0

    parent = RUNS / f'{experiment_id}_{utc_stamp()}'
    parent.mkdir(parents=True, exist_ok=False)
    pcfg = active_proposer_configuration()
    write_json(parent / 'PROPOSER_CONFIGURATION.json', pcfg)
    write_text_exact(
        parent / 'PROPOSER_CONFIGURATION.txt',
        f"profile={pcfg['profile']}\nmodel={pcfg['model']}\nreasoning_effort={pcfg['reasoning_effort']}\npaper_replication={'YES' if pcfg['paper_replication'] else 'NO'}\nselection_source={pcfg['selection_source']}\n"
    )
    summaries = []
    runtime_rows = []
    total = len(exp_rows)
    experiment_failed = False
    experiment_started = time.monotonic()
    for i, r in enumerate(exp_rows, start=1):
        print(f"=== {experiment_id} {i}/{total}: {r['run_id']} {r['episode_id']} ===", flush=True)
        post, data, runtime = run_one(r['run_id'], parent=parent)
        summaries.append(curriculum_summary_row(r, post, data, runtime))
        runtime_rows.append(runtime_summary_row(r, runtime))
        if experiment_id == 'E3' and runtime.get('e3_test_status') != 'PASS':
            experiment_failed = True
            if runtime.get('e3_test_status') == 'ERROR':
                print('E3 sequence stopped: proposer execution error; no scientific task result was recorded.', flush=True)
            else:
                print('E3 sequence stopped: current episode did not pass its formal control; later canonical checkpoints will not be used.', flush=True)
            break
        if experiment_id == 'E2' and runtime.get('e2_test_status') != 'PASS':
            experiment_failed = True
            if runtime.get('e2_test_status') == 'ERROR':
                print('E2 contains a proposer execution error; that task was not scientifically evaluated.', flush=True)

    with (parent / 'SUMMARY.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(summaries[0]))
        w.writeheader(); w.writerows(summaries)
    with (parent / 'RUNTIME_SUMMARY.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(runtime_rows[0]))
        w.writeheader(); w.writerows(runtime_rows)

    total_seconds = time.monotonic() - experiment_started
    codex_seconds = sum(float(x.get('codex_execution_s') or 0) for x in runtime_rows)
    write_text_exact(
        parent / 'RUNTIME_SUMMARY.txt',
        'RUNTIME SUMMARY\n'
        f'experiment={experiment_id}\n'
        f'episodes_planned={total}\n'
        f'episodes_executed={len(runtime_rows)}\n'
        f'experiment_wall_seconds={total_seconds:.3f}\n'
        f'sum_codex_execution_seconds={codex_seconds:.3f}\n'
        f'non_codex_or_overlap_seconds={max(0.0, total_seconds-codex_seconds):.3f}\n'
        'Detailed per-episode timings: RUNTIME_SUMMARY.csv\n'
    )

    if experiment_id in ('E2', 'E3'):
        summary_name = f'{experiment_id}_READER_SUMMARY.txt'
        title = 'E2 GROUP A - READER SUMMARY' if experiment_id == 'E2' else 'E3 - READER SUMMARY'
        pcfg = active_proposer_configuration()
        reader_parts = [
            title,
            f"Proposer: {pcfg['model']}; reasoning={pcfg['reasoning_effort']}; profile={pcfg['profile']}; paper_replication={'YES' if pcfg['paper_replication'] else 'NO'}",
            ''
        ]
        for r in exp_rows:
            rp = parent / f"R_{r['run_id']}_{r['episode_id']}" / 'READER_DIAGNOSIS.txt'
            if rp.exists():
                reader_parts.append(rp.read_text(encoding='utf-8').strip())
        write_text_exact(parent / summary_name, '\n'.join(reader_parts).rstrip() + '\n')

    z = parent / f'{experiment_id}_AUDIT_BUNDLE.zip'
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(parent.rglob('*')):
            if p.is_file() and p != z:
                zf.write(p, p.relative_to(parent))

    print(f'\n{experiment_id} SUMMARY', flush=True)
    print('-' * 68, flush=True)
    pcfg = active_proposer_configuration()
    print(f"PROPOSER: {pcfg['model']} | reasoning={pcfg['reasoning_effort']} | profile={pcfg['profile']}", flush=True)
    for item in summaries:
        sol = item['solution'] or '-'
        if item['local_outcome'] == 'no_local_solution' and item['construction_status'] == 'construction_proposed':
            detail = 'local=no_local_solution -> construction=construction_proposed'
        else:
            detail = f"local={item['local_outcome']}; construction={item['construction_status']}"
        if experiment_id == 'E2':
            rp = parent / f"R_{item['run_id']}_{item['episode_id']}" / 'READER_DIAGNOSIS.txt'
            print((rp.read_text(encoding='utf-8').strip() if rp.exists() else f"{item['episode_id']}: result unavailable"), flush=True)
        elif experiment_id == 'E3':
            print(item.get('e3_reader_line') or f"{item['episode_id']}: result unavailable", flush=True)
        else:
            print(
                f"{item['episode_id']:<10} SOLUTION {sol:<12} | overall={item['overall_outcome']}",
                flush=True,
            )
            print(f"           {detail}", flush=True)
    print('-' * 68, flush=True)
    print(
        f"RUNTIME TOTAL: wall={total_seconds:.1f}s; "
        f"sum Codex execution={codex_seconds:.1f}s; "
        f"details={parent / 'RUNTIME_SUMMARY.csv'}",
        flush=True,
    )
    if experiment_id in ('E2', 'E3'):
        print('Reader summary:', parent / f'{experiment_id}_READER_SUMMARY.txt', flush=True)
    print('Experiment audit:', z)
    return 5 if experiment_failed else 0


def full():
    # Backward-compatible alias: the historical full curriculum is E1.
    return run_experiment('E1')


def run_all_experiments():
    rc = 0
    for experiment_id in ('E1', 'E2', 'E3'):
        print('\n' + '=' * 68)
        print(f'RUNNING {experiment_id}: {load_experiments()[experiment_id]["title"]}')
        print('=' * 68)
        code = run_experiment(experiment_id)
        if code != 0:
            rc = code
            break
    return rc


def interactive_experiment(experiment_id: str):
    spec = load_experiments()[experiment_id]
    exp_rows = rows_for_experiment(experiment_id)
    while True:
        print('\n' + '=' * 68)
        print(f'{experiment_id} -- {spec.get("title", "")}')
        print(spec.get('description', ''))
        print('-' * 68)
        if not exp_rows:
            print('No tasks are defined for this experiment yet.')
            input('Press Enter to return to the experiment menu...')
            return 0
        for i, r in enumerate(exp_rows, start=1):
            label = r['episode_id']
            if r['episode_id'] != r['task_id']:
                label += f" (task {r['task_id']})"
            print(f'  [{i}] {label}')
        print('  [A] Run complete experiment')
        print('  [B] Back')
        choice = input('Selection: ').strip().upper()
        if choice == 'B':
            return 0
        if choice == 'A':
            return run_experiment(experiment_id)
        if choice.isdigit() and 1 <= int(choice) <= len(exp_rows):
            r = exp_rows[int(choice) - 1]
            post, _, _ = run_one(r['run_id'])
            print(f"Run status: {post['transport_status']}")
            continue
        print('Invalid selection.')


def interactive_menu():
    experiments = load_experiments()
    while True:
        print('\n' + '=' * 68)
        print('P4 LLM-MEDIUM-SOLVER DEMONSTRATION')
        print('=' * 68)
        print(f"  [1] E1  {experiments['E1']['title']}")
        print(f"  [2] E2  {experiments['E2']['title']}")
        pcfg = active_proposer_configuration()
        print(f"Proposer: {pcfg['model']} | reasoning={pcfg['reasoning_effort']} | profile={pcfg['profile']}")
        print('-' * 68)
        print(f"  [3] E3  {experiments['E3']['title']}")
        print('  [A] Run all populated experiments')
        print('  [M] Change proposer model/configuration')
        print('  [Q] Quit')
        choice = input('Selection: ').strip().upper()
        if choice == 'Q':
            return 0
        if choice == 'M':
            select_proposer_configuration_interactive()
            continue
        if choice in ('1', '2', '3'):
            interactive_experiment(f'E{choice}')
            continue
        if choice == 'A':
            return run_all_experiments()
        print('Invalid selection.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--proposer-profile', choices=['PAPER', 'LEGACY'], help='Use a predefined proposer configuration without prompting.')
    ap.add_argument('--model', help='Use a custom Codex model identifier without prompting.')
    ap.add_argument('--reasoning-effort', choices=['none', 'minimal', 'low', 'medium', 'high', 'xhigh'], help='Reasoning effort for --model; defaults to medium.')
    sub = ap.add_subparsers(dest='cmd')
    sub.add_parser('menu')
    sub.add_parser('check')
    sub.add_parser('health')
    one = sub.add_parser('run')
    one.add_argument('--run-id', required=True)
    sub.add_parser('full')
    exp = sub.add_parser('experiment')
    exp.add_argument('--id', required=True, choices=['E1', 'E2', 'E3'])
    exp.add_argument('--run-id')
    sub.add_parser('all-experiments')
    a = ap.parse_args()
    if a.proposer_profile and a.model:
        raise SystemExit('Choose either --proposer-profile or --model, not both.')
    if a.proposer_profile:
        set_proposer_configuration(a.proposer_profile, source='cli_hardcoded')
    elif a.model:
        set_proposer_configuration(model=a.model, reasoning_effort=a.reasoning_effort or 'medium', source='cli_custom')
    elif a.cmd not in ('check',):
        select_proposer_configuration_interactive()
    if a.cmd is None or a.cmd == 'menu':
        return interactive_menu()
    if a.cmd == 'check':
        return 2 if verify_package(True) else 0
    if a.cmd == 'health':
        return health()
    if a.cmd == 'run':
        post, _, _ = run_one(a.run_id)
        return 0 if post['transport_status'] == 'READY_FOR_REVIEW' else 4
    if a.cmd == 'full':
        return full()
    if a.cmd == 'experiment':
        if a.run_id:
            permitted = {r['run_id'] for r in rows_for_experiment(a.id)}
            if a.run_id not in permitted:
                raise SystemExit(f'Run {a.run_id} does not belong to {a.id}')
            post, _, runtime = run_one(a.run_id)
            if post['transport_status'] != 'READY_FOR_REVIEW':
                return 4
            if a.id == 'E2' and runtime.get('e2_test_status') != 'PASS':
                return 5
            if a.id == 'E3' and runtime.get('e3_test_status') != 'PASS':
                return 5
            return 0
        return run_experiment(a.id)
    if a.cmd == 'all-experiments':
        return run_all_experiments()
    return 1


if __name__ == '__main__':
    raise SystemExit('Use runner/run_envelope.py; this module supplies transport only.')
