"""Restricted P0 replay and admission. No model-generated code is executed."""
import hashlib
import json
import re
from pathlib import Path

class Invalid(ValueError):
    pass

def require(ok, why):
    if not ok:
        raise Invalid(why)

def lines(text):
    return sorted(set(' '.join(x.split()) for x in text.splitlines()
                      if x.strip() and not x.lstrip().startswith(('#', '%'))))

def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()

class State:
    def __init__(self, ks, task, tid):
        self.ks, self.task, self.tid = ks, task, tid
        self.facts = [x.split() for x in lines(ks + '\n' + task)]
        self.kfacts = [x.split() for x in lines(ks)]
        self.trace = []
    def rows(self, op):
        return [p[1:] for p in self.facts if p[0] == op]
    def q(self, obj, key, persistent=False):
        return sorted(set(' '.join(p[3:]) for p in (self.kfacts if persistent else self.facts)
                          if len(p)>=4 and p[:3] == ['QUALIFY',obj,key]))
    def one(self, obj, key, persistent=False):
        a=self.q(obj,key,persistent);require(len(a)==1, f'{obj}: ambiguous/missing {key}');return a[0]
    def log(self, op, args, result):
        self.trace.append({'op':op, 'args':list(map(str,args)), 'result':str(result)})
        return result
    def supported(self, obj):
        return (self.q(obj,'proposal_source',True)==['true'] and
                self.q(obj,'status',True) in (['supported'],['verified']))
    def schemas(self, key, value, itype=None):
        names=sorted(set(p[1] for p in self.kfacts if p[0] in ('ENTITY','PROCEDURE')))
        return [n for n in names if self.supported(n) and value in self.q(n,key,True)
                and (itype is None or self.q(n,'input_type',True)==[itype])]
    def projections(self):
        out=[]
        for k in (1,2):
            ns=[n for n in self.schemas('formation_kind','positional_projection')
                if self.q(n,'kind',True)==['schema'] and self.q(n,'selected_position',True)==[str(k)]
                and self.q(n,'uses_procedure',True)==['PROJECT']
                and self.q(n,'structure_constructor',True)==['Pair']
                and self.q(n,'structure_arity',True)==['2']]
            require(ns,'missing admitted projection schema');out.append(ns[0])
        return out
    def unknown(self):
        a=[p for p in self.rows('UNKNOWN_AT') if p[0]==self.tid]
        require(len(a)==1,'expected one unknown');return a[0][1:]
    def stream(self,u):
        a=[p for p in self.rows('AT') if p[0]==u]
        require(len({p[1] for p in a})==len(a),'duplicate stream position')
        return {p[1]:p[2] for p in a}
    def pair(self,p):
        a=[v[1:] for v in self.rows('PAIR') if v[0]==p]
        require(len(a)==1,'missing/ambiguous represented pair');return a[0]
    def role(self,u,k):
        return {i:self.pair(v)[k-1] for i,v in self.stream(u).items()}
    def edge(self,r,a,b):
        return any(p[:3]==[a,r,b] for p in self.rows('EDGE'))
    def adjacent(self,u,r,k=0):
        x,us,i,typ=self.unknown();require(us==u,'wrong target stream')
        vals=self.role(u,k) if k else self.stream(u)
        pairs=self.rows('POSITION_NEXT');known=[]
        domain=set()
        for a,rel,b,*_ in self.rows('EDGE'):
            if rel==r:domain.update((a,b))
        for a,b in pairs:
            if b==i and a in vals: known.append(('left',vals[a]))
            if a==i and b in vals: known.append(('right',vals[b]))
        require(known,'no represented POSITION_NEXT neighbour')
        possible=[o for o in sorted(domain) if all(self.edge(r,v,o) if side=='left' else self.edge(r,o,v) for side,v in known)]
        require(len(possible)==1,'nonunique/absent adjacent result')
        v=possible[0]
        filled={**vals,i:v}
        for a,b in pairs:
            if a in filled and b in filled:require(self.edge(r,filled[a],filled[b]),'relation violates givens')
        return self.log('RELATION_COMPLETION',[u,str(k),r],v)
    def residual(self,u,k):
        typ=self.one(u,'type'); refs=[r for r in self.q(self.tid,'input') if r!=u and self.q(r,'type')==[typ]
            and not any(p[2]==r for p in self.rows('UNKNOWN_AT') if p[0]==self.tid)]
        require(len(refs)>=2,'need two complete reference streams')
        domains=[]; n=None
        for r in refs:
            vals=list(self.role(r,k).values())
            require(len(vals)>=2 and len(vals)==len(set(vals)),'reference role not ALL_ONCE')
            if n is None:n=len(vals)
            require(len(vals)==n,'reference lengths differ'); domains.append(set(vals))
        require(all(d==domains[0] for d in domains),'reference domains differ')
        vs=list(self.role(u,k).values());d=domains[0]
        require(len(vs)==n-1 and len(set(vs))==len(vs) and set(vs)<=d,'target not N-1 distinct reference values')
        missing=sorted(d-set(vs));require(len(missing)==1,'residual not unique')
        self.log('REFERENCE_DOMAIN',[u,str(k)]+refs,','.join(sorted(d)))
        return self.log('RESIDUAL',[u,str(k)],missing[0])
    def component_relations(self,u):
        ids=self.q(self.tid,'constraint');out={}
        for p in self.rows('CONSTRAINT'):
            if p[0]=='COMPONENT_RELATION' and p[1] in ids and p[2]==u:
                k=int(p[3]);require(k not in out,'ambiguous component relation');out[k]=p[4]
        return out
    def finish_pair(self,u,cs):
        _,_,_,typ=self.unknown()
        ps=[p for p,a,b in self.rows('PAIR') if [a,b]==cs and self.q(p,'type')==[typ]]
        require(len(ps)==1,'need one represented typed output Pair')
        return self.log('PAIR',cs,ps[0])
    def e1(self,route):
        x,u,i,typ=self.unknown();itype=self.one(u,'type')
        require(u in self.q(self.tid,'input'),'target is not input')
        m=re.fullmatch(r'(F[0134]|CONSTRUCT)\(([^()]*)\)',route)
        require(m,'unsupported route syntax');fam=m[1];a=m[2].split(',')
        if fam=='F0':
            require(len(a)==2 and a[0]==u,'bad F0 arguments');r=a[1]
            require(r in self.q(self.tid,'available_relation'),'relation unavailable')
            require([r,typ,typ] in self.rows('RTYPE'),'relation type mismatch')
            val=self.adjacent(u,r)
        else:
            require(a[:2]==[self.tid,u], 'wrong task/stream in route')
            require(itype=='Stream('+typ+')' and typ.startswith('Pair('),'pair input required')
            require(len(a)==(3 if fam=='F1' else 2),'bad route arity')
            mode=fam
            if fam=='F1':
                h=a[2];require(self.supported(h) and self.q(h,'input_type',True)==[itype], 'unavailable reusable object')
                uses=self.q(h,'uses_procedure',True);pf=self.q(h,'procedure_family',True)
                modes=[v for v in uses if v in ('F0','F3','F4')]+[v for v in pf if v=='stored_componentwise_reuse']
                require(len(modes)==1,'ambiguous reuse mode');mode=modes[0]
                self.log('REUSE',[h],mode)
            rels=self.component_relations(u)
            if mode=='F3':
                cs=[self.residual(u,k) for k in (1,2)]
            elif mode=='F4':
                require(self.schemas('uses_procedure','F3'),'missing learned structural lifting')
                require(set(rels)=={1,2},'F4 needs two component relations')
                cs=[self.relation_role(u,k,rels[k],typ) for k in (1,2)]
            elif mode in ('CONSTRUCT','stored_componentwise_reuse'):
                self.projections();require(len(rels)==1,'mixed route needs exactly one relation')
                if mode=='CONSTRUCT':
                    require(self.schemas('uses_procedure','F3',itype) and self.schemas('uses_procedure','F4',itype),'construction parents absent')
                    require(not self.schemas('procedure_family','stored_componentwise_reuse',itype),'mixed procedure already exists')
                cs=[]
                for k in (1,2):
                    if k in rels:
                        # P0 forbids overlapping finite-reference and relation modes.
                        try:self.residual(u,k)
                        except Invalid:pass
                        else:raise Invalid('ambiguous finite/relation role')
                        cs.append(self.relation_role(u,k,rels[k],typ))
                    else:cs.append(self.residual(u,k))
            else:raise Invalid('runtime mode outside supported pair profile')
            val=self.finish_pair(u,cs)
            for k,r in rels.items():
                # All task component constraints must hold, even for F3/F1.
                require(cs[k-1]==self.relation_role(u,k,r,typ),'component constraint mismatch')
        require(self.q(val,'type')==[typ],'binding type mismatch')
        self.log('BIND',[x],val)
        return {'unknown':x,'value':val}
    def relation_role(self,u,k,r,typ):
        ts=typ[5:-1].split(',');require(k in (1,2),'bad role')
        require([r,ts[k-1],ts[k-1]] in self.rows('RTYPE') and self.q(r,'functional')==['true'],'component relation not typed functional')
        return self.adjacent(u,r,k)

    def e3(self,route):
        form=self.one(self.tid,'e3_form')
        fam={'L2_TO_L':'e3_later_successor_letter','LN_TO_N':'e3_letter_weight',
             'LLN_TO_LN':'e3_common_argument_composition','LNLN_TO_LN':'e3_independent_argument_composition'}[form]
        m=re.fullmatch(r'(E3_REUSE|E3_CONSTRUCT)\(([^,()]+),([^,()]+)\)',route)
        require(m and m[2]==self.tid,'bad E3 route')
        if m[1]=='E3_REUSE':
            require(self.supported(m[3]) and self.q(m[3],'procedure_family',True)==[fam],'missing E3 reusable procedure')
            self.log('REUSE',[m[3]],fam)
        else:
            require(m[3]==fam,'wrong E3 construction family')
            require(not self.schemas('procedure_family',fam),'local reuse available')
        def prim(p):require(['PRIMITIVE',p] in self.kfacts,'missing primitive '+p)
        def nat(n):
            rs=self.rows('NAT_RANGE');require(len(rs)==1,'missing NAT_RANGE')
            n=int(n);require(int(rs[0][0])<=n<=int(rs[0][1]),'outside represented NAT_RANGE');return n
        def hl(a,b):
            def path(start,end):
                path=[start];seen=set()
                while path[-1]!=end and path[-1] not in seen:
                    cur=path[-1];seen.add(cur)
                    ns=[v for aa,r,v,*_ in self.rows('EDGE') if aa==cur and r=='Rseq']
                    if len(ns)!=1:return None
                    path.append(ns[0])
                return path if path[-1]==end else None
            p=path(a,b) or path(b,a);require(p,'letters not ordered by Rseq')
            self.log('REACHABLE',p,p[-1]);last=p[-1]
            ns=[v for aa,r,v,*_ in self.rows('EDGE') if aa==last and r=='Rseq']
            require(len(ns)==1,'no unique represented successor')
            return self.log('Rseq',[last],ns[0])
        def hw(a,n):
            prim('MUL_NAT');n=nat(n)
            vs=[v for aa,r,v,*_ in self.rows('EDGE') if aa==a and r=='Rord']
            require(len(vs)==1,'no unique represented ordinal');w=nat(vs[0])
            self.log('Rord',[a],w)
            return self.log('MUL_NAT',[w,n],nat(w*n))
        def calc(args):
            if form=='L2_TO_L':return hl(*args)
            if form=='LN_TO_N':return str(hw(*args))
            # Composition requires admitted lower-level procedures, even in construction.
            require(self.schemas('procedure_family','e3_later_successor_letter') and
                    self.schemas('procedure_family','e3_letter_weight'),'missing admitted composition parents')
            if form=='LLN_TO_LN':a,b,n=args;n1=n2=n
            else:a,n1,b,n2=args
            l=hl(a,b);v1=hw(a,n1);v2=hw(b,n2);prim('ADD_NAT')
            n=self.log('ADD_NAT',[v1,v2],nat(v1+v2))
            return self.log('LN_TOKEN',[l,n],l+str(n))
        for p in self.rows('E3_EXAMPLE_'+form):
            if form in ('L2_TO_L','LN_TO_N'):args=p[1:-1];expected=p[-1]
            else:args=p[1:-2];expected=p[-2]+p[-1]
            require(calc(args)==expected,'procedure fails example')
            self.log('EXAMPLE',args,expected)
        qs=self.rows('E3_QUERY_'+form);require(len(qs)==1,'missing query')
        q=qs[0];v=calc(q[2:]);self.log('BIND',[q[1]],v)
        return {'unknown':q[1],'value':v}

