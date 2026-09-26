"""Actual native mode mechanism and Ring3 policy tests; no source-only proof."""
from pathlib import Path
import json,os,subprocess,sys,time,unittest,uuid
import struct
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_sdk import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs

class VideoModeTests(unittest.TestCase):
    def test_independent_replay_rejects_tampered_runtime_evidence(self):
        from verify_x86_64_video_mode import replay_qemu
        directory=Path(os.environ.get('REIST_VIDEO_REPLAY_DIRECTORY',
                       ROOT/'build/codex-agent/r83ck-video-mode/media10'))
        folder=Path(os.environ.get('REIST_VIDEO_REPLAY_FOLDER',
                    ROOT/'build/codex-agent/r83ck-video-mode/guest15'))
        self.assertTrue(replay_qemu(directory,folder)['passed'])
        original=Path.read_bytes
        variants=[]
        target=folder/'commands/mode.bin';data=bytearray(original(target))
        struct.pack_into('<Q',data,4*8,0);struct.pack_into('<Q',data,16*8,2**64-1)
        variants.append((target,bytes(data)))
        target=folder/'graphics/mode-pdpt.bin';data=bytearray(original(target))
        data[509*8]|=4;variants.append((target,bytes(data)))
        target=folder/'commands/family.bin';data=bytearray(original(target))
        data[40*8]=1;variants.append((target,bytes(data)))
        target=folder/'serial.log';data=original(target)
        import re
        records=list(re.finditer(rb'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-F]{64})',data))
        owner=struct.unpack_from('<Q',original(folder/'commands/mode.bin'))[0]
        fault=next(m for m in records if struct.unpack('<4I2Q',bytes.fromhex(m[1].decode()))[:2]==(owner&0xffffffff,owner>>32))
        record=bytearray.fromhex(fault[1].decode());struct.pack_into('<I',record,8,122)
        variants.append((target,data[:fault.start(1)]+record.hex().upper().encode()+data[fault.end(1):]))
        for target,changed in variants:
            with self.subTest(path=target.relative_to(folder)):
                def read(path):return changed if path==target else original(path)
                with patch.object(Path,'read_bytes',read):
                    with self.assertRaises(ValueError):replay_qemu(directory,folder)

    def test_compact_terminal_preserves_all_loaded_bytes(self):
        from build_x86_64_video_mode import compact_elf
        from build_x86_64_boot_programs import prepare
        source=next((ROOT/'build/codex-agent/r83ck-video-mode/build04/x86_64').glob('programs-*'))/'video-driver.prg'
        original=source.read_bytes();compact=compact_elf(original)
        self.assertEqual(prepare(original,[],True),prepare(compact,[],True))
        self.assertGreater(len(original)-len(compact),3000)

    def test_production_core(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83ck-video-mode'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        cache=next(folder.parent.glob('host-*/global'),folder.parent/'zig-global')
        env=dict(os.environ,ZIG_GLOBAL_CACHE_DIR=str(cache),ZIG_LOCAL_CACHE_DIR=str(folder/'local'))
        for level in ('0','2'):
            target=folder/('core-'+level+'.exe')
            for label,command in (('compile-'+level,[find_zig(),'cc','-target','x86_64-windows-gnu',
                 '-std=c11','-O'+level,'-Wall','-Wextra','-Werror','-I.','-Iuserspace/sdk/include',
                 'test/x86_64_video_mode_host.c','arch/x86_64/video/video_mode.c',
                 'userspace/drivers/video/native_mode.c','-o',str(target)]),
                 ('run-'+level,[str(target)])):
                start=time.monotonic()
                result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=60)
                (folder/(label+'.log')).write_bytes(result.stdout+result.stderr)
                (folder/(label+'.json')).write_text(json.dumps(dict(command=list(map(str,command)),
                   elapsed=time.monotonic()-start,exit=result.returncode)))
                self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace')[-2000:])
        command=[find_zig(),'cc','-target','x86_64-freestanding-none','-std=c11','-Oz',
                 '-Wall','-Wextra','-Werror','-ffreestanding','-nostdlib','-fno-builtin',
                 '-fno-stack-protector','-mno-red-zone','-fno-pic','-fno-pie',
                 '-mno-mmx','-mno-sse','-mno-sse2','-I.','-DREIST_NATIVE_VIDEO_MODE=1',
                 '-c','arch/x86_64/video/video_mode.c','-o',str(folder/'hardware.o')]
        result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=60)
        (folder/'hardware.log').write_bytes(result.stdout+result.stderr)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace')[-2000:])

if __name__=='__main__':unittest.main()
