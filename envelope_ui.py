"""Interactive launchers. Uses the current Python interpreter and paths relative to this file."""
import json
from pathlib import Path
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'runner'))
from runner import run_envelope as backend


def show_errors(root=None):
    root = Path(root) if root else ROOT
    files = sorted((root / 'runs').glob('V09_*/*/POST_ENVELOPE.json'),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files:
        try:
            post = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if post.get('transport_status') != 'READY_FOR_REVIEW':
            backend.show_execution_error(path.parent, post)
            return
    print('No saved Codex execution failure found under this envelope folder.')


def choose_episode():
    rs = backend.rows()
    print('\nIndividual runs use prepared checkpoints; they are isolated tests.')
    for r in rs:
        print(f"  {r['run_id']:12s} {backend.group(r)}  {r['episode_id']}")
    while True:
        answer = input('Run ID (Enter to cancel): ').strip()
        if not answer:
            return None
        matches = [r for r in rs if r['run_id'].lower() == answer.lower()
                   or r['episode_id'].lower() == answer.lower()]
        if len(matches) == 1:
            return matches[0]
        print('Choose a run ID from the list.')


def run_action(action):
    if action == 'display':
        backend.DISPLAY_MODE='full' if backend.DISPLAY_MODE=='short' else 'short'
        print('Task output:',backend.DISPLAY_MODE)
        return 0
    if action == 'errors':
        show_errors()
        return 0
    if action == 'check':
        return 0 if backend.check() else 2
    if action == 'tests':
        if not backend.check():
            return 2
        return subprocess.run([sys.executable, '-m', 'unittest', 'discover',
                               '-s', str(ROOT / 'tests'), '-v'], cwd=ROOT).returncode
    if not backend.check():
        return 2
    if action == 'one':
        row = choose_episode()
        if row is None:
            return 0
        action = ('episode', backend.group(row), row['run_id'])
    if action == 'model':
        backend.transport.select_proposer_configuration_interactive()
        return 0
    if backend.transport.ACTIVE_PROPOSER_CONFIG is None:
        backend.transport.select_proposer_configuration_interactive()
    if action == 'health':
        return backend.transport.health()
    if isinstance(action, tuple):
        return backend.experiment(action[1], action[2])
    if action == 'all':
        for group in ('E1', 'E2', 'E3'):
            rc = backend.experiment(group)
            if rc:
                return rc
        return 0
    return backend.experiment(action)


def menu():
    options = {'1': 'check', '2': 'tests', '3': 'health', '4': 'E1',
               '5': 'E2', '6': 'E3', '7': 'one', '8': 'all',
               '9': 'errors', 'm': 'model', 'v': 'display'}
    while True:
        print('\nP4 ENVELOPE — interactive Python launcher')
        cfg = backend.transport.ACTIVE_PROPOSER_CONFIG
        print('Model: ' + (f"{cfg['model']} / {cfg['reasoning_effort']}" if cfg else 'select before first model call'))
        print('  1  Check package       2  Run local tests')
        print('  3  Codex health check  4  Full E1 curriculum')
        print('  5  E2 controls         6  Full E3 curriculum')
        print('  7  One episode         8  All experiments')
        print('  9  Show latest error   M  Select/change model')
        print('  V  Toggle short/full task output (current: '+backend.DISPLAY_MODE+')')
        print('  0  Exit')
        choice = input('Choice: ').strip().lower()
        if choice in ('0', 'q', 'exit'):
            return 0
        if choice not in options:
            print('Choose a listed option.')
            continue
        try:
            rc = run_action(options[choice])
            print(f'Finished. Exit code: {rc}')
        except Exception as exc:
            print(f'Failed: {exc}')
            traceback.print_exc()
            print('You can select 9 to inspect a saved execution failure.')


def entry(action=None):
    rc = 0
    try:
        # Main root launcher also accepts the existing command-line arguments.
        if action is None and len(sys.argv) > 1:
            rc = backend.main()
        else:
            rc = menu() if action is None else run_action(action)
    except KeyboardInterrupt:
        print('\nStopped by user.')
        rc = 130
    except Exception as exc:
        print(f'Failed: {exc}')
        traceback.print_exc()
        rc = 1
    if action is not None and sys.stdin.isatty():
        try:
            input('\nPress Enter to close...')
        except (EOFError, KeyboardInterrupt):
            pass
    return rc