def replay(ks, task, tid, route):
    s=State(ks,task,tid)
    binding=s.e3(route) if s.q(tid,'profile')==['E3_COMPOSITION'] else s.e1(route)
    return binding,s.trace

def local_routes(ks,task,tid):
    s=State(ks,task,tid)
    if s.q(tid,'profile')==['E3_COMPOSITION']:
        fam={'L2_TO_L':'e3_later_successor_letter','LN_TO_N':'e3_letter_weight','LLN_TO_LN':'e3_common_argument_composition','LNLN_TO_LN':'e3_independent_argument_composition'}[s.one(tid,'e3_form')]
        return [f'E3_REUSE({tid},{h})' for h in s.schemas('procedure_family',fam)]
    _,u,_,_=s.unknown()
    return ([f'F0({u},{r})' for r in s.q(tid,'available_relation')]+[f'F3({tid},{u})',f'F4({tid},{u})']+
            [f'F1({tid},{u},{h})' for h in sorted(set(p[1] for p in s.kfacts if p[0] in ('ENTITY','PROCEDURE'))) if s.supported(h)])

def survivors(ks,task,tid):
    out=[]
    for r in local_routes(ks,task,tid):
        try:b,t=replay(ks,task,tid,r)
        except (Invalid,ValueError,KeyError,IndexError):continue
        out.append((r,b,t))
    return out

