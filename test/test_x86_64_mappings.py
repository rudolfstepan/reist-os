"""Native page-table/copy mechanism with strict pre-effect failure checks."""
from pathlib import Path
import os,struct,subprocess,sys,unittest,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs

class MappingTests(unittest.TestCase):
    def test_snapshot_oracle(self):
        from run_qemu_x86_64_mappings import validate_snapshot,validate_sources,NX,DM
        tables=[0x4000000+i*4096 for i in range(4)];source=[0x4010000+i*4096 for i in range(3)]+[0]*5
        flags=[5,4,6]+[0]*5;private=[0,0,0x4020000]+[0]*5;stack=0x4030000
        plan=struct.pack('<4Q8Q8B8Q3Q',*tables,*source,*flags,*private,stack,NX|0x1023,0x2003)
        pt=[[0]*512 for _ in range(4)];pt[0][0]=tables[1]|7;pt[0][256]=NX|0x1023;pt[0][511]=0x2003
        pt[1][0]=tables[2]|7;pt[2][2]=tables[3]|7
        pt[3][:3]=[source[0]|5,source[1]|5|NX,private[2]|7|NX];pt[3][8]=stack|7|NX
        records={f'table{i}':struct.pack('<512Q',*pt[i]) for i in range(4)}
        records.update({f'source{i}':bytes([i+1])*4096 for i in range(3)})
        records.update(private2=records['source2'],stack=bytes(4096),
            ptr=struct.pack('<21Q',*[DM+x if x else 0 for x in tables+source+private+[stack]]))
        sources={i:(flags[i],records[f'source{i}']) for i in range(3)}
        self.assertEqual(validate_snapshot(plan,records),flags);validate_sources(flags,records,sources)
        for offset,value in ((0,0),(40,source[0]),(120,source[2]),(176,0x1023),(184,NX|0x2003),(168,0x08000000)):
            bad=bytearray(plan);struct.pack_into('<Q',bad,offset,value)
            with self.assertRaises(RuntimeError):validate_snapshot(bad,records)
        bad=bytearray(plan);bad[97]=5
        with self.assertRaises(RuntimeError):validate_snapshot(bad,records)
        with self.assertRaises(RuntimeError):validate_snapshot(plan[:-1],records)
        for name in ('table0','table1','table2','table3','ptr','private2','stack'):
            bad=dict(records);b=bytearray(bad[name]);b[-1]^=1;bad[name]=bytes(b)
            with self.assertRaises(RuntimeError):validate_snapshot(plan,bad)
        with self.assertRaises(RuntimeError):validate_snapshot(plan,dict(records,foreign=bytes(4096)))
        for i in range(3):
            bad=dict(records);bad[f'source{i}']=bytes(4096)
            with self.assertRaises(RuntimeError):validate_sources(flags,bad,sources)

    def test_receipt_oracle(self):
        from run_qemu_x86_64_mappings import validate_receipts
        for case in (1,2,3):
            rip=0x401000 if case==3 else 0x400123;error=21 if case==3 else 7
            trace='MAPPING_TABLES generation=40 result=1 if0=1\n';serial=''
            for gen in (41,42):
                trace+=f'MAPPING_TABLES generation={gen} result=1 if0=1\n'
                if case!=1:trace+=f'MAPPING_FAULT generation={gen} vector=14 error={error} cr2=401000 rip={rip:x} cs=33\n'
                kind='EXIT_REAP_OK status=0000004D' if case==1 else 'FAULT_REAP_OK vector=0E'
                serial+=f'REIST_X86_64_CHILD_{kind} generation={gen:02X} parent=01 queued=00 rip={rip:016X}\nREIST_X86_64_RING3_SHELL_RUN_OK\nMAPPING_OK\n'
            validate_receipts(serial,trace,case,rip)
            for bad in (trace+trace,trace.replace('generation=42','generation=41'),trace.replace('result=1','result=0',1),trace.replace('if0=1','if0=0',1)):
                with self.assertRaises(RuntimeError):validate_receipts(serial,bad,case,rip)
            if case!=1:
                for bad in (trace.replace(f'error={error}','error=0',1),trace.replace('cr2=401000','cr2=400000',1),
                            trace.replace('cs=33','cs=8',1),trace.replace('vector=14','vector=6',1),trace.replace('MAPPING_FAULT','MISSING',1)):
                    with self.assertRaises(RuntimeError):validate_receipts(serial,bad,case,rip)
            for bad in (serial+serial,serial.replace('MAPPING_OK','',1),serial.replace('queued=00','queued=01',1),
                        serial.replace('parent=01','parent=00',1),serial.replace(f'{rip:016X}','0000000000000000',1)):
                with self.assertRaises(RuntimeError):validate_receipts(bad,trace,case,rip)

    def test_elf_oracle(self):
        from run_qemu_x86_64_mappings import elf_pages
        data=bytearray(128);data[:6]=b'\x7fELF\x02\x01';struct.pack_into('<Q',data,32,64);struct.pack_into('<HH',data,54,56,1)
        struct.pack_into('<IIQQQQQQ',data,64,1,5,0,0x400000,0,128,4096,4096)
        self.assertEqual(elf_pages(data),{0:(5,bytes(data)+bytes(3968))})
        for offset,fmt,value in ((32,'Q',2**64-1),(56,'H',5),(68,'I',7),(80,'Q',0x408000),
                                 (96,'Q',129),(104,'Q',0x100000),(112,'Q',16)):
            bad=bytearray(data);struct.pack_into('<'+fmt,bad,offset,value)
            with self.assertRaises(RuntimeError):elf_pages(bad)

    def test_shared_integration_and_fixture_exclusion(self):
        source=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        build=source.split('scheduler_build_task64:',1)[1].split('scheduler_build_shell_child_stack64:',1)[0]
        self.assertIn('call scheduler_map_task64',build);self.assertNotIn('share_rx:',build)
        self.assertEqual(build.count('call scheduler_task_frame_alloc64'),3)
        self.assertLess(build.index('call scheduler_map_task64'),build.index('mov qword [r12 + TASK_CR3], rax'))
        core=(ROOT/'arch/x86_64/mm/address_space.asm').read_text()
        for forbidden in ('physical_frame_alloc','physical_frame_free','ELF_IMAGE','TASK_SHELL','X86_64_MAPPING_CASE'):
            self.assertNotIn(forbidden,core)
        self.assertNotIn('call ',core.split('.validated:',1)[1])
        out=ROOT/'build/codex-agent/r83o-mappings'/('excluded-'+uuid.uuid4().hex)
        r=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
            '-OutputDirectory',out.relative_to(ROOT).as_posix(),'-MappingCase','1','-IpcCase','1'],
            cwd=ROOT,capture_output=True,text=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.assertNotEqual(r.returncode,0);self.assertIn('MappingCase is exclusive',r.stdout+r.stderr);self.assertFalse(out.exists())

    def test_host(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83o-mappings'/('host-'+uuid.uuid4().hex);folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(args,label,timeout=90):
            r=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,timeout=timeout,capture_output=True,text=True,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(label+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
            self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-3000:]);return r.stdout
        obj=folder/'address_space.o'
        run(['C:/tools/nasm-3.02/nasm.exe','-f','win64','arch/x86_64/mm/address_space.asm','-o',obj],'assemble')
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone','-fno-sanitize=all',
                '-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument',
                'test/x86_64_mappings_host.c',obj,'-o',exe],opt+'-build')
            self.assertIn('X86_64_MAPPINGS_HOST_OK',run([exe],opt+'-run',10))

if __name__=='__main__':unittest.main()
