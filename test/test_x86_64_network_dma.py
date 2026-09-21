from pathlib import Path
import os,subprocess,sys,unittest,uuid,json,shutil,hashlib,struct
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_sdk import find_zig
class NetworkDMA(unittest.TestCase):
    def test_actual_raw_replay_and_mutations(self):
        import run_qemu_x86_64_network_dma as guest
        base=ROOT/'build/codex-agent/r83bj-network-dma';image=base/'build03/x86_64/reist-x86_64-bootstrap.elf'
        source=base/'diagnostic10';self.assertEqual(guest.review(image,source,guest.CASES[0])['packets'],4)
        for kind,offset,value in (('dma',0,1),('state',24,0),('witness',40,63),('tasks',2*1024+8,99),('cpu',2*32+8,33)):
            folder=base/('mutated-'+uuid.uuid4().hex);shutil.copytree(source,folder)
            config=json.loads((folder/'config.json').read_text());config['folder']=folder.as_posix();(folder/'config.json').write_text(json.dumps(config),encoding='utf-8')
            trace=(folder/'frame-trace.log').read_text();lines=trace.splitlines()
            for i,line in enumerate(lines):
                if not line.startswith('NETWORK '):continue
                event=json.loads(line[8:])
                if event['kind']!='terminal' or event['slot']!=2:continue
                item=event['raw'][kind];p=folder/item['file'];raw=bytearray(p.read_bytes());struct.pack_into('<Q',raw,offset,value);p.write_bytes(raw)
                item['sha256']=hashlib.sha256(raw).hexdigest();lines[i]='NETWORK '+json.dumps(event);break
            (folder/'frame-trace.log').write_text('\n'.join(lines)+'\n',encoding='utf-8')
            with self.assertRaises(ValueError,msg=kind):guest.review(image,folder,guest.CASES[0])
    def test_parent_fence_precedes_dependent_reap(self):
        import run_qemu_x86_64_network_dma as guest
        base=ROOT/'build/codex-agent/r83bj-network-dma';image=base/'build03/x86_64/reist-x86_64-bootstrap.elf'
        source=base/'candidate01/guests/parent-crash'
        self.assertEqual(guest.review(image,source,guest.CASES[5])['children'],3)
        folder=base/('parent-mutated-'+uuid.uuid4().hex);shutil.copytree(source,folder)
        config=json.loads((folder/'config.json').read_text());config['folder']=folder.as_posix();(folder/'config.json').write_text(json.dumps(config),encoding='utf-8')
        serial=(folder/'guest.log').read_text();lines=serial.splitlines();indices=[i for i,l in enumerate(lines) if 'PROCESS_REAP_OK' in l]
        a,b=indices[1:3];lines[a],lines[b]=lines[b],lines[a];(folder/'guest.log').write_text('\n'.join(lines)+'\n',encoding='ascii')
        with self.assertRaisesRegex(ValueError,'reap ordering'):guest.review(image,folder,guest.CASES[5])
    def test_rx_uses_bulk_write_permission(self):
        source=(ROOT/'arch/x86_64/devices/network_domain.inc').read_text(encoding='utf-8')
        self.assertIn('mov ecx,PF_W\n    call scheduler_validate_shell_range64',source)
        self.assertNotIn('PF_R|PF_W',source)
    def test_linked_entry_sections(self):
        from verify_x86_64_network_dma import EVIDENCE,BUILD
        image=EVIDENCE/('build'+BUILD)/'x86_64/reist-x86_64-bootstrap.elf'
        rows=[line.split() for line in subprocess.check_output(['nm',str(image)],text=True,timeout=10).splitlines()]
        entries=[r for r in rows if len(r)==3 and r[2].startswith('native_network_') and r[2].endswith('64')]
        self.assertGreaterEqual(len(entries),6)
        self.assertTrue(all(r[1].lower()=='t' for r in entries),entries)
    def test_freestanding_consumers(self):
        from unittest.mock import patch
        from build_x86_64_boot_programs import build
        out=ROOT/'build/codex-agent/r83bj-network-dma'/('programs-host-'+uuid.uuid4().hex);out.mkdir(parents=True)
        zig=str(find_zig());env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(out/'cache')
        with patch.dict(os.environ,env):
            build(out,[zig,'cc'],['C:/tools/nasm-3.02/nasm.exe'],[zig,'ld.lld'],0,
                family=True,startup=True,import_image=True,wide=True,task_pool=True,network_dma=True)
        cmd=[zig,'cc','-target','x86_64-freestanding-none','-std=c11','-Oz','-Wall','-Wextra','-Werror',
            '-Wno-unused-command-line-argument','-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector',
            '-mno-red-zone','-mno-mmx','-mno-sse','-mno-sse2','-I.','-DREIST_NATIVE_NETWORK_DMA=1',
            '-c','arch/x86_64/devices/network_dma.c','-o',str(out/'network.o')]
        r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,timeout=120);self.assertEqual(r.returncode,0,r.stderr.decode(errors='replace')[-1500:])
    def test_actual_core(self):
        out=ROOT/'build/codex-agent/r83bj-network-dma'/('host-'+uuid.uuid4().hex);out.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(out/'cache')
        for opt in ('-O0','-O2'):
            exe=out/(opt+'.exe')
            cmd=[str(find_zig()),'cc','-target','x86_64-windows-gnu',opt,'-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument','-fno-sanitize=all','-I.','test/x86_64_network_dma_host.c','arch/x86_64/devices/network_dma.c','-o',str(exe)]
            r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,timeout=120);(out/(opt+'.log')).write_bytes(r.stdout+r.stderr)
            self.assertEqual(r.returncode,0,r.stderr.decode(errors='replace')[-1800:])
            r=subprocess.run([exe],cwd=ROOT,capture_output=True,timeout=5);self.assertEqual(r.returncode,0,r.stderr.decode(errors='replace'));self.assertIn(b'NETWORK_DMA_HOST_OK',r.stdout)
if __name__=='__main__':unittest.main()