def construction_route(ks,task,tid):
    s=State(ks,task,tid)
    if s.q(tid,'profile')==['E3_COMPOSITION']:
        fam={'L2_TO_L':'e3_later_successor_letter','LN_TO_N':'e3_letter_weight','LLN_TO_LN':'e3_common_argument_composition','LNLN_TO_LN':'e3_independent_argument_composition'}[s.one(tid,'e3_form')]
        return f'E3_CONSTRUCT({tid},{fam})'
    return f'CONSTRUCT({tid},{s.unknown()[1]})'

def descriptions(ks,task,tid,route):
    """Exact supported descriptions derived from the checked route, never a checkpoint delta."""
    s=State(ks,task,tid)
    if route.startswith('E3_CONSTRUCT'):
        fam=route[:-1].split(',')[1]
        parents={'e3_later_successor_letter':['Rseq'],'e3_letter_weight':['Rord','MUL_NAT'],
                 'e3_common_argument_composition':['H_L','H_W','ADD_NAT'],
                 'e3_independent_argument_composition':['H_L','H_W','ADD_NAT']}[fam]
        # Resolve actual admitted names rather than hardcoding canonical parents.
        if len(parents)==3:
            parents=[s.schemas('procedure_family','e3_later_successor_letter')[0],s.schemas('procedure_family','e3_letter_weight')[0],'ADD_NAT']
        return [{'kind':'procedure','procedure_family':fam,'parents':parents}]
    if route.startswith('E3_REUSE') or route.startswith('F1'):return []
    x,u,_,typ=s.unknown();base={'input_type':s.one(u,'type'),'output_type':typ}
    fam=route.split('(')[0]
    if fam=='CONSTRUCT':
        return [dict(base,kind='procedure',procedure_family='stored_componentwise_reuse',formation_kind='bounded_component_composition',structure_constructor='Pair',structure_arity='2')]
    if fam=='F3':
        try:s.projections()
        except Invalid:
            return [dict(kind='schema',formation_kind='positional_projection',structure_constructor='Pair',structure_arity='2',selected_position=str(k),uses_procedure='PROJECT') for k in (1,2)]
    extra={}
    if fam=='F0':extra['associated_relation']=route[:-1].split(',')[1]
    if fam=='F3':extra.update(component_mode='all_once',structure_arity='2')
    return [dict(base,kind=k,uses_procedure=fam,**extra) for k in ('rule','schema')]

