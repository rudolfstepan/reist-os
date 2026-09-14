"""Reference renewal admission rejects stale evidence before any guest."""
from pathlib import Path
from contextlib import contextmanager
import copy,hashlib,json,os,stat,sys,tempfile,unittest
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import qualify_x86_64_reference_renewal as renewal

class ReferenceRenewalTests(unittest.TestCase):
    @contextmanager
    def cached_build_fixture(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as directory:
            root=Path(directory);folder=root/'build/cache';folder.mkdir(parents=True)
            def put(name,payload):
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payload)
                return hashlib.sha256(payload).hexdigest()
            sources={'kernel.c':put('kernel.c',b'kernel'),
                     'test/fixtures/key.pem':put('test/fixtures/key.pem',b'signing input'),
                     'docs/development/CURRENT_WORK.md':put('docs/development/CURRENT_WORK.md',b'status')}
            tool=root/'compiler.exe';tool.write_bytes(b'compiler')
            frozen=dict(source_inputs=sources,tools_sha256={str(tool):hashlib.sha256(b'compiler').hexdigest()},
                        original_artifacts={'original.img':put('original.img',b'original')},gates=[{} for _ in range(17)])
            result=dict(gates=[{} for _ in range(13)]);summary=dict(before={},programs={f'P{i:02}.PRG':'unused' for i in range(96)})
            for index,target in ((11,'vmware'),(12,'qemu')):
                prefix='build/cache/'+target
                argv=['C:/Program Files/PowerShell/7/pwsh.exe','-NoProfile','-File','scripts/build-windows.ps1',
                      '-Target',target,'-Video','vga','-OutputDirectory',prefix]
                gate=dict(id=index,name='build-'+target,argv=argv,timeout=900);frozen['gates'][index-1]=gate
                log='build/cache/gate-%02d.log'%index
                result['gates'][index-1]=dict(gate,result='PASS',exit_code=0,elapsed_seconds=1,log=log,log_sha256=put(log,b'build success'))
                for name in ('kernel.bin','kernel.bin.sig','reist-os.img','reist-sbom.spdx.json',*('programs/'+p for p in summary['programs'])):
                    path=prefix+'/'+name;summary['before'][path]=put(path,b'bound artifact '+path.encode())
                path=prefix+'/.windows-build-config.json'
                summary['before'][path]=put(path,json.dumps(dict(target=target,video='vga',output_directory=prefix)).encode())
            yield root,folder,frozen,result,summary

    def test_cached_builds_reuse_exact_profiles_without_build_or_guest(self):
        with self.cached_build_fixture() as args,patch.object(renewal.legacy.subprocess,'run',side_effect=AssertionError('external process')):
            result=renewal.admit_cached_builds(*args)
            self.assertEqual([row['target'] for row in result],['vmware','qemu'])
            self.assertTrue(all(row['status']=='REUSED' and not row['runtime_accepted'] for row in result))
            self.assertEqual(sum(row['artifact_count'] for row in result),202)

    def test_cached_builds_reject_stale_sources_tools_logs_outputs_and_missing_files(self):
        with self.cached_build_fixture() as args:
            root,folder,frozen,result,summary=args
            paths=['kernel.c','test/fixtures/key.pem','compiler.exe','original.img','build/cache/gate-11.log',
                   'build/cache/vmware/kernel.bin','build/cache/qemu/reist-os.img']
            for name in paths:
                path=root/name;original=path.read_bytes();path.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'drift'):renewal.admit_cached_builds(*args)
                path.write_bytes(original)
            path=root/'build/cache/qemu/kernel.bin';path.unlink()
            with self.assertRaises((ValueError,OSError)):renewal.admit_cached_builds(*args)

    def test_cached_builds_allow_only_explicit_nonbuild_changes(self):
        with self.cached_build_fixture() as args:
            root,_,frozen,_,_=args
            (root/'docs/development/CURRENT_WORK.md').write_bytes(b'new status')
            self.assertEqual(len(renewal.admit_cached_builds(*args)),2)
            self.assertEqual(len(renewal.BUILD_NON_INPUTS),7)
            self.assertNotIn('test/fixtures/key.pem',renewal.BUILD_NON_INPUTS)

    def test_cached_builds_reject_failed_wrong_profile_and_partial_receipts(self):
        with self.cached_build_fixture() as args:
            root,folder,frozen,result,summary=args
            for key,value in (('result','FAIL'),('exit_code',1),('elapsed_seconds',901),('argv',['wrong-profile']),('log','../escape')):
                modified=copy.deepcopy(result);modified['gates'][10][key]=value
                with self.assertRaises(ValueError):renewal.admit_cached_builds(root,folder,frozen,modified,summary)
            partial=copy.deepcopy(summary);del partial['before']['build/cache/qemu/kernel.bin']
            with self.assertRaises(ValueError):renewal.admit_cached_builds(root,folder,frozen,result,partial)

    def test_cached_build_command_keeps_existing_dispatch(self):
        self.assertEqual(renewal.BUILD_CACHE.relative_to(renewal.ROOT).as_posix(),'build/codex-agent/r83am-file-launch/reference-metadata')
        with patch.object(renewal,'check_hashes',side_effect=ValueError('cache drift')),patch.object(renewal.legacy,'main') as guest:
            with self.assertRaisesRegex(ValueError,'cache drift'):renewal.check_builds()
            guest.assert_not_called()

    def test_rewritten_sources_and_cmd_keep_cross_view_identity(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as directory:
            for suffix in ('.cmd','.c'):
                source=Path(directory)/('source'+suffix)
                for payload in (b'original',b'rewritten source',b''):
                    source.write_bytes(payload);before=source.lstat()
                    self.assertEqual(renewal.source_digest(source),hashlib.sha256(payload).hexdigest())
                    after=source.lstat()
                    for field in ('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns'):
                        self.assertEqual(getattr(before,field),getattr(after,field))

    def test_source_cross_view_identity_mismatches_reject_before_read(self):
        fields=('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns','st_birthtime_ns')
        real_fstat=os.fstat
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as directory:
            source=Path(directory)/'source.c';source.write_bytes(b'unchanged')
            for field in ('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_birthtime_ns'):
                calls=[]
                def changed(fd):
                    info=real_fstat(fd);values={name:getattr(info,name,None) for name in fields}
                    values[field]=stat.S_IFDIR if field=='st_mode' else (values[field] or 0)+1
                    calls.append(fd);return SimpleNamespace(**values)
                with patch.object(renewal.os,'fstat',changed):
                    with self.assertRaisesRegex(ValueError,'source changed before read'):renewal.source_digest(source)
                self.assertEqual(len(calls),1)

    def test_source_each_views_own_mode_and_ctime_are_stable(self):
        fields=('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns','st_birthtime_ns')
        real_lstat=Path.lstat;real_fstat=os.fstat
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as directory:
            source=Path(directory)/'source.c';source.write_bytes(b'unchanged')
            for view in ('path','handle'):
                for field in ('st_mode','st_ctime_ns'):
                    calls=[]
                    def changed(value):
                        info=real_lstat(value) if view=='path' else real_fstat(value)
                        calls.append(value)
                        if len(calls)==1:return info
                        values={name:getattr(info,name,None) for name in fields}
                        values[field]=values[field]^stat.S_IXUSR if field=='st_mode' else values[field]+1
                        return SimpleNamespace(**values)
                    target,attribute=(Path,'lstat') if view=='path' else (renewal.os,'fstat')
                    with patch.object(target,attribute,changed):
                        phase='after read' if view=='path' else 'while reading'
                        with self.assertRaisesRegex(ValueError,'source changed '+phase):renewal.source_digest(source)
                    self.assertEqual(len(calls),2)

    def test_empty_source_keeps_hash_binding_and_artifacts_stay_nonempty(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as directory:
            root=Path(directory);source=root/'empty.c';source.write_bytes(b'')
            entries={'empty.c':hashlib.sha256(b'').hexdigest()};before=source.stat().st_mtime_ns
            renewal.check_hashes(root,entries)
            self.assertEqual(source.stat().st_mtime_ns,before)
            with self.assertRaisesRegex(ValueError,'source drift'):
                renewal.check_hashes(root,{'empty.c':'0'*64})
            with self.assertRaisesRegex(ValueError,'invalid artifact size/type'):
                renewal.legacy.guard.digest(source)
            with patch.object(renewal,'source_digest',side_effect=AssertionError('artifact used source policy')):
                with self.assertRaisesRegex(ValueError,'invalid artifact size/type'):
                    renewal.check_hashes(root,entries,artifacts=True)
                source.write_bytes(b'artifact')
                renewal.check_hashes(root,{'empty.c':hashlib.sha256(b'artifact').hexdigest()},artifacts=True)

    def test_source_digest_size_type_and_link_bounds(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as directory:
            root=Path(directory);source=root/'source.c'
            with patch.object(renewal,'MAX_SOURCE_BYTES',4):
                for value in (b'',b'abcd'):
                    source.write_bytes(value);self.assertEqual(renewal.source_digest(source),hashlib.sha256(value).hexdigest())
                source.write_bytes(b'abcde')
                with self.assertRaises(ValueError):renewal.source_digest(source)
            with self.assertRaises((ValueError,OSError)):renewal.source_digest(root)
            with self.assertRaises((ValueError,OSError)):renewal.source_digest(root/'missing.c')
            source.write_bytes(b'x');os.link(source,root/'alias.c')
            with self.assertRaises(ValueError):renewal.source_digest(source)
            with self.assertRaises(ValueError):renewal.check_hashes(root,{'source.c':hashlib.sha256(b'x').hexdigest()},artifacts='yes')

    def test_source_digest_exact_reads_and_mutation_rejection(self):
        real_open=Path.open;payload=b'x'*1048593
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as directory:
            source=Path(directory)/'source.c'
            for mutation in ('none','grow','shorten','mtime'):
                source.write_bytes(payload);requests=[];mutations=[]
                class Reader:
                    def __init__(self,stream):self.stream=stream
                    def fileno(self):return self.stream.fileno()
                    def read(self,size):
                        requests.append(size);chunk=self.stream.read(size)
                        if len(requests)==1:
                            if mutation=='grow':
                                with real_open(source,'ab') as out:out.write(b'y')
                                mutations.append(mutation)
                            elif mutation=='shorten':
                                with real_open(source,'wb') as out:out.write(b'z')
                                mutations.append(mutation)
                            elif mutation=='mtime':
                                info=source.stat();os.utime(source,ns=(info.st_atime_ns,info.st_mtime_ns+1000000000))
                                mutations.append(mutation)
                        return chunk
                @contextmanager
                def wrapped_open(path,mode='r',*args,**kwargs):
                    self.assertEqual(path,source);self.assertEqual(mode,'rb')
                    with real_open(path,mode,*args,**kwargs) as stream:yield Reader(stream)
                with patch.object(Path,'open',wrapped_open):
                    if mutation=='none':self.assertEqual(renewal.source_digest(source),hashlib.sha256(payload).hexdigest())
                    else:
                        reason={'grow':'source grew while reading','shorten':'source shortened while reading','mtime':'source changed while reading'}[mutation]
                        with self.assertRaisesRegex(ValueError,reason):renewal.source_digest(source)
                self.assertEqual(mutations,[] if mutation=='none' else [mutation])
                self.assertGreaterEqual(len(requests),1)
                self.assertLessEqual(len(requests),3)
                self.assertTrue(all(0<size<=1048576 for size in requests))
                if mutation=='none':self.assertEqual(requests,[1048576,17,1])

    def test_exact_reviewed_delta_not_learned_from_candidate(self):
        self.assertEqual(renewal.EXPECTED['build/reist-os.img'],'2b58094b7bc68eb261f18ab0cf053b4815f8528bc6e33ed6ca68e73232353bc7')
        self.assertEqual(renewal.EXPECTED['build/vmware/reist-os/reist-os-flat.vmdk'],'9f2998be4acc1ed6a8b7ab3051746fd14de1de06851575871422a0ad996309f5')
        self.assertEqual(renewal.PROGRAM_DIGEST,'7ba8d99a96ce6e242d9c07ed50907df5ceb8356b6c3387780dd1bb9db1997de5')
        self.assertEqual(renewal.EXPECTED['build/codex-agent/r345-js-colors/framebuffer/reist-os.img'],renewal.legacy.EXPECTED['build/codex-agent/r345-js-colors/framebuffer/reist-os.img'])

    def test_profile_restores_every_constant_on_success_and_failure(self):
        names=renewal.PROFILE.keys();before={name:getattr(renewal.legacy,name) for name in names}
        for fail in (False,True):
            try:
                with renewal.reviewed_profile():
                    for name,value in renewal.PROFILE.items():self.assertEqual(getattr(renewal.legacy,name),value)
                    cases=renewal.legacy.reference_cases()
                    self.assertEqual([c[1] for c in cases],['vmware','vmware','qemu','qemu'])
                    self.assertEqual([c[3] for c in cases],[False,False,False,True])
                    self.assertTrue(all(c[2].is_relative_to(renewal.ROOT) for c in cases))
                    self.assertEqual(cases[2][2],renewal.EVIDENCE/'qemu/reist-os.img')
                    if fail:raise ValueError('original failure')
            except ValueError as error:self.assertEqual(str(error),'original failure')
            for name,value in before.items():self.assertIs(getattr(renewal.legacy,name),value)

    def test_source_binding_real_files_hashes_inventory_and_no_writes(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as directory:
            root=Path(directory);source=root/'source.c';source.write_bytes(b'original')
            entries={'source.c':hashlib.sha256(b'original').hexdigest()}
            before=source.stat().st_mtime_ns
            renewal.check_hashes(root,entries)
            self.assertEqual(source.stat().st_mtime_ns,before)
            for bad in ({},{'../escape':entries['source.c']},{'source.c':'x'*64},{'source.c':'0'*64}):
                with self.assertRaises((ValueError,OSError)):renewal.check_hashes(root,bad)
            source.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'source drift'):renewal.check_hashes(root,entries)
            source.unlink()
            with self.assertRaises((ValueError,OSError)):renewal.check_hashes(root,entries)

    def test_json_rejects_duplicate_fields_and_capacity(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as directory:
            path=Path(directory)/'data.json'
            for contents in ('{"a":1,"a":2}',' '*1048577):
                path.write_text(contents)
                with self.assertRaises(ValueError):renewal.read_json(path)

    def test_exact_receipts_and_log_binding(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as directory:
            folder=Path(directory);gates=[dict(id=i,name='host'+str(i),argv=['python','test.py'],timeout=180) for i in range(1,18)]
            for g in gates[:12]:
                log=folder/f"gate-{g['id']:02d}.log";log.write_bytes(b'actual output')
                row=dict(g,result='PASS',exit_code=0,elapsed_seconds=1,log=log.relative_to(ROOT).as_posix(),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())
                (folder/f"gate-{g['id']:02d}.result.json").write_text(json.dumps(row))
            frozen=dict(gates=gates);self.assertEqual(len(renewal.admit_receipts(folder,frozen,12)),12)
            path=folder/'gate-04.result.json';good=path.read_text();original=json.loads(good)
            for key,value in (('result','FAIL'),('exit_code',1),('elapsed_seconds',181),('argv',['other']),('log_sha256','0'*64),('id',7)):
                row=dict(original);row[key]=value;path.write_text(json.dumps(row))
                with self.assertRaises(ValueError):renewal.admit_receipts(folder,frozen,12)
            path.write_text(good);(folder/'gate-04.log').write_bytes(b'different')
            with self.assertRaises(ValueError):renewal.admit_receipts(folder,frozen,12)
            path.unlink()
            with self.assertRaises((ValueError,OSError)):renewal.admit_receipts(folder,frozen,12)
            with self.assertRaises(ValueError):renewal.admit_receipts(folder,frozen,11)

    def test_no_guest_before_source_and_prior_gate_admission(self):
        with patch.object(renewal,'admission',side_effect=ValueError('stale source')),patch.object(renewal.legacy,'main') as run:
            with self.assertRaisesRegex(ValueError,'stale source'):renewal.qualify()
            run.assert_not_called()

    def test_failure_cannot_publish_reviewed_admission(self):
        with patch.object(renewal,'admission',side_effect=ValueError('failed gate')),patch.object(renewal,'write_json') as publish:
            with self.assertRaisesRegex(ValueError,'failed gate'):renewal.review()
            publish.assert_not_called()

if __name__=='__main__':unittest.main()
