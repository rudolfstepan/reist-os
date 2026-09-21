from pathlib import Path
import os,struct,subprocess,sys,unittest,uuid
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from build_user_sdk import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs
class InputTests(unittest.TestCase):
    def test_live_authority_and_full_pixels_reject_mutation(self):
        from run_qemu_x86_64_input import live_profile,painted
        folder=ROOT/'build/codex-agent/r83bg-input'/('oracle-'+uuid.uuid4().hex);folder.mkdir(parents=True)
        tasks=bytearray(8192);profiles=bytearray(256);family=bytearray(512)
        struct.pack_into('<Q',tasks,8,1)
        for slot,gen,mask,high in ((4,3,sum(1<<n for n in (4,5,6,9,15,20,22,40,41,42,50,51,53,54,58)),(1<<49)|(1<<63)),
                                  (5,2,sum(1<<n for n in (9,22,41,42,53)),1<<49)):
            struct.pack_into('<Q',tasks,slot*1024+8,gen);struct.pack_into('<4Q',profiles,slot*32,gen,mask,high,0)
            struct.pack_into('<2Q',family,slot*64,gen<<32|slot,1<<32)
        for name,raw in (('tasks',tasks),('profiles',profiles),('family',family)):(folder/(name+'.bin')).write_bytes(raw)
        event=(1,64,1,0,2<<32|5,3<<32|4,1,1,0,0,0,0)
        self.assertEqual(live_profile(folder,event)['root'],1<<32)
        for slot in (4,5):
            for word in range(4):
                bad=bytearray(profiles);bad[slot*32+word*8]^=1;(folder/'profiles.bin').write_bytes(bad)
                with self.assertRaises(ValueError):live_profile(folder,event)
        (folder/'profiles.bin').write_bytes(profiles)
        family[5*64+8]^=1;(folder/'family.bin').write_bytes(family)
        with self.assertRaises(ValueError):live_profile(folder,event)
        before=bytes(800*600*3);after=bytearray(before)
        for y in range(64):
            for x in range(64):at=((32+y)*800+32+x)*3;after[at:at+3]=bytes((x*4,y*4,90))
        for y in range(134,198):
            for x in range(140,204):at=(y*800+x)*3;after[at:at+3]=bytes((0,208,255))
        header=b'P6\n800 600\n255\n';(folder/'before.ppm').write_bytes(header+before);(folder/'after.ppm').write_bytes(header+after)
        painted(folder/'before.ppm',folder/'after.ppm',True)
        after[-1]^=1;(folder/'after.ppm').write_bytes(header+after)
        with self.assertRaises(ValueError):painted(folder/'before.ppm',folder/'after.ppm',True)

    def test_pinned_starter_and_invalid_launch_before_effects(self):
        import run_x86_64_input as starter
        import build_x86_64_input_media as producer
        from verify_x86_64_input import EVIDENCE,BUILD_ID
        values=producer.inputs(EVIDENCE/('build'+BUILD_ID)/'x86_64');starter.inputs(values)
        for name in ('program0.prg','file-program.prg','reist-x86_64-bootstrap.elf'):
            bad=dict(values);bad[name]=bytes([values[name][0]^1])+values[name][1:]
            with self.assertRaises(ValueError):starter.inputs(bad)
        with mock.patch.object(starter,'admit',side_effect=AssertionError('invalid launch must have no admission/session effects')):
            for args in (dict(seconds=29),dict(seconds=321),dict(seconds=True),dict(ram=16384),dict(layout='usb'),dict(headless=1)):
                with self.assertRaises(ValueError):starter.launch(**args)
    def test_hardware_event_oracle_rejects_mutation(self):
        from run_qemu_x86_64_input import event_proof,input_arguments
        fields=[(1,0,0,0,0,0),(2,4,42,0,0,0),(2,4,30,0,0,0),(2,5,30,0,0,0),
                (2,1,42,0,0,0),(3,0,0,12,-6,1),(3,0,0,0,0,0)]
        rows=[[1,64,t,f,2<<32|5,3<<32|4,1,n,c,x,y,b] for n,(t,f,c,x,y,b) in enumerate(fields,1)]
        def encode(rows):return b''.join(b'INPUT_EVENT v1='+struct.pack('<4I4Q3iI',*r).hex().encode()+b'\n' for r in rows)
        self.assertEqual(len(event_proof(encode(rows),True)),7)
        # Independent i8042 FIFOs may interleave; each device's order is fixed.
        interleaved=[r[:] for r in rows];interleaved[4],interleaved[5]=interleaved[5],interleaved[4]
        for n,r in enumerate(interleaved,1):r[7]=n
        self.assertEqual(len(event_proof(encode(interleaved),True)),7)
        for a,b in ((1,2),(2,3),(3,4),(5,6)):
            bad=[r[:] for r in rows];bad[a],bad[b]=bad[b],bad[a]
            for n,r in enumerate(bad,1):r[7]=n
            with self.assertRaises(ValueError):event_proof(encode(bad),True)
        for n in range(7):
            with self.assertRaises(ValueError):event_proof(encode(rows[:n]+rows[n+1:]),True)
        for n,field in ((0,4),(1,4),(1,5),(1,6),(1,7),(1,3),(5,9),(5,10),(5,11)):
            bad=[r[:] for r in rows];bad[n][field]+=1
            with self.assertRaises(ValueError):event_proof(encode(bad),True)
        self.assertEqual(len(input_arguments()),7);self.assertEqual(len(input_arguments(True)),64)
    def test_kernel_reap_interleaving_preserves_complete_user_event(self):
        from run_qemu_x86_64_input import events
        import struct
        event=struct.pack('<4I4Q3iI',1,64,4,0,(8<<32)|5,(7<<32)|4,1,2,-122,0,0,0)
        wire=b'INPUT_EVENT v1='+event.hex().encode()+b'\n'
        reap=b'REIST_X86_64_PROCESS_REAP_OK v1='+struct.pack('<4I2Q',5,8,122,4,0,4259883).hex().upper().encode()+b'\r\n'
        expected=[struct.unpack('<4I4Q3iI',event)]
        for boundary in (64,128):
            raw=wire[:boundary]+reap+wire[boundary:]
            self.assertEqual(events(raw),expected)
            self.assertEqual(events(wire[:boundary]+reap[:-2]+wire[boundary:]),[])
            self.assertEqual(events(wire[:boundary]+reap.replace(b' v1=',b' v2=')+wire[boundary:]),[])
        self.assertEqual(events(wire[:64]+reap+wire[64:128]+reap+wire[128:]),expected)
    def test_disabled_profile_and_freestanding_units(self):
        from verify_x86_64_input import default_projection
        default_projection()
        folder=ROOT/'build/codex-agent/r83bg-input'/('compile-'+uuid.uuid4().hex);folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        macros=('SERVICE_CPU','LIVE_FILE','SERVICE_CONSOLE','TERMINAL','SESSION','SHELL_SESSION','WIDE_FILE','APP_FILES','DISPLAY','INPUT')
        for n,source in enumerate(('arch/x86_64/user/input_service.c','arch/x86_64/user/input_client.c','userspace/sdk/lib/x86_64/shell_platform.c')):
            args=[find_zig(),'cc','-target','x86_64-freestanding-none','-std=c11','-Oz','-Wall','-Wextra','-Werror','-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie','-mno-mmx','-mno-sse','-mno-sse2','-Iuserspace/sdk/include','-Iuserspace/storage/include',
                  *['-DREIST_NATIVE_'+m+'=1' for m in macros],'-c',source,'-o',folder/(str(n)+'.o')]
            p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,capture_output=True,text=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(str(n)+'.log')).write_text(p.stdout+p.stderr);self.assertEqual(p.returncode,0,(p.stdout+p.stderr)[-1800:])
    def test_actual_core_and_decoder_o0_o2(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83bg-input'/('host-'+uuid.uuid4().hex);folder.mkdir(parents=True)
        asm=folder/'core.asm';asm.write_text('BITS 64\nsection .text\n%include "arch/x86_64/devices/input_core.inc"\n')
        obj=folder/'core.o';env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(args,name):
            p=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,capture_output=True,text=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(name+'.log')).write_text(p.stdout+p.stderr);self.assertEqual(p.returncode,0,(p.stdout+p.stderr)[-1800:])
        run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',asm,'-o',obj],'asm')
        for level in ('0','2'):
            exe=folder/('input-'+level+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu','-O'+level,'-Wall','-Wextra','-Werror','-I.','-Iuserspace/sdk/include',
                 'test/x86_64_input_host.c','userspace/drivers/ps2/native_input.c',obj,'-o',exe],'compile'+level)
            run([exe],'run'+level)
            service=folder/('service-'+level+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu','-O'+level,'-Wall','-Wextra','-Werror','-DREIST_INPUT_SERVICE_HOST=1','-I.','-Iuserspace/sdk/include',
                 'test/x86_64_input_host.c','userspace/drivers/ps2/native_input.c','-o',service],'compile-service'+level)
            run([service],'run-service'+level)
if __name__=='__main__':unittest.main()