def serialize_addition(name, desc):
    require(re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',name),'invalid proposed identifier')
    fs=['ENTITY '+name,'QUALIFY '+name+' status '+('verified' if desc['kind']=='rule' else 'supported'),'QUALIFY '+name+' proposal_source true']
    if desc.get('procedure_family','').startswith('e3_'):fs.append('PROCEDURE '+name)
    for k,v in desc.items():
        if k=='parents':
            fs.extend('QUALIFY '+name+' parent '+p for p in v)
        else:fs.append('QUALIFY '+name+' '+k+' '+v)
    return '\n'.join(fs)+'\n'

def evaluate(ks,task,tid,policy,data):
    result={'decision':'REJECT','reason':'','proposal_decisions':[], 'admitted':[], 'ks_after':ks}
    try:
        require(set(data)=={'protocol','task_id','outcome','route','binding','trace','proposals'},'wrong response fields')
        require(data['protocol']=='KS_CHECKED_V09' and data['task_id']==tid,'wrong protocol/task')
        require(isinstance(data['proposals'],list) and isinstance(data['trace'],list),'invalid arrays')
        if data['outcome']=='NO_LOCAL_SOLUTION':
            require(not data['route'] and data['binding']=={'unknown':'','value':''} and not data['trace'] and not data['proposals'],'failure cannot carry solution/proposals')
            require(not survivors(ks,task,tid),'local solution exists')
            if policy['construction_allowed']:
                try:replay(ks,task,tid,construction_route(ks,task,tid))
                except (Invalid,ValueError,KeyError,IndexError):pass
                else:raise Invalid('admissible construction exists; proposer missed it')
            result.update(decision='NO_LOCAL_SOLUTION',reason='verified local failure under episode controls');return result
        require(data['outcome']=='SOLUTION','unknown outcome')
        route=data['route'];construction=route.startswith(('CONSTRUCT(','E3_CONSTRUCT('))
        if construction:
            require(policy['construction_allowed'] and policy['proposal_allowed'],'construction/proposal disabled by experiment')
            require(not survivors(ks,task,tid),'construction before complete local failure')
        expected,trace=replay(ks,task,tid,route)
        require(data['binding']==expected,'binding differs from replay')
        require(data['trace']==trace,'trace differs from deterministic replay')
        allowed=descriptions(ks,task,tid,route)
        require(not data['proposals'] or policy['proposal_allowed'],'insertion proposal disabled by experiment')
        names=set();used=[];delta=[]
        s=State(ks,task,tid)
        occupied={p[1] for p in s.facts if len(p)>1 and p[0] in ('ENTITY','PROCEDURE','PAIR','TYPE')}
        for item in data['proposals']:
            require(set(item)=={'name','description'},'bad proposal fields')
            name=item['name'];desc=item['description']
            require(name not in occupied and name not in names,'proposed identifier already exists');names.add(name)
            require(desc in allowed and desc not in used,'unlicensed or duplicate KS description');used.append(desc)
            addition=serialize_addition(name,desc)
            if policy['insertion_allowed']:
                delta.append(addition);result['admitted'].append(name)
            result['proposal_decisions'].append({'name':name,'admissible':True,'inserted':policy['insertion_allowed']})
        if construction:
            require(used==allowed,'dependent solution needs complete checked construction proposal')
            require(policy['insertion_allowed'],'dependent construction solution requires admission')
        # Ground task facts are observations; persist them only at enabled update episodes.
        after=ks
        if policy['insertion_allowed']:
            after='\n'.join(lines(ks+'\n'+task+'\n'+'\n'.join(delta)))+'\n'
        result.update(decision='ACCEPT',reason='solution path and proposed additions replayed',ks_after=after)
    except (Invalid,ValueError,KeyError,IndexError,TypeError,AttributeError) as exc:
        result.update(decision='REJECT',reason=str(exc),proposal_decisions=[],admitted=[],ks_after=ks)
    return result

def validate_schema(value, spec, path='$'):
    """Small strict validator for the finite schema shipped with v09."""
    typ=spec['type']
    require((typ=='object' and isinstance(value,dict)) or (typ=='array' and isinstance(value,list)) or
            (typ=='string' and isinstance(value,str)),path+': wrong type')
    if 'enum' in spec:require(value in spec['enum'],path+': outside enum')
    if typ=='object':
        require(set(value)==set(spec['required']),path+': missing/extra fields')
        for k,v in value.items():validate_schema(v,spec['properties'][k],path+'.'+k)
    if typ=='array':
        for i,v in enumerate(value):validate_schema(v,spec['items'],path+f'[{i}]')
