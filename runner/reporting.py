"""Human-readable reporting only: no proposal/admission decisions are made here."""
import json


def task_lines(transport, row, controls, state_hash):
    raw = transport.console_task_block(row)
    # The legacy display labels prepared checkpoints; v09 uses actual runtime state.
    out = [line for line in raw if not line.startswith(('VISIBLE KS:', 'CONSTRUCTION:'))]
    out += ['CONTROLS: ' + ', '.join(f"{k}={'on' if v else 'off'}" for k, v in controls.items()),
            'ACTUAL VISIBLE KS SHA256: ' + state_hash]
    return out


def result_lines(row, data, result):
    data = data if isinstance(data, dict) else {}
    binding = data.get('binding')
    binding = binding if isinstance(binding,dict) else {}
    lines = ['', f"RESULT {row['episode_id']}"]
    if data.get('outcome') == 'SOLUTION':
        lines.append(f"  Proposer answer: {binding.get('unknown', '?')} = {binding.get('value', '?')}")
        lines.append('  Proposed route: ' + str(data.get('route', '')))
    elif data.get('outcome'):
        lines.append('  Proposer outcome: ' + str(data['outcome']))
    else:
        lines.append('  No usable proposer response.')
    lines += ['  KSU: ' + result['decision'], '  Reason: ' + result.get('reason', '')]
    if result['decision'] == 'ACCEPT':
        lines.append('  Solution path: independently checked and accepted.')
    elif result['decision'] == 'NO_LOCAL_SOLUTION':
        lines.append('  No admissible solution under the current episode controls.')
    else:
        lines.append('  No solution accepted for this episode.')
    admitted = result.get('admitted') or []
    lines.append('  Admitted KS elements: ' + (', '.join(admitted) if admitted else 'none'))
    changed = result.get('ks_before_sha256') != result.get('ks_after_sha256')
    lines.append('  Persistent KS: ' + ('updated' if changed else 'unchanged'))
    return lines


def trace_lines(data, result):
    data = data if isinstance(data, dict) else {}
    label = 'CHECKED SOLUTION TRACE' if result['decision'] == 'ACCEPT' else 'PROPOSER TRACE — NOT AN ACCEPTED SOLUTION'
    out = [label]
    trace = data.get('trace')
    if not isinstance(trace, list) or not trace:
        out.append('  (no trace supplied)')
    else:
        for i, step in enumerate(trace, 1):
            if isinstance(step, dict):
                args = step.get('args', [])
                if not isinstance(args,list):args=[repr(args)]
                out.append(f"  {i}. {step.get('op', '?')}({', '.join(map(str,args))}) -> {step.get('result', '?')}")
            else:
                out.append(f'  {i}. {step!r}')
    out.append('\nPROPOSED KS ADDITIONS')
    proposals = data.get('proposals')
    if not isinstance(proposals, list) or not proposals:
        out.append('  none')
    else:
        for item in proposals:
            out.append(json.dumps(item, ensure_ascii=False, indent=2))
    out.append('\nKSU PROPOSAL DECISIONS')
    out.append(json.dumps(result.get('proposal_decisions', []), ensure_ascii=False, indent=2))
    return out


def report(out, row, data, result, mode='short'):
    short = result_lines(row, data, result)
    long = trace_lines(data, result)
    (out / 'MINIMAL_RESULT.txt').write_text('\n'.join(short) + '\n', encoding='utf-8')
    (out / 'FULL_TRACE.txt').write_text('\n'.join(short + [''] + long) + '\n', encoding='utf-8')
    for line in short:
        print(line, flush=True)
    if mode == 'full':
        for line in long:
            print(line, flush=True)
    print('  Full readable trace:', (out / 'FULL_TRACE.txt').resolve(), flush=True)
