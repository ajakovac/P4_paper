import copy
import csv
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'runner'))
import ksu
import run_envelope as runner
ROWS={r['run_id']:r for r in runner.rows()}
YES=dict(construction_allowed=True,proposal_allowed=True,insertion_allowed=True)

def source(rid):
 r=ROWS[rid];return (ROOT/r['ks_file']).read_text(),(ROOT/r['task_file']).read_text(),r['task_id']

def response(ks,task,tid,rid,controls=None):
 controls=controls or runner.policy(ROWS[rid]);ss=ksu.survivors(ks,task,tid)
 if not ss and not controls['construction_allowed']:
  return dict(protocol='KS_CHECKED_V09',task_id=tid,outcome='NO_LOCAL_SOLUTION',route='',binding={'unknown':'','value':''},trace=[],proposals=[])
 route=ss[0][0] if ss else ksu.construction_route(ks,task,tid)
 b,tr=ksu.replay(ks,task,tid,route);ds=ksu.descriptions(ks,task,tid,route) if controls['proposal_allowed'] else []
 return dict(protocol='KS_CHECKED_V09',task_id=tid,outcome='SOLUTION',route=route,binding=b,trace=tr,
             proposals=[{'name':f'Learned_{rid}_{i}','description':d} for i,d in enumerate(ds)])

def padded(d):
 d=copy.deepcopy(d)
 fields=runner.schema()['properties']['proposals']['items']['properties']['description']['properties']
 for p in d['proposals']:
  p['description']={k:p['description'].get(k,[] if k=='parents' else '') for k in fields}
 return d

