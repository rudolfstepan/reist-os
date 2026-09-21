"""No-guest regressions for the complete BC collector and independent oracles."""
from pathlib import Path
import ast,copy,inspect,struct,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import run_qemu_x86_64_app_files as run

def request(op=0,sequence=1,offset=0,count=0):
    bound=op!=0
    return struct.pack('<4I5Qi3IQ',1,512,op,0,1 if bound else 0,4,3 if bound else 0,
        sequence,1500 if bound else 0,0,0,offset,count,0)+bytes(432)

FILES={name:(run.media.DATA if name=='data.txt' else (name.encode()*50)) for name in run.media.NAMES}

def object_events():
    events=[];receipts={}
    def bulk(raw):return (struct.pack('<3I',2,2060,len(raw))+raw.ljust(2048,b'\0')).hex()
    for number,root,child,ep in ((1,1,4,10),(2,11,14,20)):
        events.append(dict(kind='start',gen=root,slot=0,run=number,now=0))
        def returned(op,args,before='',after='',result=0,now=100):
            row=dict(kind='return',gen=root,slot=0,run=number,op=op,args=args,before=before,after=after,
                result=result,entered=now,now=now,profile_denied=False)
            events.append(row);return row
        def fs(op,path,offset=0,count=0,sequence=1):
            q=bytearray(512);path=path.encode();struct.pack_into('<6I',q,0,1,512,op,0,len(path),0)
            if op==6:struct.pack_into('<2I',q,24,offset,count)
            at={5:24,6:36}[op];q[at:at+len(path)]=path
            header=struct.pack('<4I4QIiQ',1,64,op,0,((root+2)<<32)|3,sequence,1000,0,512,0,0)
            events.append(dict(kind='call',gen=root,op=53,profile_denied=False,before=bulk(header+q),entered=0))
            status,answer=run.fs_expected_response(bytes(q),2,FILES)
            h=struct.pack('<4I4QIiQ',1,64,op,1,((root+2)<<32)|3,sequence,1000,0,len(answer),status,0)
            returned(54,[90,0,1000],after=bulk(h+answer),now=50)
        fs(5,'/cat.prg',sequence=1);fs(5,'/data.txt',sequence=2)
        fs(6,'/data.txt',count=len(FILES['data.txt']),sequence=3)
        fs(6,'/data.txt',offset=len(FILES['data.txt']),count=1,sequence=4)
        for endpoint in (ep,ep+1):returned(49,[0],after=struct.pack('<I',endpoint).hex())
        returned(132,[0],result=(child<<32)|4)
        mask=sum(1<<n for n in (4,5,6,9,15,20,22,40,41,42,50,51,53,54,58))
        events.append(dict(kind='start',gen=child,slot=4,run=number,now=100,
            args=['cat.prg','/data.txt','@af1:%08x'%ep,'@af1:%08x'%(ep+1)],
            profile=struct.pack('<4Q',child,mask,1<<63,0).hex()))
        returned(55,[ep,child,1]);returned(55,[ep+1,child,2])
        for sequence,(op,offset,count) in enumerate(((0,0,0),(1,0,0),(2,0,256),(2,len(FILES['data.txt']),1),(4,0,0)),1):
            q=struct.pack('<4I5Qi3IQ',1,512,op,0,root if op else 0,child,1 if op else 0,
                sequence,1100 if op else 0,0,0,offset,count,0)+bytes(432)
            answer=run.expected_reply(q,root,child,1,1100,sequence,2,FILES,'data.txt')
            returned(54,[ep,0,1000],after=bulk(q));returned(53,[ep+1,0,1000],before=bulk(answer))
        returned(52,[ep]);returned(52,[ep+1]);receipts[child]=dict(ticks=0)
    return events,receipts

