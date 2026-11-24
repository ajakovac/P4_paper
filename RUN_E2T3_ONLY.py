"""Interactive Python launcher; run from any working directory."""
from envelope_ui import entry

if __name__ == "__main__":
    raise SystemExit(entry(('episode', 'E1', 'E2T3')))