class CheckedTests(unittest.TestCase):
 def setUp(self):
  self.ks,self.task,self.tid=source('01');self.data=response(self.ks,self.task,self.tid,'01')
 def evaluate(self,d=None,controls=None):return ksu.evaluate(self.ks,self.task,self.tid,controls or YES,d or self.data)
 def reject(self,fn):
  d=copy.deepcopy(self.data);fn(d);r=self.evaluate(d);self.assertEqual(r['decision'],'REJECT');self.assertEqual(r['ks_after'],self.ks);self.assertEqual(r['admitted'],[])
 def test_E1_curriculum_actual_state(self):
  golden=['V4','V1','V2','V6','A1B2','A2B4','A5V7','A3V2',None,'A3V3','A5V2']
  ks=self.ks
  for rid,answer in zip([f'{i:02}' for i in range(1,12)],golden):
   _,task,tid=source(rid);d=response(ks,task,tid,rid);r=runner.gate(ROWS[rid],ks,padded(d))
   self.assertEqual(r['decision'],'NO_LOCAL_SOLUTION' if answer is None else 'ACCEPT',(rid,r))
   if answer:self.assertEqual(d['binding']['value'],answer)
   if rid=='09':self.assertEqual(r['ks_after'],ks)
   ks=r['ks_after']
  self.assertIn('F1(',d['route'])
 def test_E3_curriculum_actual_state(self):
  ks,_,_=source('E3T1')
  for rid,answer in zip(['E3T1','E3T2','E3T3_pre','E3T3_build','E3T3_post','E3T4'],['E','10',None,'D28','D28','C8']):
   _,task,tid=source(rid);d=response(ks,task,tid,rid);r=runner.gate(ROWS[rid],ks,padded(d))
   self.assertEqual(r['decision'],'NO_LOCAL_SOLUTION' if answer is None else 'ACCEPT',(rid,r))
   if answer:self.assertEqual(d['binding']['value'],answer)
   if rid in ('E3T3_pre','E3T3_post'):self.assertEqual(r['ks_after'],ks)
   ks=r['ks_after']
 def test_wrong_answer(self):self.reject(lambda d:d['binding'].update(value='V5'))
 def test_missing_trace(self):self.reject(lambda d:d.update(trace=[]))
 def test_fabricated_trace_step(self):self.reject(lambda d:d['trace'].append({'op':'EXTERNAL','args':[],'result':'V4'}))
 def test_altered_intermediate(self):self.reject(lambda d:d['trace'][0].update(result='V5'))
 def test_wrong_relation(self):self.reject(lambda d:d.update(route='F0(U1,R0)'))
 def test_absent_relation(self):self.reject(lambda d:d.update(route='F0(U1,MAGIC)'))
 def test_unknown_operation(self):self.reject(lambda d:d.update(route='F2(H,H)'))
 def test_invalid_proposal(self):self.reject(lambda d:d['proposals'][0]['description'].update(uses_procedure='EXTERNAL'))
 def test_silent_extra_proposal_field(self):self.reject(lambda d:d['proposals'][0].update(authority='admitted'))
 def test_id_collision(self):self.reject(lambda d:d['proposals'][0].update(name='R1'))
 def test_id_injection(self):self.reject(lambda d:d['proposals'][0].update(name='X\nEDGE V1 MAGIC V5 1'))
 def test_duplicate_proposal(self):self.reject(lambda d:d['proposals'].append(copy.deepcopy(d['proposals'][0])))
 def test_disabled_proposals(self):
  r=self.evaluate(controls=dict(YES,proposal_allowed=False));self.assertEqual(r['decision'],'REJECT');self.assertEqual(r['ks_after'],self.ks)
 def test_disabled_insertion_valid_solution(self):
  r=self.evaluate(controls=dict(YES,insertion_allowed=False));self.assertEqual(r['decision'],'ACCEPT');self.assertEqual(r['ks_after'],self.ks);self.assertTrue(all(not p['inserted'] for p in r['proposal_decisions']))
 def test_false_no_solution(self):
  d=dict(self.data,outcome='NO_LOCAL_SOLUTION',route='',binding={'unknown':'','value':''},trace=[],proposals=[])
  self.assertEqual(self.evaluate(d)['decision'],'REJECT')
 def test_e3_counterexample_rejected(self):
  ks,task,tid=source('E3T3_build');d=response(ks,task,tid,'E3T3_build');d['trace']=[]
  d['proposals'][0]['description']={'kind':'procedure','facts':['NOT A DERIVATION e3_common_argument_composition H_L H_W ADD_NAT']}
  r=ksu.evaluate(ks,task,tid,YES,d);self.assertEqual(r['decision'],'REJECT');self.assertEqual(r['ks_after'],ks)
 def test_e3_missing_parent(self):
  ks,task,tid=source('E3T3_build');d=response(ks,task,tid,'E3T3_build')
  ks='\n'.join(x for x in ks.splitlines() if 'H_L' not in x)
  self.assertEqual(ksu.evaluate(ks,task,tid,YES,d)['decision'],'REJECT')
 def test_e3_wrong_parent_description(self):
  ks,task,tid=source('E3T3_build');d=response(ks,task,tid,'E3T3_build');d['proposals'][0]['description']['parents']=['H_L','H_W','MAGIC']
  self.assertEqual(ksu.evaluate(ks,task,tid,YES,d)['decision'],'REJECT')
 def test_e3_construction_requires_admission(self):
  ks,task,tid=source('E3T3_build');d=response(ks,task,tid,'E3T3_build')
  r=ksu.evaluate(ks,task,tid,dict(YES,insertion_allowed=False),d);self.assertEqual(r['decision'],'REJECT');self.assertEqual(r['ks_after'],ks)
 def test_disabled_construction(self):
  ks,task,tid=source('E3T3_build');d=response(ks,task,tid,'E3T3_build')
  self.assertEqual(ksu.evaluate(ks,task,tid,dict(YES,construction_allowed=False),d)['decision'],'REJECT')
 def test_out_of_range(self):
  ks,task,tid=source('E3T3_build');d=response(ks,task,tid,'E3T3_build');ks=ks.replace('NAT_RANGE 0 30','NAT_RANGE 0 20')
  self.assertEqual(ksu.evaluate(ks,task,tid,YES,d)['decision'],'REJECT')
 def test_successor_boundary(self):
  ks,task,tid=source('E3T1');task=task.replace('E3_QUERY_L2_TO_L E3T1 XE3T1 B D','E3_QUERY_L2_TO_L E3T1 XE3T1 E F')
  # derive directly to avoid relying on query text replacement specifics
  s=ksu.State(ks,task,tid);self.assertFalse(s.edge('Rseq','F','A'))
  task='ENTITY E3T1\nQUALIFY E3T1 profile E3_COMPOSITION\nQUALIFY E3T1 e3_form L2_TO_L\nE3_QUERY_L2_TO_L E3T1 X E F\n'
  with self.assertRaises(ksu.Invalid):ksu.replay(ks,task,tid,'E3_CONSTRUCT(E3T1,e3_later_successor_letter)')
 def test_e2_controls_fixed_state(self):
  for rid in [f'E2T{i}' for i in range(1,8)]:
   ks,task,tid=source(rid);static=runner.static_base_a_check(ROOT/ROWS[rid]['task_file'],tid)
   if static['formal_supported']:d=response(ks,task,tid,rid)
   else:d=dict(protocol='KS_CHECKED_V09',task_id=tid,outcome='NO_LOCAL_SOLUTION',route='',binding={'unknown':'','value':''},trace=[],proposals=[])
   r=runner.gate(ROWS[rid],ks,padded(d));self.assertEqual(r['ks_after'],ks);self.assertEqual(r['admitted'],[])
   if static['formal_supported']:self.assertEqual(r['decision'],'ACCEPT',(rid,r))
 def test_schema_requires_all_fields(self):
  d=padded(self.data);del d['trace'];self.assertEqual(runner.gate(ROWS['01'],self.ks,d)['decision'],'REJECT')
 def test_schema_rejects_extra(self):
  d=padded(self.data);d['external']='hint';self.assertEqual(runner.gate(ROWS['01'],self.ks,d)['decision'],'REJECT')
 def test_schema_rejects_false_array(self):
  d=padded(self.data);d['trace']='pass';self.assertEqual(runner.gate(ROWS['01'],self.ks,d)['decision'],'REJECT')
 def test_schema_accepts_generated_response(self):ksu.validate_schema(padded(self.data),runner.schema())
 def test_no_checkpoint_loading_during_sequence(self):
  calls=[]
  def fake_trial(r,ks,parent):
   calls.append((r['run_id'],ks));task=(ROOT/r['task_file']).read_text();d=response(ks,task,r['task_id'],r['run_id']);z=runner.gate(r,ks,padded(d));return z.pop('ks_after'),z
  import tempfile
  with tempfile.TemporaryDirectory() as td:
   # Redirect runs only; preserve source-file resolution through Path wrapper.
   original=runner.trial
   with patch.object(runner,'trial',side_effect=fake_trial):self.assertEqual(runner.experiment('E1',output_root=Path(td)),0)
  self.assertIn('Learned_10_0',calls[-1][1]);self.assertNotIn('QUALIFY H14 ',calls[-1][1])

if __name__=='__main__':unittest.main()
