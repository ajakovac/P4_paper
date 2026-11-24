import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runner'))
import reporting
import run_envelope as backend
from test_checked import source, response, padded, ROWS

class ReportingTests(unittest.TestCase):
    def test_task_result_and_full_trace_saved(self):
        ks,task,tid=source('01');data=padded(response(ks,task,tid,'01'))
        def fake_request(*args):
            args[-1].mkdir(parents=True)
            return {'transport_status':'READY_FOR_REVIEW'},data,{}
        with tempfile.TemporaryDirectory() as td,patch.object(backend.transport,'execute_request',side_effect=fake_request),contextlib.redirect_stdout(io.StringIO()) as text:
            after,result=backend.trial(ROWS['01'],ks,Path(td))
            self.assertIn('U1 = [V1, V2, V3, ?]',text.getvalue())
            self.assertIn('X1 = V4',text.getvalue())
            self.assertIn('KSU: ACCEPT',text.getvalue())
            self.assertIn('RELATION_COMPLETION',(Path(td)/'01/FULL_TRACE.txt').read_text())
            self.assertTrue((Path(td)/'01/TASK.txt').exists())
            self.assertTrue((Path(td)/'01/MINIMAL_RESULT.txt').exists())
    def test_rejected_trace_is_never_labelled_checked(self):
        s='\n'.join(reporting.trace_lines({'trace':[{'op':'invented','args':[],'result':'V4'}]}, {'decision':'REJECT'}))
        self.assertIn('NOT AN ACCEPTED SOLUTION',s)
        self.assertNotIn('CHECKED SOLUTION TRACE',s)
    def test_full_console_output(self):
        data={'trace':[{'op':'BIND','args':['X1'],'result':'V4'}]}
        result={'decision':'REJECT','reason':'test','admitted':[],'ks_before_sha256':'a','ks_after_sha256':'a'}
        with tempfile.TemporaryDirectory() as td,contextlib.redirect_stdout(io.StringIO()) as text:
            reporting.report(Path(td),ROWS['01'],data,result,'full')
            self.assertIn('BIND(X1) -> V4',text.getvalue())
    def test_malformed_response_still_reported(self):
        data={'outcome':'SOLUTION','binding':'invalid','trace':[{'args':None}]}
        result={'decision':'REJECT','reason':'schema failure','admitted':[]}
        reporting.result_lines(ROWS['01'],data,result)
        reporting.trace_lines(data,result)

if __name__=='__main__':unittest.main()
