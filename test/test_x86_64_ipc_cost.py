"""Exact actual-adapter publication counts, differential behavior and faults."""
from pathlib import Path
import hashlib,os,re,subprocess,sys,unittest,uuid,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs

class IPCCostTests(unittest.TestCase):
    def test_actual_counts_semantics_and_corruption(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83ai-block'/('ipc-cost-'+uuid.uuid4().hex);folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        baseline=subprocess.check_output(['git','show','7f452faf:arch/x86_64/ipc/native_ipc.c'],cwd=ROOT,timeout=10)
        old=folder/'reference.c';old.write_bytes(baseline)
        current=ROOT/'arch/x86_64/ipc/native_ipc.c'
        (folder/'sources.json').write_text(json.dumps({name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in [('reference',old),('candidate',current)]},indent=2))
        def run(command,label):
            r=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,text=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(label+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
            self.assertEqual(r.returncode,0,str(folder)+'\n'+(r.stdout+r.stderr)[-2500:]);return r.stdout
        for opt in ('0','2'):
            transcripts={}
            for name,path in [('reference',old),('candidate',current)]:
                exe=folder/(name+opt+'.exe')
                run([find_zig(),'cc','-std=c11','-Wall','-Wextra','-Werror','-O'+opt,
                     '-DREIST_NATIVE_IPC','-DREIST_NATIVE_IPC_HOST_TEST','-DREIST_HOST_TEST','-DREIST_NATIVE_RUNTIME',
                     '-DIPC_SOURCE="'+path.as_posix()+'"','-I.','-Iarch/x86_64/ipc',
                     'kernel/ipc/ipc.c','kernel/init/critical_object.c','test/x86_64_ipc_cost_host.c','-o',exe],name+opt+'-build')
                transcripts[name]=run([exe],name+opt+'-run')
                self.assertIn('IPC_COST_HOST_OK',transcripts[name])
                for slot in range(4):self.assertIn('IPC_COST_FAULT_OK',run([exe,str(slot)],name+opt+'-fault-'+str(slot)))
            self.assertEqual(re.findall(r'SEMANTICS .*',transcripts['reference']),re.findall(r'SEMANTICS .*',transcripts['candidate']))
            old_rows=re.findall(r'COST (\S+) (\d+) (\d+) (\d+) (\d+)',transcripts['reference'])
            new_rows=re.findall(r'COST (\S+) (\d+) (\d+) (\d+) (\d+)',transcripts['candidate'])
            self.assertEqual(len(old_rows),len(new_rows))
            for old_row,new_row in zip(old_rows,new_rows):
                self.assertEqual(old_row[:2],new_row[:2]) # Full verification count unchanged.
                self.assertEqual(new_row[3],old_row[3]) # Common message allocation may initialize fresh guards.
                label=old_row[0];updates=int(new_row[2])
                if label in ('send','receive'):self.assertEqual(new_row[4],'0',label+' local capabilities are read-only')
                if label=='delegate':self.assertEqual(new_row[4],'2','only target capabilities change')
                expected={'idle':0,'wait-v1':0,'wait-v2':0,'take':5,'empty-take':0,'bind':2,'end':0}
                if label in expected:self.assertEqual(updates,expected[label],label)
                self.assertLessEqual(updates,int(old_row[2]),label)
            print('IPC_COST_EQUIVALENT O'+opt+' '+str(folder),flush=True)

if __name__=='__main__':unittest.main()
