import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import envelope_ui as ui

class LauncherTests(unittest.TestCase):
    def test_menu_returns_without_model_call(self):
        with patch('builtins.input',side_effect=['invalid','0']), patch.object(ui.backend.transport,'select_proposer_configuration_interactive') as choose, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ui.menu(),0)
            choose.assert_not_called()
    def test_model_selected_only_once(self):
        with patch.object(ui.backend,'check',return_value=True), patch.object(ui.backend.transport,'ACTIVE_PROPOSER_CONFIG',None),patch.object(ui.backend.transport,'select_proposer_configuration_interactive') as choose:
            self.assertEqual(ui.run_action('model'),0)
            choose.assert_called_once()
    def test_check_does_not_invoke_codex(self):
        with patch.object(ui.backend,'check',return_value=True), patch.object(ui.backend.transport,'execute_request') as invoke:
            self.assertEqual(ui.run_action('check'),0)
            invoke.assert_not_called()
    def test_latest_execution_error_is_visible(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)/'runs/V09_E1_test/01';d.mkdir(parents=True)
            (d/'POST_ENVELOPE.json').write_text(json.dumps({'transport_status':'REJECTED','codex_exit_code':1}))
            (d/'stderr.txt').write_text('test diagnostic: model unavailable')
            out=io.StringIO()
            with contextlib.redirect_stdout(out):ui.show_errors(Path(td))
            self.assertIn('test diagnostic: model unavailable',out.getvalue())
            self.assertIn('Exit code: 1',out.getvalue())

if __name__=='__main__':unittest.main()
