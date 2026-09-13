"""Mutation tests of the exact wide guest acceptance oracle."""
from pathlib import Path
import copy,json,struct,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import run_qemu_x86_64_program_memory as r

def sample(case,oom=None):
    events=[dict(kind='poison',bytes=270336),dict(kind='boot',catalog=261,scratch=66,reserved=2887,zero=1,aliases=0)]
    blocks=[]
    for run in range(2):
        block=''
        if oom is not None:
            events.extend([dict(kind='oom',owner=(run*4+1)<<32,acquired=oom),
                           dict(kind='rollback',owner=(run*4+1)<<32,acquired=oom,free=1000,before=1000)])
        for n in range(1,5):
            gen=run*4+n;slot=n-1 if n<3 else 2
            mode=case if case<6 and n==3 else 0
            if slot==2:events.extend([dict(kind='copy',gen=gen,bytes=r.SIZE,sha=('a' if n==3 else 'b')*64),dict(kind='create',gen=gen,acquired=55)])
            events.append(dict(kind='start',slot=slot,gen=gen,pages=32,private=12))
            if slot==2:events.append(dict(kind='stack',gen=gen,bytes=12288,checksum=1566720,immutable=1,case=mode))
            if mode in (1,2,3):events.append(dict(kind='fault',gen=gen,vector=14,error={1:6,2:21,3:7}[mode],address={1:0x407fff,2:0x40c000,3:0x410000}[mode]))
            if mode==5:events.append(dict(kind='cancel',gen=gen,state=6))
            events.append(dict(kind='release',slot=slot,gen=gen,frames=17,before=1000,after=1017,fenced=1))
            status=78 if n==1 else 77 if n==2 else 142 if mode in (1,2,3) else 256 if mode==4 else 0 if mode==5 else 80
            state=3 if mode else 4;rip=0x40c000 if mode==2 else 0x410123
            block+='REIST_X86_64_PROCESS_REAP_OK v1='+struct.pack('<4I2Q',slot,gen,status,state,32 if mode==4 else 4,rip).hex().upper()+'\n'
        events.append(dict(kind='finish',run=run+1,free=1000,initial=1000,tasks=4,generation=(run+1)*4))
        blocks.append(block+r.process.DONE+'\n')
    markers=[m for m in r.transport.REQUIRED_MARKERS if 'SHELL' not in m]+[r.process.SUCCESS]
    serial='\n'.join(markers)
    serial=serial.replace('REIST_X86_64_C_KERNEL_CONTROL_OK',''.join(blocks)+'REIST_X86_64_C_KERNEL_CONTROL_OK')
    return serial,events

def trace(events):return '\n'.join('WIDE '+json.dumps(e) for e in events)

class RuntimeTests(unittest.TestCase):
    def test_all_cases_and_missing_duplicate_corrupt_events(self):
        for case in range(7):
            oom=27 if case==6 else None;serial,events=sample(case,oom)
            self.assertEqual(len(r.validate(serial,trace(events),case,oom,55)),8)
            for index in range(len(events)):
                for bad in (events[:index]+events[index+1:],events+[events[index]],list(reversed(events))):
                    with self.assertRaises(ValueError):r.validate(serial,trace(bad),case,oom,55)
            for kind,key,value in (('boot','aliases',1),('boot','zero',0),('copy','bytes',36896),
                ('create','acquired',54),('stack','bytes',4096),('stack','immutable',0),('stack','checksum',0),
                ('release','fenced',0),('release','after',1000),('finish','free',999),('finish','tasks',3)):
                bad=copy.deepcopy(events);next(e for e in bad if e['kind']==kind)[key]=value
                with self.assertRaises(ValueError):r.validate(serial,trace(bad),case,oom,55)
            for bad in (serial+serial,serial.replace(r.process.SUCCESS,''),serial+'\n'+r.transport.FAILURES[0]):
                with self.assertRaises(ValueError):r.validate(bad,trace(events),case,oom,55)
            if case in (1,2,3):
                for key,value in (('vector',13),('error',0),('address',0x411000)):
                    bad=copy.deepcopy(events);next(e for e in bad if e['kind']=='fault')[key]=value
                    with self.assertRaises(ValueError):r.validate(serial,trace(bad),case,oom,55)

    def test_record_count_and_observer_compilation(self):
        record=bytearray(r.SIZE);record[:16]=b'RNPGv2\0\0'+struct.pack('<II',2,r.SIZE)
        record[24:88]=bytes([5]*7+[0,0]+[6]*7+[4]*48)
        self.assertEqual(r.allocations(record),74)
        for offset in (0,8,12,24+7,24+8,24+15):
            bad=record[:];bad[offset]^=1
            with self.assertRaises(ValueError):r.allocations(bad)
        compile(r.OBSERVER,'wide-observer','exec')

if __name__=='__main__':unittest.main()