class RuntimeTests(unittest.TestCase):
    def test_budget_error_exit_requires_eighty_replies_and_rejected_81(self):
        spec=('request-budget',0,2,4096,(8,));start=dict(gen=7,run=1,slot=4,parent=1<<32,
            args=['probe.prg','/data.txt','@af1:00000105','@af1:00000106'])
        def bulk(sequence,reply):
            q=struct.pack('<4I5Qi3IQ',1,512,1,int(reply),1,7,1,sequence,4650,0,0,0,0,0)+bytes(432)
            return (struct.pack('<3I',2,2060,512)+q+bytes(1536)).hex()
        events=[dict(kind='return',gen=7,op=54,args=[262],result=0,after=bulk(n,True)) for n in range(1,81)]
        events += [dict(kind='call',gen=1,op=52,args=[261]),
            dict(kind='return',gen=7,op=53,args=[261],result=-9,before=bulk(81,False)),
            dict(kind='call',gen=7,op=9,args=[1,0,0,0,0,0])]
        receipts={7:dict(status=1,state=4)}
        self.assertEqual(run.qualified_outcome(spec,start,[start],events,receipts),(1,4))
        for n in (0,79,80,81,82):
            with self.assertRaises(ValueError):run.qualified_outcome(spec,start,[start],events[:n]+events[n+1:],receipts)
        bad=copy.deepcopy(events);bad[81]['before']=bulk(71,False)
        with self.assertRaises(ValueError):run.qualified_outcome(spec,start,[start],bad,receipts)
        with self.assertRaises(ValueError):run.qualified_outcome(spec,start,[start],events,{7:dict(status=256,state=3)})

    def test_budget_queued_81_is_never_a_broker_operation(self):
        spec=('request-budget',0,2,4096,(8,));start=dict(gen=7,run=1,slot=4,parent=1<<32,
            args=['probe.prg','/data.txt','@af1:00000105','@af1:00000106'])
        def bulk(sequence,reply):
            q=struct.pack('<4I5Qi3IQ',1,512,1,int(reply),1,7,1,sequence,4650,0,0,0,0,0)+bytes(432)
            return (struct.pack('<3I',2,2060,512)+q+bytes(1536)).hex()
        events=[]
        for n in range(1,81):
            events += [dict(kind='return',gen=1,op=54,args=[261],result=0),
                dict(kind='return',gen=1,op=53,args=[262],result=0),
                dict(kind='return',gen=7,op=54,args=[262],result=0,after=bulk(n,True))]
        events += [dict(kind='return',gen=7,op=53,args=[261],result=0,before=bulk(81,False),entered=4020,now=4020),
            dict(kind='call',gen=1,op=52,args=[261]),
            dict(kind='return',gen=1,op=52,args=[261],result=0,now=4020),
            dict(kind='call',gen=7,op=9,args=[1,0,0,0,0,0]),
            dict(kind='call',gen=1,op=52,args=[262]),
            dict(kind='return',gen=1,op=52,args=[262],result=0,now=4020)]
        receipts={7:dict(status=1,state=4)}
        self.assertEqual(run.qualified_outcome(spec,start,[start],events,receipts),(1,4))
        bad_cases=[]
        for n in (0,1,2,239,240,241,242,243,244,245):bad_cases.append(events[:n]+events[n+1:])
        for extra in (dict(kind='return',gen=1,op=54,args=[261],result=0),
                      dict(kind='return',gen=1,op=53,args=[262],result=0)):
            bad_cases.append(events+[extra])
        bad=copy.deepcopy(events);bad[240]['before']=bulk(82,False);bad_cases.append(bad)
        bad=copy.deepcopy(events);bad[240]['result']=-32;bad_cases.append(bad)
        bad=copy.deepcopy(events);bad[240]['now']=4650;bad_cases.append(bad)
        bad=copy.deepcopy(events);bad[242]['result']=-9;bad_cases.append(bad)
        bad=copy.deepcopy(events);bad[239],bad[240]=bad[240],bad[239];bad_cases.append(bad)
        for n,bad in enumerate(bad_cases):
            with self.assertRaises(ValueError,msg=str(n)):run.qualified_outcome(spec,start,[start],bad,receipts)
        with self.assertRaises(ValueError):run.qualified_outcome(spec,start,[start],events,{7:dict(status=0,state=4)})

    def test_budget_wire_client_actual_broker_and_unchanged_default(self):
        import subprocess
        from verify_x86_64_shell_session import disabled
        path='arch/x86_64/user/app_files_probe.c'
        original=(ROOT/'build/codex-agent/r83bc-application-files/candidate04/sources'/path)
        # The inherited source is archived in the original transaction.
        if not original.exists():original=ROOT/'build/codex-agent/r83bc-application-files/candidate01/sources'/path
        self.assertEqual(disabled((ROOT/path).read_text(encoding='utf-8'),'REIST_APP_BUDGET_CLIENT',False),
            original.read_text(encoding='utf-8'))
        source=r'''
#include <stdlib.h>
#include <string.h>
#define REIST_APP_HOST_TEST 1
#define REIST_APP_BUDGET_CLIENT 1
#define main __real_main
#include "arch/x86_64/user/app_files_probe.c"
#undef main
static reist_app_snapshot snapshot;
static reist_app_grant grant;
static reist_app_frame reply;
static unsigned sent,received,closed;
int64_t app_host_call(unsigned op,uint64_t a,uint64_t b,uint64_t c) {
    if(op==REIST_X64_SYS_MONOTONIC_MS)return 100;
    if(!c || c>1000)abort();
    x86os_ipc_bulk_message_t *m=(void*)(uintptr_t)b;
    if(op==REIST_X64_SYS_IPC_SEND_TIMEOUT) {
        if(a!=17 || m->version!=2 || m->struct_size!=2060 || m->length!=512)abort();
        ++sent;if(closed)return -9;
        reist_app_frame q;memcpy(&q,m->payload,512);
        return reist_app_dispatch(&grant,&snapshot,&q,&reply,100);
    }
    if(op!=REIST_X64_SYS_IPC_RECEIVE_TIMEOUT || a!=18 || closed)abort();
    if(sent>=3 && (b&4095))abort();
    if(sent>=4) {
        reist_app_frame old;memcpy(&old,m->payload,512);
        if(m->version!=2 || m->struct_size!=2060 || m->length!=2048 ||
           old.sequence!=sent-1 || old.flags!=1 || old.length!=276)abort();
    }
    memset(m,0,sizeof(*m));m->version=2;m->struct_size=2060;m->length=512;
    memcpy(m->payload,&reply,512);++received;if(received==80)closed=1;return 0;
}
int main(void) {
    snapshot.info.type=X86OS_FILE;snapshot.info.size=snapshot.length=5;
    memcpy(snapshot.info.name,"data.txt",9);memcpy(snapshot.bytes,"DATA\n",5);
    if(reist_app_grant_init(&grant,&snapshot,1,7,1,100))return 1;
    app_child=7;app_request=17;app_reply=18;app_previous=100;app_end=1100;
    memcpy(app_path,"/data.txt",10);reist_app_frame hello;
    if(transact(REIST_APP_HELLO,0,0,1000,&hello))return 2;
    reist_app_probe_selection[2]=8;char *args[]={"probe.prg","/data.txt",0};
    if(__real_main(2,args)!=36 || sent!=81 || received!=80 || grant.sequence!=80 ||
        app_sequence!=80 || app_end!=1100 || grant.deadline!=1100)return 3;
    return 0;
}
'''
        parent=ROOT/'build/codex-agent/r83bc-application-files/development'
        parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as folder:
            exe=Path(folder)/'budget-host.exe'
            result=subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-I.',
                '-Iuserspace/sdk/include','-Iuserspace/storage/include','-xc','-',
                'userspace/sdk/lib/x86_64/app_files.c','-o',str(exe)],input=source.encode(),
                cwd=ROOT,capture_output=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
            self.assertEqual(subprocess.run([str(exe)],timeout=5).returncode,0)

    def test_hang_selfexit_needs_expired_broker_and_blocked_client(self):
        spec=('hang',0,2,4096,(6,));start=dict(gen=7,run=1,slot=4,parent=1<<32,
            args=['probe.prg','/data.txt','@af1:00000105','@af1:00000106'])
        q=struct.pack('<4I5Qi3IQ',1,512,0,1,1,7,1,1,4650,0,276,0,0,0)+bytes(432)
        bulk=(struct.pack('<3I',2,2060,512)+q+bytes(1536)).hex()
        events=[dict(kind='return',gen=1,op=53,args=[262,0,970],result=0,before=bulk,now=3680),
            dict(kind='return',gen=1,op=54,args=[261,0,950],result=-110,entered=3700,now=4650),
            dict(kind='call',gen=1,op=52,args=[261],entered=4650),
            dict(kind='call',gen=1,op=52,args=[262],entered=4650),
            dict(kind='return',gen=7,op=54,args=[262,0,1000],result=-32,entered=3700,now=4650),
            dict(kind='call',gen=7,op=9,args=[1,0,0,0,0,0],entered=4660)]
        receipts={7:dict(status=1,state=4)}
        self.assertEqual(run.qualified_outcome(spec,start,[start],events,receipts),(1,4))
        for n in range(len(events)):
            with self.assertRaises(ValueError):run.qualified_outcome(spec,start,[start],events[:n]+events[n+1:],receipts)
        for n,key,value in ((1,'result',0),(1,'now',4649),(4,'entered',4650),(4,'result',0),(5,'entered',4649)):
            bad=copy.deepcopy(events);bad[n][key]=value
            with self.assertRaises(ValueError):run.qualified_outcome(spec,start,[start],bad,receipts)

    def test_revocation_selfexit_needs_actual_closed_channel_chain(self):
        spec=('authority',0,2,4096,(2,));start=dict(gen=10,run=1,slot=4,parent=1<<32,
            args=['probe.prg','/data.txt','@af1:00000205','@af1:00000206'])
        q=struct.pack('<4I5Qi3IQ',1,512,4,0,1,10,2,3,8300,0,0,0,0,0)+bytes(432)
        close=(struct.pack('<3I',2,2060,512)+q+bytes(1536)).hex()
        events=[dict(kind='call',gen=1,op=52,args=[0x205]),dict(kind='call',gen=1,op=52,args=[0x206]),
            dict(kind='return',gen=10,op=54,args=[0x206],result=-32),
            dict(kind='return',gen=10,op=53,args=[0x205],result=-9,before=close),
            dict(kind='call',gen=10,op=9,args=[1,0,0,0,0,0])]
        receipts={10:dict(status=1,state=4)}
        self.assertEqual(run.qualified_outcome(spec,start,[start],events,receipts),(1,4))
        for n in range(len(events)):
            with self.assertRaises(ValueError):run.qualified_outcome(spec,start,[start],events[:n]+events[n+1:],receipts)
        bad=copy.deepcopy(events);bad[2]['result']=0
        with self.assertRaises(ValueError):run.qualified_outcome(spec,start,[start],bad,receipts)
        with self.assertRaises(ValueError):run.qualified_outcome(spec,start,[start],events,{10:dict(status=0,state=4)})

    def test_relative_timeout_uses_pre_entry_clock_sample(self):
        # A timer interrupt may occur between userspace CLOCK and SYSCALL.
        # No slack is added: recover the sample from the unchanged absolute end
        # and demand that it lies after the preceding completed root operation.
        self.assertTrue(run.relative_deadline(3570,960,2610,2620,2620))
        for values in ((3570,961,2610,2620,2620),(3570,949,2610,2620,2620),
                       (3570,960,2610,2620,3570),(3570,1001,2500,2620,2620)):
            with self.assertRaises(ValueError):run.relative_deadline(*values)

    def test_object_lifecycle_oracle_and_mutations(self):
        events,receipts=object_events();config=dict(app_case='ext2-1k')
        self.assertEqual(run.validate_objects(events,receipts,2,FILES,config),10)
        mutations=[]
        for op in (49,52,55):
            value=copy.deepcopy(events);row=next(r for r in value if r['kind']=='return' and r['op']==op)
            row['result']=-13;mutations.append(value)
        # Wrong reply content, enlarged end, duplicate sequence: no acceptance.
        for byte in (12+80,12+48,12+40):
            value=copy.deepcopy(events);row=next(r for r in value if r['kind']=='return' and r['op']==53)
            raw=bytearray.fromhex(row['before']);raw[byte]^=1;row['before']=raw.hex();mutations.append(value)
        value=copy.deepcopy(events)
        eof=next(r for r in value if r['kind']=='return' and r['op']==54 and len(bytes.fromhex(r['after']))==2060 and
            struct.unpack_from('<I',bytes.fromhex(r['after']),8)[0]==576 and
            struct.unpack_from('<I',bytes.fromhex(r['after']),12+64+8)[0]==6 and
            struct.unpack_from('<I',bytes.fromhex(r['after']),12+64+32)[0]==0)
        value.remove(eof);mutations.append(value)
        for n,value in enumerate(mutations):
            with self.assertRaises(ValueError,msg=str(n)):run.validate_objects(value,receipts,2,FILES,config)

    def test_exact_matrix_and_plans(self):
        self.assertEqual(run.case_order(),run.CASES)
        self.assertEqual(run.case_order(True),(run.CASES[-1],)+run.CASES[:-1])
        self.assertEqual(set(run.case_order(True)),set(run.CASES))
        self.assertEqual(run.case_order(True)[0][0],'request-budget')
        with self.assertRaises(ValueError):run.case_order(1)
        self.assertEqual(len(run.CASES),16);self.assertEqual(len({s[0] for s in run.CASES}),16)
        self.assertEqual(tuple(s[2] for s in run.CASES[:5]),tuple(range(5)))
        self.assertEqual(sum(s[3]==8192 for s in run.CASES),1)
        self.assertEqual(set(m for s in run.CASES for m in s[4]),set(range(1,9)))
        for label,*_ in run.CASES:
            plan=run.input_plan(label);module=run.namespace(label)
            self.assertEqual(module.admitted_plan(plan),plan)
            self.assertEqual(len(plan),2)
            self.assertTrue(all(data.endswith(b'exit\n') or label=='owner-loss' for _,data in plan[0]))
            self.assertLessEqual(sum(sum((len(command)+7)//8 for command in data.splitlines(keepends=True)) for part in plan for _,data in part),64)
            with self.assertRaises(ValueError):module.admitted_plan((((False,b'exit\n'),),plan[1]))
            with self.assertRaises(ValueError):module.admitted_plan((((0,b'format\n'),),plan[1]))
        with self.assertRaises(ValueError):run.input_plan('unknown')

    def test_preserved_predicates_and_private_namespace(self):
        old=run.wide.namespace();module=run.namespace('fat12')
        for name in ('validate_cpu','validate_image_start','validate_identity','validate_terminal',
                     'validate_ipc_delivery','validate_policy','validate_pio_records','validate_probe_steps'):
            self.assertEqual(ast.dump(ast.parse(inspect.getsource(getattr(module,name)))),
                ast.dump(ast.parse(inspect.getsource(getattr(old,name)))),name)
        self.assertIsNot(module.file,old.file)
        self.assertIsNot(module.file.media,old.file.media)
        self.assertNotEqual(module.input_plan(0),old.input_plan(0))
        source=inspect.getsource(module.validate_capture)
        self.assertIn('validate_objects(combined,receipts,layout,app,config)',source)
        self.assertIn('entry_record(row,raw,records)',source)
        self.assertIn('raw.finish()',source)

    def test_full_observer_compiles_without_starting_guest(self):
        # Use real accepted symbol/config inventory, synthetic distinct expected
        # tool bytes. No executable is run or new kernel artifact produced.
        image=ROOT/'build/codex-agent/r83ba-wide-file/wide-pacing/x86_64/reist-x86_64-bootstrap.elf'
        old=run.wide.namespace();config,records,_=old.image_config(image)
        for n in (5,6,7):
            value=bytearray(records[4]);value[96+n]^=n;records[n]=bytes(value)
        config.update(app_probe=0x430000,probe_modes=(1,2,3,4),app_case='authority')
        parent=ROOT/'build/codex-agent/r83bc-application-files/development';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temp:
            module=run.namespace('authority')
            code=module.observer(config,records,Path(temp),0,2)
            body=code.split('\npython\n',1)[1].rsplit('\nend\n',1)[0]
            compile(body,'<BC full emitted observer>','exec')
            self.assertIn("emit('app_selection'",body)
            self.assertIn('record[:262240]==r[:262240]',body)
            self.assertEqual(len(list(Path(temp).glob('prepared-*.bin'))),6)
            capture=module.stepped_capture_namespace(1)
            self.assertTrue(callable(capture['capture']))

    def test_wire_oracle_and_every_request_byte_mutation(self):
        def reply(q,**kw):return run.expected_reply(q,1,4,3,1500,kw.get('sequence',1),2,FILES,kw.get('operand','data.txt'))
        q=request();h,payload=run.frame(reply(q));self.assertEqual(payload,run.info(2,'data.txt',FILES))
        self.assertEqual(h[4:9],(1,4,3,1,1500))
        for n in range(512):
            changed=bytearray(q);changed[n]^=1
            with self.assertRaises(ValueError,msg=str(n)):reply(bytes(changed))
        for op in (1,4):
            h,data=run.frame(reply(request(op,2),sequence=2))
            self.assertEqual(len(data),276 if op==1 else 0)
        h,data=run.frame(reply(request(2,2,0,256),sequence=2));self.assertEqual(data,FILES['data.txt'])
        h,data=run.frame(reply(request(2,2,len(FILES['data.txt']),1),sequence=2));self.assertEqual(data,b'')
        for q in (request(2,2,0,257),request(2,2,999,1),request(4,2,1,0),request(8,2)):
            with self.assertRaises(ValueError):reply(q,sequence=2)
        for n,name in enumerate(run.media.NAMES):
            h,data=run.frame(reply(request(3,2,n),sequence=2,operand='/'))
            self.assertEqual(h[9],1);self.assertEqual(data,run.info(2,name,FILES))
        h,data=run.frame(reply(request(3,2,5),sequence=2,operand='/'));self.assertEqual((h[9],data),(0,b''))
        with self.assertRaises(ValueError):reply(request(3,2,6),sequence=2,operand='/')

    def test_fs_oracle_all_layouts_and_true_eof(self):
        def fsq(op,path,index=0,count=0):
            raw=bytearray(512);path=path.encode();struct.pack_into('<6I',raw,0,1,512,op,0,len(path),0)
            if op==6:struct.pack_into('<2I',raw,24,index,count)
            elif op==7:struct.pack_into('<I',raw,24,index)
            at={5:24,6:36,7:28}[op];raw[at:at+len(path)]=path;return bytes(raw)
        for layout in range(5):
            for name in run.media.NAMES:
                status,data=run.fs_expected_response(fsq(5,'/'+name),layout,FILES)
                self.assertEqual((status,data[216:492]),(0,run.info(layout,name,FILES)))
                status,data=run.fs_expected_response(fsq(6,'/'+name,0,256),layout,FILES)
                count=struct.unpack_from('<I',data,32)[0];self.assertEqual(data[228:228+count],FILES[name][:256])
                self.assertEqual(run.fs_expected_response(fsq(7,'/'+name),layout,FILES),(-20,b''))
            for n,name in enumerate(run.media.NAMES):
                status,data=run.fs_expected_response(fsq(7,'/',n),layout,FILES)
                self.assertEqual((status,data[220:496]),(0,run.info(layout,name,FILES)))
            self.assertEqual(run.fs_expected_response(fsq(7,'/',5),layout,FILES)[0],1)
            self.assertEqual(run.fs_expected_response(fsq(6,'/',0,1),layout,FILES),(-21,b''))
            self.assertEqual(run.fs_expected_response(fsq(5,'/missing'),layout,FILES),(-2,b''))

    def test_no_unknown_executable_or_unbound_selection(self):
        records={n:bytes([n])*266336 for n in range(2,8)}
        self.assertEqual(run.matching_record(4,records[5],records),records[5])
        with self.assertRaises(ValueError):run.matching_record(4,bytes(266336),records)
        row=dict(slot=4,args=['cat.prg'])
        self.assertEqual(run.entry_record(row,None,records),records[5])
        with self.assertRaises(ValueError):run.entry_record(dict(slot=4,args=['unknown.prg']),None,records)
        with self.assertRaises(ValueError):run.validate_probe_selection(dict(gen=4),{},set(),{})

if __name__=='__main__':unittest.main()
