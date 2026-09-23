"""Bounded actual native C/C++ runtime and build admission regressions."""
from pathlib import Path
import os,subprocess,sys,unittest,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build_user_program as builder

class NativeCppRuntime(unittest.TestCase):
    def setUp(self):
        self.folder=ROOT/'build/codex-agent/r83br-cpp-runtime'/('host-'+uuid.uuid4().hex)
        self.folder.mkdir(parents=True);self.env=os.environ.copy()
        self.env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        self.env['ZIG_LOCAL_CACHE_DIR']=str(self.folder/'cache')
    def command(self,args,timeout=90):
        p=subprocess.run([str(x) for x in args],cwd=ROOT,env=self.env,capture_output=True,timeout=timeout)
        (self.folder/('command-'+uuid.uuid4().hex+'.log')).write_bytes(p.stdout+p.stderr)
        self.assertEqual(p.returncode,0,(p.stdout+p.stderr).decode(errors='replace')[-2000:])
        return p
    def compile(self,name,source,architecture='x86_64',extra=()):
        path=self.folder/name;path.write_text(source,encoding='utf-8');out=path.with_suffix('.o')
        self.command([builder.find_zig(),'cc','-target',architecture+'-freestanding-none',
            '-ffreestanding','-fno-builtin','-fno-stack-protector','-fno-sanitize=all',
            '-fno-unwind-tables','-fno-asynchronous-unwind-tables',
            '-Iuserspace/libc/include','-Iuserspace/sdk/include',*extra,'-c',path,'-o',out])
        return out.read_bytes()
    def test_native_process_provider_layout(self):
        source=(ROOT/'userspace/libc/lib/process_heap.c').read_text(encoding='utf-8')
        for arch in ('x86','x86_64'):
            self.compile('provider-'+arch+'.c',source,arch,['-std=c11','-O2','-Wall','-Wextra','-Werror'])
    def test_explicit_native_object_admission(self):
        for opt in ('0','2'):
            raw=self.compile('simple'+opt+'.cpp','extern "C" int answer(){return 42;}\n',
                extra=[*builder.cpp_compile_flags(),'-O'+opt])
            builder.validate_cpp_object(raw,architecture='x86_64')
            with self.assertRaises(ValueError):builder.validate_cpp_object(raw)
            for offset in (4,5,18,40,58):
                bad=bytearray(raw);bad[offset]^=0xff
                with self.assertRaises(ValueError):builder.validate_cpp_object(bytes(bad),architecture='x86_64')
        old=self.compile('old.cpp','extern "C" int answer(){return 42;}\n','x86',builder.cpp_compile_flags())
        builder.validate_cpp_object(old)
        with self.assertRaises(ValueError):builder.validate_cpp_object(old,architecture='x86_64')
    def test_native_forbidden_runtime(self):
        for name,source in {
            'tls':'thread_local int state; int f(){return state;}\n',
            'guard':'extern int create(); int f(){static int value=create();return value;}\n',
            'ctor':'extern int create(); int value=create();\n',
        }.items():
            raw=self.compile(name+'.cpp',source,extra=['-std=c++20','-O0'])
            with self.assertRaises(ValueError):builder.validate_cpp_object(raw,architecture='x86_64')

    def test_native_archive_admission(self):
        self.compile('member.cpp','extern "C" int answer(){return 42;}\n',extra=builder.cpp_compile_flags())
        archive=self.folder/'valid.a'
        self.command([builder.find_zig(),'ar','rcs',archive,self.folder/'member.o'])
        builder.validate_cpp_object(archive.read_bytes(),architecture='x86_64')
        with self.assertRaises(ValueError):builder.validate_cpp_object(archive.read_bytes())
        self.compile('hidden.cpp','extern int f();int value=f();\n',extra=['-std=c++20'])
        self.command([builder.find_zig(),'ar','rcs',archive,self.folder/'hidden.o'])
        with self.assertRaises(ValueError):builder.validate_cpp_object(archive.read_bytes(),architecture='x86_64')
        with self.assertRaises(ValueError):builder.validate_cpp_object(archive.read_bytes()[:-1],architecture='x86_64')

    def test_actual_cpp_runtime_high_pointers(self):
        source=(ROOT/'test/test_user_cpp_host.cpp').read_text(encoding='utf-8')
        source=source.replace('CHECK(constructions == 0 && !acquired);',
            'CHECK(sizeof(void*)==8 && reinterpret_cast<uintptr_t>(storage)>UINT32_MAX);\n'
            '    CHECK(constructions == 0 && !acquired);')
        path=self.folder/'runtime-host.cpp';path.write_text(source,encoding='utf-8')
        zig=builder.find_zig()
        rename=['-D'+n+'=reist_cpp_test_'+n for n in ('malloc','calloc','realloc','free')]
        for opt in ('0','2'):
            prefix=[zig,'cc','-O'+opt,'-UNDEBUG','-fno-builtin','-fno-sanitize=all',
                '-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument',
                '-Iuserspace/sdk/include','-Iuserspace/cpp/include','-Iuserspace/libc/include']
            heap=self.folder/('heap'+opt+'.o');runtime=self.folder/('runtime'+opt+'.o');fixture=self.folder/('test'+opt+'.o')
            self.command([*prefix,*rename,'-std=c11','-c','userspace/libc/lib/heap.c','-o',heap])
            self.command([*prefix,*rename,*builder.cpp_compile_flags(),'-c','userspace/cpp/runtime.cpp','-o',runtime])
            self.command([*prefix,*builder.cpp_compile_flags(),'-c',path,'-o',fixture])
            exe=self.folder/('runtime'+opt+'.exe');self.command([zig,'cc',heap,runtime,fixture,'-o',exe])
            self.assertIn(b'REIST_CPP_HOST_OK',self.command([exe],30).stdout)
            for mode,status in (('oom',71),('pure',72),('deleted',72)):
                p=subprocess.run([str(exe),mode],cwd=ROOT,capture_output=True,timeout=30)
                self.assertEqual(p.returncode,status,p.stdout+p.stderr)

    def test_actual_sdk_provider(self):
        zig=builder.find_zig()
        for opt in ('0','2'):
            exe=self.folder/('sdk'+opt+'.exe')
            self.command([zig,'cc','-O'+opt,'-std=c11','-UNDEBUG','-fno-builtin',
                '-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument',
                '-Iuserspace/sdk/include','-Iuserspace/libc/include','-DREIST_CPP_RUNTIME_HOST_TEST',
                'test/x86_64_cpp_runtime_platform_host.c','userspace/sdk/lib/x86_64/cpp_runtime.c',
                'userspace/libc/lib/process_heap.c','-o',exe])
            self.command([exe],30);self.command([exe,'blocked-output'],30)

    def test_actual_allocator_failure_recovery(self):
        zig=builder.find_zig();rename=['-D'+n+'=reist_test_'+n for n in ('malloc','calloc','realloc','free')]
        for opt in ('0','2'):
            exe=self.folder/('heap'+opt+'.exe')
            self.command([zig,'cc','-O'+opt,'-std=c11','-UNDEBUG','-fno-builtin',
                '-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument',
                '-Iuserspace/libc/include',*rename,'test/test_process_heap_host.c',
                'userspace/libc/lib/heap.c','-o',exe])
            self.assertIn(b'PRIVATE_MEMORY_HOST_OK',self.command([exe],30).stdout)

    def test_runtime_observer_composition(self):
        import run_qemu_x86_64_cpp_runtime as runtime
        for label,case,ram,mode in runtime.CASES:
            module=runtime.namespace(label)
            self.assertEqual(module.CASES,((case,2,ram),))
            source=runtime.selected_source()
            self.assertIn('elapsed<177',source)
            self.assertNotIn('elapsed<297',source)
            body=module.observer_body()
            self.assertIn('class CPPCheckpoint',body)
            self.assertIn('cpp_checkpoint.enabled=False',body)
        with self.assertRaises(ValueError):runtime.spec_for('unknown')

    def test_retained_raw_diagnostic(self):
        import run_qemu_x86_64_cpp_runtime as runtime
        image=ROOT/'build/codex-agent/r83br-cpp-runtime/build03/x86_64/reist-x86_64-bootstrap.elf'
        folder=ROOT/'build/codex-agent/r83br-cpp-runtime/diagnostic03'
        module=runtime.namespace('realloc-failure');config,records,files=runtime.image_config(image,'realloc-failure')
        module.app_files=files
        proof=module.evaluate(folder,config,records,(image.parent/'boot-programs.bin').read_bytes(),0,2,files)
        self.assertGreater(proof['tasks'],8)

    def test_default_projection_and_stack(self):
        import verify_x86_64_cpp_runtime as verifier
        self.assertTrue(verifier.projection())
        stack=verifier.stack_review(ROOT/'build/codex-agent/r83br-cpp-runtime/build03/x86_64/reist-x86_64-bootstrap.elf')
        self.assertLess(stack['aggregate']+stack['margin'],stack['stack'])

    def test_raw_checkpoint_mutations(self):
        import copy,json,struct
        import run_qemu_x86_64_cpp_runtime as runtime
        folder=ROOT/'build/codex-agent/r83br-cpp-runtime/diagnostic03'
        module=runtime.namespace('realloc-failure')
        image=ROOT/'build/codex-agent/r83br-cpp-runtime/build03/x86_64/reist-x86_64-bootstrap.elf'
        config,_,_=runtime.image_config(image,'realloc-failure')
        trace=runtime.wide.decode_evidence(runtime.wide.live_trace(folder/'frame-trace.log'))
        events=[json.loads(line[14:]) for line in trace.splitlines() if line.startswith('SHELL_SESSION ')]
        starts={r['gen']:r for r in events if r['kind']=='start'}
        rows=[r for r in events if r['kind']=='cpp_checkpoint']
        self.assertEqual(len(rows),5)
        reader=module.Snapshots(folder)
        for row in rows:runtime.validate_checkpoint(row,starts,set(starts),config,reader)
        class Changed:
            def __init__(self,key,data):self.key=key;self.data=data
            def read(self,ref,size=None):return self.data if ref==rows[0][self.key] else reader.read(ref,size)
        for key,offset,value in [('witness',8,32),('witness',56,0),('control',0,1),
                                 ('walks',0,0),('walks',56,0),('pages',16,0)]:
            data=bytearray(reader.read(rows[0][key]))
            if key=='pages':
                w=struct.unpack('<8Q',reader.read(rows[0]['witness']));data[w[1]&4095]^=1
            else:struct.pack_into('<Q',data,offset,value)
            with self.assertRaises(ValueError):runtime.validate_checkpoint(rows[0],starts,set(starts),config,Changed(key,bytes(data)))
        for key,value in [('pc',0),('root',0),('gen',0),('leaves',[0]*4)]:
            row=copy.deepcopy(rows[0]);row[key]=value
            with self.assertRaises(ValueError):runtime.validate_checkpoint(row,starts,set(starts),config,reader)
        reaped=[r for r in events if r['kind']=='cpp_reaped']
        self.assertEqual(len(reaped),2)
        for row in reaped:runtime.validate_reaped(row,starts,set(starts),reader)
        class DirtyReap:
            def read(self,ref,size=None):
                data=bytearray(reader.read(ref,size));data[128]=1;return bytes(data)
        with self.assertRaises(ValueError):runtime.validate_reaped(reaped[0],starts,set(starts),DirtyReap())

    def test_six_file_media_corruption(self):
        import run_qemu_x86_64_cpp_runtime as runtime
        image=ROOT/'build/codex-agent/r83br-cpp-runtime/build03/x86_64/reist-x86_64-bootstrap.elf'
        _,_,files=runtime.image_config(image,'healthy4g')
        raw=runtime.media.image('ext2-1k',files)
        runtime.check.verify_volume(raw,files)
        for offset in (1024,1024+16,2048+14,4096,5120+16*128+4):
            changed=bytearray(raw);changed[offset]^=1
            with self.assertRaises(ValueError):runtime.check.verify_volume(bytes(changed),files)
        altered=dict(files);altered['cpptest.prg']=altered['cpptest.prg'][:-1]
        with self.assertRaises(ValueError):runtime.check.verify_volume(raw,altered)

if __name__=='__main__':unittest.main()
