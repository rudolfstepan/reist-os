"""Execute native GUI production mechanisms; no source-only runtime claims."""
from pathlib import Path
import os,subprocess,sys,unittest,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_program import find_zig

class GraphicalSessionTests(unittest.TestCase):
    def test_altered_admission_command_scope(self):
        import struct,json
        from unittest.mock import patch
        import run_qemu_x86_64_graphical_session as runner
        import verify_x86_64_graphical_session as verify
        base=verify.EVIDENCE/'candidate06'
        raw=(base/'graphical/altered-service/guest.log').read_bytes()
        self.assertFalse(any(r[0]>=4 for r in runner.desktop_receipts(raw)))
        self.assertTrue(any(r[0]==4 and r[1]==9 for r in runner.reap_records(raw)))
        for slot in range(4,8):
            record=b'REIST_X86_64_PROCESS_REAP_OK v1='+struct.pack('<4I2Q',slot,9,0,4,1,0x410000).hex().upper().encode()+b'\r\n'
            modified=raw.replace(b'desktop\n',b'desktop\n'+record,1)
            self.assertTrue(any(r[0]>=4 for r in runner.desktop_receipts(modified)))
        for modified in (raw.replace(b'C:\\>',b'broken'),raw.replace(b'desktop\n',b'wrong\n',1)):
            with self.assertRaises(ValueError):runner.desktop_receipts(modified)
        # Offline regression only: bind historical observer identities to the
        # immutable frozen source copies; current reviewer replays all raw checks.
        # This neither changes receipts nor admits a historical case as fresh.
        image,package=verify.package();digest=verify.digest
        names=('scripts/run_qemu_x86_64_graphical_session.py','scripts/verify_x86_64_graphical_session.py')
        saved={str((ROOT/n).resolve()):base/'sources'/n for n in names}
        def historical(path):return digest(saved.get(str(Path(path).resolve()),path))
        with patch.object(verify,'digest',side_effect=historical):
            for spec in runner.CASES[-2:]:
                proof=runner.review_case(image,package,base/'graphical'/spec[0],spec)
                self.assertEqual(proof['ready'],3 if spec[1]==14 else 0)

    def test_exhaustion_generation_scope(self):
        import struct
        from run_qemu_x86_64_graphical_session import exhaustion_receipts,reap_records
        raw=(ROOT/'build/codex-agent/r83bi-graphical-session/guest11/guest.log').read_bytes()
        self.assertEqual([r[1] for r in exhaustion_receipts(raw,13<<32|4)],[13,17,21])
        self.assertEqual([r[1] for r in reap_records(raw) if r[0]==4],[13,17,21,29])
        def wire(row):return struct.pack('<4I2Q',*row).hex().upper().encode()
        records=exhaustion_receipts(raw,13<<32|4)
        for row in records:
            changed=(*row[:2],0,*row[3:])
            with self.assertRaises(ValueError):exhaustion_receipts(raw.replace(wire(row),wire(changed)),13<<32|4)
        with self.assertRaises(ValueError):exhaustion_receipts(raw,17<<32|4)
        with self.assertRaises(ValueError):exhaustion_receipts(raw.replace(b'C:\\>',b'broken'),13<<32|4)

    def test_actual_render_pacing(self):
        from build_x86_64_graphical_programs import font_header
        folder=ROOT/'build/codex-agent/r83bi-graphical-session'/('pacing-'+uuid.uuid4().hex)
        folder.mkdir(parents=True);font_header(folder)
        self.compile_run(['test/x86_64_graphical_compositor_host.c',
            'userspace/gui/compositor/native_session.c','userspace/gui/compositor/native_render.c',
            'userspace/gui/compositor/desktop_wm.c','userspace/gui/compositor/desktop_surface.c',
            'userspace/gui/lib/font_catalog.c','userspace/sdk/lib/x86_64/graphical_session.c'],
            'GRAPHICAL_COMPOSITOR',['-DREIST_RENDER_PACING=1','-Iuserspace/gui/include','-I'+str(folder)])
    def test_focus_capture_independent_replay(self):
        import copy,struct,json
        from run_qemu_x86_64_graphical_session import CASES,replay_routing
        rows=[];sequence=0
        def raw(kind,flags=0,code=0,dx=0,dy=0,buttons=0):
            nonlocal sequence
            sequence+=1;payload=struct.pack('<4I4Q3iI',2,64,kind,flags,8<<32|5,7<<32|4,1,sequence,code,dx,dy,buttons)
            rows.append(dict(slot=4,wire=(struct.pack('<3I',1,140,64)+payload+bytes(64)).hex()))
        def local(slot,event):
            payload=bytearray(124);struct.pack_into('<4I2I',payload,0,6,124,129,0,slot-5,slot+10)
            struct.pack_into('<2I4i4I',payload,84,*event)
            rows.append(dict(slot=slot,wire=(struct.pack('<3I',1,140,124)+payload+bytes(4)).hex()))
        raw(1);raw(2,16,56);raw(2,16,15);raw(2,17,15);local(6,(3,1,0,0,0,0,0,0,9,0));raw(2,1,56)
        raw(3,dx=42,dy=-72);local(6,(1,2,27,16,42,72,0,0,0,0))
        raw(3,buttons=1);local(6,(2,3,27,16,0,0,1,1,0,0))
        raw(3,dx=255,dy=-255,buttons=1);local(6,(1,4,282,191,255,255,0,0,0,0))
        raw(3,dx=200,dy=-50,buttons=1);local(6,(1,5,319,191,200,50,0,0,0,0))
        raw(3);local(6,(2,6,319,191,0,0,1,0,0,0))
        raw(3,dx=-5,dy=85);local(7,(1,7,237,76,-5,-85,0,0,0,0))
        raw(3,buttons=1);local(7,(2,8,237,76,0,0,1,1,0,0))
        raw(3);local(7,(2,9,237,76,0,0,1,0,0,0))
        raw(2,code=48);local(7,(3,10,0,0,0,0,0,1,98,0))
        raw(2,flags=1,code=48);local(7,(3,11,0,0,0,0,0,0,98,0))
        spec=next(s for s in CASES if s[0]=='focus-capture')
        result=replay_routing(rows,spec)
        self.assertEqual(result['local_events'],11)
        self.assertEqual(result,json.loads(json.dumps(result)))
        release=next(n for n,r in enumerate(rows) if r['slot']==6 and struct.unpack_from('<I',bytes.fromhex(r['wire']),100)[0]==6)
        for offset in (96,100,104,108,112,116,120,124,128,132):
            bad=copy.deepcopy(rows);wire=bytearray.fromhex(bad[release]['wire']);wire[offset]^=1;bad[release]['wire']=wire.hex()
            with self.assertRaises(ValueError):replay_routing(bad,spec)
        bad=copy.deepcopy(rows);bad[release]['slot']=7
        with self.assertRaises(ValueError):replay_routing(bad,spec)
        bad=copy.deepcopy(rows);bad.pop(release)
        with self.assertRaises(ValueError):replay_routing(bad,spec)

    def test_qualification_adapters_and_launcher_admission(self):
        from unittest.mock import patch,Mock
        import run_qemu_x86_64_graphical_session as guest
        import verify_x86_64_graphical_session as verify
        import run_qemu_x86_64_cli_media as cli
        image,package=verify.package()
        self.assertTrue(callable(verify.cli_runner()));self.assertTrue(callable(verify.cli_reviewer(image,package)))
        _,_,files=cli.apps.image_config(image,'ext2-1k')
        self.assertEqual(verify.cli_files(package,files),cli.apps.media.image('ext2-1k',files))
        bad=dict(files);bad['cat.prg']=bytes(len(bad['cat.prg']))
        with self.assertRaises(ValueError):verify.cli_files(package,bad)
        with patch.object(guest,'accepted_package',side_effect=ValueError('not accepted')),patch.object(guest.subprocess,'Popen') as popen:
            for only in (False,True):
                with self.assertRaisesRegex(ValueError,'not accepted'):guest.launch(check_only=only)
            popen.assert_not_called()
        # Admission must fail closed before the accepted receipt exists. This
        # test stays valid after acceptance by substituting an empty directory.
        empty=verify.EVIDENCE/('admission-'+uuid.uuid4().hex);empty.mkdir()
        with patch.object(verify,'EVIDENCE',empty),patch.object(guest.subprocess,'Popen') as popen:
            with self.assertRaisesRegex(ValueError,'noch nicht abgenommen'):guest.launch(check_only=True)
            popen.assert_not_called()
        with patch.object(guest,'accepted_package',return_value=package),patch.object(guest.subprocess,'Popen') as popen:
            self.assertEqual(guest.launch(check_only=True),dict(passed=True,check_only=True));popen.assert_not_called()
        a=guest.machine_arguments('qemu',4096,'none');b=guest.machine_arguments('qemu',4096,'gtk')
        self.assertEqual([(x,y) for x,y in zip(a,b) if x!=y],[('none','gtk')])
        for ram in (True,0,2048,16384):
            with self.assertRaises(ValueError):guest.machine_arguments('qemu',ram,'gtk')
        symbols={n:v['value'] for n,v in guest.elf.elf(image.read_bytes(),32)['symbols'].items()}
        for selector in (1,10,12,13):
            path=empty/str(selector)
            with patch.object(guest.subprocess,'Popen',return_value=Mock()) as popen:
                _,log=guest.lifecycle_observer(image,symbols,1234,path,selector);log.close()
                self.assertEqual(popen.call_count,1)
            script=(path/'lifecycle.gdb').read_text()
            for part in script.split('\npython\n')[1:]:compile(part.split('\nend\n')[0],'<gdb lifecycle Python>','exec')

    def test_launcher_owned_cleanup_and_deadlines(self):
        import json
        from unittest.mock import patch,Mock
        import run_qemu_x86_64_graphical_session as guest
        root=guest.verify.EVIDENCE/('launcher-host-'+uuid.uuid4().hex);root.mkdir()
        package=root/'package';package.mkdir();(package/'system.ext2').write_bytes(bytes(1048576))
        for mode in ('normal','deadline','user','launch-error','data-cleanup-error'):
            medium=Mock();medium.overlay=root/'boot.qcow2';data=Mock();data.arguments.return_value=[]
            vm=Mock();vm.wait.return_value=0;vm.poll.return_value=0
            if mode=='deadline':vm.wait.side_effect=[subprocess.TimeoutExpired('qemu',175),0];vm.poll.return_value=None
            if mode=='user':vm.wait.side_effect=[KeyboardInterrupt(),0];vm.poll.return_value=None
            def terminated():vm.poll.return_value=0
            vm.terminate.side_effect=terminated
            if mode=='data-cleanup-error':data.verify.side_effect=[None,ValueError('media cleanup')]
            trial=root/mode
            with patch.object(guest.verify,'EVIDENCE',trial),patch.object(guest,'accepted_package',return_value=package),\
                 patch.object(guest.bios,'BootMedium',return_value=medium),patch.object(guest,'Data',return_value=data),\
                 patch.object(guest.boot,'resolve_qemu',return_value=Path('qemu.exe')),\
                 patch.object(guest.subprocess,'Popen',side_effect=OSError('launch') if mode=='launch-error' else None,return_value=vm) as popen:
                if mode in ('launch-error','data-cleanup-error'):
                    with self.assertRaises((OSError,ValueError)):guest.launch()
                else:
                    result=guest.launch();self.assertTrue(result['passed'])
                    self.assertLessEqual(vm.wait.call_args_list[0].kwargs['timeout'],175)
                    if mode in ('deadline','user'):vm.terminate.assert_called_once()
                self.assertEqual(medium.verify.call_args_list[-1].args,('after',))
                self.assertEqual(data.verify.call_args_list[-1].args,('after',))
                cmd=popen.call_args.args[0]
                self.assertEqual(cmd[cmd.index('-display')+1],'gtk');self.assertNotIn('-kernel',cmd)
            saved=list(trial.glob('sessions/*/session.json'));self.assertEqual(len(saved),1)
            self.assertEqual(json.loads(saved[0].read_text())['passed'],mode not in ('launch-error','data-cleanup-error'))

    def test_graphical_matrix_raw_oracles(self):
        import copy,struct
        from unittest.mock import patch
        import run_qemu_x86_64_graphical_session as guest
        for number,label in (('05','healthy-hdd'),('07','compositor-crash'),('08','client-crash'),('09','healthy-hdd'),('10','client-crash')):
            folder=ROOT/'build/codex-agent/r83bi-graphical-session'/('guest'+number)
            spec=next(s for s in guest.CASES if s[0]==label)
            result=guest.review_audits(folder/'receive-audit',spec)
            self.assertEqual(result['local_keyboard'],40)
            self.assertEqual(guest.pixel_proof(folder)['glyphs'],20)
            if number=='10':
                import json
                row=json.loads((folder/'result.json').read_text())
                self.assertEqual(guest.review_audits(folder/'reintegration',readiness_only=True),row['reintegration'])
                self.assertEqual(row['reintegration']['authority'],result['authority'])
        folder=ROOT/'build/codex-agent/r83bi-graphical-session/guest08'
        width,height,raw=guest.ppm(folder/'after-input/pixels.ppm')
        before=guest.ppm(folder/'initial/pixels.ppm')
        for offset in (((112*width+35)*3),((600*width+700)*3)):
            bad=bytearray(raw);bad[offset]^=1
            with patch.object(guest,'ppm',side_effect=(before,(width,height,bytes(bad)))):
                with self.assertRaises(ValueError):guest.pixel_proof(folder)
        audit=folder/'receive-audit';proof=guest.state(audit,True);rows=[]
        for slot in (4,6,7):rows.extend(guest.parse_audit((audit/('audit'+str(slot)+'.bin')).read_bytes(),proof['owners'][slot-4],proof['service_epoch']))
        rows.sort(key=lambda r:(r['tick'],r['slot'],r['sequence']))
        spec=next(s for s in guest.CASES if s[0]=='client-crash')
        guest.replay_routing(rows,spec)
        index=next(n for n,r in enumerate(rows) if r['slot']==6)
        for offset in (24,28,36,96,100,104,108,112,116,120,124,128,132):
            bad=copy.deepcopy(rows);wire=bytearray.fromhex(bad[index]['wire']);wire[offset]^=1;bad[index]['wire']=wire.hex()
            with self.assertRaises(ValueError,msg=str(offset)):guest.replay_routing(bad,spec)

    def test_matrix_and_altered_service_fixture(self):
        import json
        import run_qemu_x86_64_graphical_session as guest
        self.assertEqual(len(guest.CASES),18)
        self.assertEqual([s[1] for s in guest.CASES],[0,0,0,*range(1,16)])
        receipt=json.loads((ROOT/'build/codex-agent/r83bi-graphical-session/development-media04.json').read_text())
        package=Path(receipt['package']);raw,proof=guest.altered_volume(package)
        old=(package/'system.ext2').read_bytes()
        self.assertEqual([i for i,(a,b) in enumerate(zip(old,raw)) if a!=b],[proof['offset']])
        self.assertEqual(raw[proof['offset']],old[proof['offset']]^1)

    def test_real_focus_capture_json_replay(self):
        import json
        import run_qemu_x86_64_graphical_session as guest
        folder=guest.verify.EVIDENCE/'candidate02/graphical/focus-capture'
        spec=next(s for s in guest.CASES if s[0]=='focus-capture')
        expected=json.loads((folder/'result.json').read_text())['receive_audit']
        self.assertEqual(guest.review_audits(folder/'receive-audit',spec),expected)

    def test_renderer_exact_pixels_and_bounded_lookups(self):
        from build_x86_64_graphical_programs import font_header
        folder=ROOT/'build/codex-agent/r83bi-graphical-session'/('render-equivalence-'+uuid.uuid4().hex)
        folder.mkdir(parents=True);font_header(folder)
        adapter=folder/'production.c'
        adapter.write_text('#define desktop_wm_window_at instrumented_window_at\n#include "'+
            (ROOT/'userspace/gui/compositor/native_render.c').as_posix()+'"\n',encoding='ascii')
        self.compile_run(['test/x86_64_graphical_compositor_host.c',
            'userspace/gui/compositor/native_session.c',str(adapter),
            'userspace/gui/compositor/desktop_wm.c','userspace/gui/compositor/desktop_surface.c',
            'userspace/gui/lib/font_catalog.c','userspace/sdk/lib/x86_64/graphical_session.c'],
            'GRAPHICAL_COMPOSITOR',['-DREIST_RENDER_EQUIVALENCE=1','-Iuserspace/gui/include','-I'+str(folder)])

    def test_receive_audit_snapshot_parser(self):
        import struct
        from run_qemu_x86_64_graphical_session import parse_audit,audit_bindings
        owner=7<<32|4;epoch=3;raw=bytearray(20544)
        struct.pack_into('<4Q4I2Q',raw,0,0x3154494455414752,owner,epoch,2,1,128,20544,0,0,0)
        for n in range(2):
            payload=struct.pack('<4I4Q3iI',2,64,1 if not n else 2,0,8<<32|5,owner,epoch,n+1,0 if not n else 30,0,0,0)
            wire=struct.pack('<3I',1,140,64)+payload+bytes(64)
            at=64+n*160;struct.pack_into('<2QI',raw,at,n+1,100+n,101);raw[at+20:at+160]=wire
        self.assertEqual(len(parse_audit(bytes(raw),owner,epoch)),2)
        for at in (0,8,16,24,32,36,40,44,48,56,64,72,84,88,92,223,224,384):
            bad=bytearray(raw);bad[at]^=128
            with self.assertRaises(ValueError,msg=str(at)):parse_audit(bytes(bad),owner,epoch)
        bad=bytearray(raw);struct.pack_into('<I',bad,80,0)
        with self.assertRaises(ValueError):parse_audit(bytes(bad),owner,epoch)
        for identity,generation in ((owner+1,epoch),(owner,epoch+1)):
            with self.assertRaises(ValueError):parse_audit(bytes(raw),identity,generation)
        image=ROOT/'build/codex-agent/r83bi-graphical-session/build02/x86_64/reist-x86_64-bootstrap.elf'
        bindings=audit_bindings(image);self.assertEqual(set(bindings),{4,6,7})
        self.assertTrue(all(v['bytes']==20544 for v in bindings.values()))

    def test_actual_receive_audit(self):
        self.compile_run(['test/x86_64_graphical_session_host.c',
            'userspace/sdk/lib/x86_64/graphical_session.c','userspace/gui/lib/native_surface.c'],
            'GRAPHICAL_LIFECYCLE',['-DREIST_GRAPHICAL_AUDIT_HOST=1','-fno-builtin','-Iuserspace/gui/include'])

    def test_existing_compiled_input_probe(self):
        import shutil,struct
        from run_qemu_x86_64_graphical_session import input_probe
        image=ROOT/'build/codex-agent/r83bi-graphical-session/build01/x86_64/reist-x86_64-bootstrap.elf'
        proof=input_probe(image);self.assertEqual(len(bytes.fromhex(proof['prefix'])),32)
        folder=ROOT/'build/codex-agent/r83bi-graphical-session'/('probe-host-'+uuid.uuid4().hex)
        target=folder/'programs-test';target.mkdir(parents=True)
        shutil.copyfile(image.parent/'boot-programs.bin',folder/'boot-programs.bin')
        shutil.copyfile(image.parent/'boot-programs.bin',target/'boot-programs.bin')
        for name in proof['bindings']:
            path=ROOT/name;shutil.copyfile(path,target/path.name)
        candidate=folder/'reist-x86_64-bootstrap.elf';self.assertEqual(input_probe(candidate)['address'],proof['address'])
        path=target/'desktop.prg';original=path.read_bytes();raw=bytearray(original)
        phoff=struct.unpack_from('<Q',raw,32)[0]
        for n in range(struct.unpack_from('<H',raw,56)[0]):
            kind,flags,offset,va,_,filesz,_,_=struct.unpack_from('<II6Q',raw,phoff+56*n)
            if kind==1 and va<=proof['address']<va+filesz:
                raw[offset+proof['address']-va]^=1;break
        path.write_bytes(raw)
        with self.assertRaisesRegex(ValueError,'entry bytes'):input_probe(candidate)

    def test_bounded_qmp_debug_notifications(self):
        import time
        from unittest.mock import Mock,patch
        from run_qemu_x86_64_graphical_session import QMP
        def transport(rows):
            value=QMP.__new__(QMP);value.end=time.monotonic()+30;value.seq=0
            value.sock=Mock();value.read=Mock(side_effect=rows);return value
        value=transport([{'event':'STOP'},{'event':'RESUME'}]*1000+[{'id':1,'return':{'running':True}}])
        self.assertEqual(value.call('query-status',{}),{'running':True});self.assertEqual(value.read.call_count,2001)
        for rows in ([{'event':'RESET'}],[{'id':2,'return':{}}],[{'id':1,'error':{}}],
                     [{'event':'STOP'}]*8224):
            with self.assertRaises(ValueError):transport(rows).call('query-status',{})
        value=transport([{'event':'STOP'}]);end=value.end
        with patch('run_qemu_x86_64_graphical_session.time.monotonic',side_effect=(end-10,end-10,end-10,end-7)):
            with self.assertRaisesRegex(ValueError,'deadline'):value.call('query-status',{})
        self.assertEqual(value.end,end)

    def test_actual_ipc_replay_rejects_mutations(self):
        import copy,struct
        from run_qemu_x86_64_graphical_session import replay_records
        rows=[]
        def add(slot,generation,payload):
            wire=struct.pack('<3I',1,140,len(payload))+payload+bytes(128-len(payload))
            rows.append(dict(index=len(rows)+1,slot=slot,generation=generation,endpoint=100,
                tick=len(rows),wire=wire.hex()))
        add(4,7,struct.pack('<4I4Q3iI',2,64,1,0,8<<32|5,7<<32|4,1,1,0,0,0,0))
        for n in range(40):
            add(4,7,struct.pack('<4I4Q3iI',2,64,2,n%2,8<<32|5,7<<32|4,1,n+2,30,0,0,0))
            payload=bytearray(124);struct.pack_into('<3I',payload,0,6,124,129)
            struct.pack_into('<2I4i4I',payload,84,3,n+1,0,0,0,0,0,1-n%2,ord('a'),0)
            add(6,9,payload)
        self.assertEqual(replay_records(rows),dict(received_input=41,local_keyboard=40))
        for index,field,value in ((1,'slot',6),(1,'generation',8),(2,'slot',7),
                (3,'index',1),(3,'tick',0),(2,'generation',0)):
            bad=copy.deepcopy(rows);bad[index][field]=value
            with self.assertRaises(ValueError):replay_records(bad)
        for index,offset in ((0,0),(0,4),(0,8),(0,139),(1,12),(1,28),(1,36),
                             (1,44),(1,52),(1,60),(2,96),(2,124),(2,128),(2,132)):
            bad=copy.deepcopy(rows);wire=bytearray.fromhex(bad[index]['wire']);wire[offset]^=128
            bad[index]['wire']=wire.hex()
            with self.assertRaises(ValueError,msg=str((index,offset))):replay_records(bad)
        for index in (0,1,2,20,80):
            bad=copy.deepcopy(rows);bad.pop(index)
            with self.assertRaises(ValueError):replay_records(bad)

    def test_graphical_media_actual_filesystem(self):
        from build_x86_64_graphical_media import image,NAMES
        from check_x86_64_graphical_media import verify_volume
        folder=ROOT/'build/codex-agent/r83bi-graphical-session'/('media-host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        files={name:bytes((n*13+index)&255 for n in range(size)) for index,(name,size) in enumerate(
            zip(NAMES,(19000,20000,24000,17000,79,180000,27000,20000,21000)))}
        raw=image('ext2-1k',files);self.assertEqual(verify_volume(raw,files)['files'],9)
        for name,value in files.items():(folder/name).write_bytes(value)
        disk=folder/'system.ext2';disk.write_bytes(raw)
        for offset in (1024,1028,1040,1048,1064,1080,1112,1120,2048,2060,2062,4096,
                       5*1024+128,21*1024+32,22*1024,32*1024,len(raw)-1):
            bad=bytearray(raw);bad[offset]^=1
            with self.assertRaises(ValueError,msg=str(offset)):verify_volume(bytes(bad),files)
        source=(ROOT/'test/x86_64_app_files_host.c').read_text(encoding='utf-8')
        for a,b in [('"data.txt"};','"data.txt","desktop.prg","input.prg","text.prg","paint.prg"};'),
                    ('n<5;n++','n<9;n++'),('n<=5;n++','n<=9;n++'),('n==5?1:0','n==9?1:0'),
                    ('k<5','k<9'),('seen==31','seen==511')]:
            self.assertIn(a,source);source=source.replace(a,b)
        harness=folder/'parser.c';harness.write_text(source,encoding='utf-8')
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            commands=[([str(find_zig()),'cc',opt,'-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument',
                '-Iuserspace/sdk/include','-Iuserspace/storage/include',str(harness),
                'userspace/sdk/lib/x86_64/app_files.c','userspace/storage/lib/vfs_shadow_ext2.c',
                'userspace/storage/lib/vfs_shadow_fat32.c','-o',str(exe)],'compile'),
                ([str(exe),str(disk),'ext2-1k',str(folder)],'run')]
            for cmd,label in commands:
                r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,timeout=90,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (folder/(opt+'-'+label+'.log')).write_bytes(r.stdout+r.stderr)
                self.assertEqual(r.returncode,0,(r.stdout+r.stderr).decode(errors='replace')[-2400:])
                if label=='run':self.assertIn(b'APP_FILES_MEDIA_HOST_OK',r.stdout)

    def test_disabled_profiles(self):
        from verify_x86_64_graphical_session import default_projection,scope
        from verify_x86_64_terminal_service import default_projection as previous
        from verify_x86_64_input import default_projection as input_previous
        self.assertTrue(default_projection());scope();previous();input_previous()

    def test_freestanding_root_and_old_program_bytes(self):
        import hashlib
        from build_x86_64_boot_programs import build
        zig=str(find_zig());base=ROOT/'build/codex-agent/r83bi-graphical-session'/('roots-'+uuid.uuid4().hex)
        flags=dict(family=True,startup=True,import_image=True,pio=True,block=True,wide=True,
            block_profile=True,filesystem=True,file_launch=True,task_pool=True,pool_pio=True,
            live_file=True,service_console=True,terminal=True,shell_session=True,wide_file=True,
            app_files=True,display=True,input=True,terminal_service=True)
        env=os.environ.copy()
        os.environ['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        os.environ['ZIG_LOCAL_CACHE_DIR']=str(base/'cache')
        try:
            for graphical in (False,True):
                folder=base/str(int(graphical))
                build(folder,[zig,'cc'],['C:/tools/nasm-3.02/nasm.exe'],[zig,'ld.lld'],0,
                      graphical_session=graphical,**flags)
                if not graphical:
                    old=ROOT/'build/codex-agent/r83bh-terminal-service/build04/x86_64/programs-b232128df0204f2b9b84ed8467fe66b5'
                    attempt=next(folder.glob('programs-*'))
                    for name in [*(f'program{n}.prg' for n in range(4)),'file-program.prg','cat.prg','ls.prg','probe.prg']:
                        self.assertEqual(hashlib.sha256((attempt/name).read_bytes()).digest(),
                            hashlib.sha256((old/name).read_bytes()).digest(),name)
        finally:
            for name in ('ZIG_GLOBAL_CACHE_DIR','ZIG_LOCAL_CACHE_DIR'):
                if name in env:os.environ[name]=env[name]
                else:os.environ.pop(name,None)

    def compile_run(self,sources,label,extra=()):
        if 'userspace/sdk/lib/x86_64/graphical_session.c' in sources:
            sources=[*sources,'userspace/sdk/lib/x86_64/service_session.c']
        folder=ROOT/'build/codex-agent/r83bi-graphical-session'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(command,name):
            p=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,timeout=120,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(name+'.log')).write_bytes(p.stdout+p.stderr)
            self.assertEqual(p.returncode,0,(p.stdout+p.stderr).decode(errors='replace')[-3000:])
            return p.stdout.decode()
        for opt in ('-O0','-O2'):
            exe=folder/(label+opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-Wall','-Wextra','-Werror',
                '-fno-sanitize=all','-Wno-unused-command-line-argument',
                '-Iuserspace/sdk/include',*extra,*sources,'-o',exe],opt+'-build')
            self.assertIn(label+'_OK',run([exe],opt+'-run'))

    def test_actual_lifecycle(self):
        self.compile_run(['test/x86_64_graphical_session_host.c',
            'userspace/sdk/lib/x86_64/graphical_session.c'],'GRAPHICAL_LIFECYCLE')

    def test_actual_hash_admission(self):
        import hashlib
        from build_x86_64_graphical_programs import hash_inputs
        folder=ROOT/'build/codex-agent/r83bi-graphical-session'/('hash-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        raw=bytes((n*17+n//4096)&255 for n in range(262240))
        expected=hashlib.sha256(raw).digest()
        (folder/'expected_hash.h').write_text('static const unsigned char expected[32]={'+
            ','.join(map(str,expected))+'};\n',encoding='ascii')
        sources,flags=hash_inputs(folder)
        self.compile_run(['test/x86_64_graphical_hash_host.c',*sources],
            'GRAPHICAL_HASH',[*flags,'-I'+str(folder)])

    def test_actual_compositor(self):
        from build_x86_64_graphical_programs import font_header
        folder=ROOT/'build/codex-agent/r83bi-graphical-session'/('render-'+uuid.uuid4().hex)
        folder.mkdir(parents=True);font_header(folder)
        self.compile_run(['test/x86_64_graphical_compositor_host.c',
            'userspace/gui/compositor/native_session.c',
            'userspace/gui/compositor/native_render.c',
            'userspace/gui/compositor/desktop_wm.c',
            'userspace/gui/compositor/desktop_surface.c',
            'userspace/gui/lib/font_catalog.c',
            'userspace/sdk/lib/x86_64/graphical_session.c'],
            'GRAPHICAL_COMPOSITOR',['-Iuserspace/gui/include','-I'+str(folder)])

    def test_freestanding_role_programs(self):
        from build_x86_64_graphical_programs import build_roles,hash_inputs
        from build_x86_64_boot_programs import prepare
        folder=ROOT/'build/codex-agent/r83bi-graphical-session'/('roles-'+uuid.uuid4().hex)
        zig=str(find_zig())
        roles=build_roles(folder,[zig,'cc'],['C:/tools/nasm-3.02/nasm.exe'],[zig,'ld.lld'])
        self.assertEqual([p.name for p in roles],['desktop.prg','input.prg','text.prg','paint.prg'])
        for path in roles:self.assertEqual(len(prepare(path.read_bytes(),[],True)),266336)
        sources,flags=hash_inputs(folder,True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'zig-cache')
        for n,source in enumerate(sources):
            r=subprocess.run([zig,'cc','-target','x86_64-freestanding-none','-std=c11','-Oz',
                '-Wall','-Wextra','-Werror','-ffreestanding','-nostdlib','-fno-builtin',
                '-fno-stack-protector','-mno-red-zone','-mno-mmx','-mno-sse','-mno-sse2',
                '-Iuserspace/sdk/include',*flags,'-c',str(source),'-o',str(folder/f'hash-{n}.o')],
                cwd=ROOT,env=env,timeout=60,capture_output=True)
            (folder/f'hash-{n}.log').write_bytes(r.stdout+r.stderr)
            self.assertEqual(r.returncode,0,r.stderr.decode(errors='replace')[-2400:])

if __name__=='__main__':unittest.main()
