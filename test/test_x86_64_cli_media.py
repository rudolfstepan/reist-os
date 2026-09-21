"""Host-only delivery admission, independent filesystem and publication tests."""
from pathlib import Path
import hashlib,inspect,json,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import check_x86_64_cli_media as check
import build_x86_64_cli_media as producer
import build_x86_64_app_files_media as media

class CliMediaTests(unittest.TestCase):
    def folder(self):return Path(tempfile.mkdtemp(prefix='bd-host-',dir=ROOT/'build/codex-agent'))

    def test_exact_twelve_accepted_inputs_and_no_compiler(self):
        values=producer.inputs(check.INPUT)
        self.assertEqual(len(values),12)
        for name in check.PINS:
            bad=dict(values);raw=bytearray(bad[name]);raw[-1]^=1;bad[name]=bytes(raw)
            with self.subTest(name=name),self.assertRaises(ValueError):check.input_binding(bad)
        for bad in (dict(values,extra=b'x'),{k:v for k,v in values.items() if k!='probe.prg'}):
            with self.assertRaises(ValueError):check.input_binding(bad)
        source=inspect.getsource(producer.selected.build)
        self.assertNotIn('zig',source);self.assertNotIn('build-x86_64-bootstrap',source)
        self.assertEqual(hashlib.sha256(values['probe.prg']).hexdigest(),check.PINS['probe.prg'])

    def test_independent_five_file_media_and_corruption(self):
        values=producer.inputs(check.INPUT);files=check.medium_files(values)
        raw=media.image('ext2-1k',files);check.data_volume(raw,values)
        for at in (1028,1036,1080,2048,2060,3072,4096,5248,6528+4,6528+40,
                   6528+92,21*1024+24,32*1024,1000*1024):
            bad=bytearray(raw);bad[at]^=1
            with self.subTest(at=at),self.assertRaises(ValueError):check.data_volume(bytes(bad),values)
        for bad in (raw[:-1],raw+b'x'):
            with self.assertRaises(ValueError):check.data_volume(bad,values)
        self.assertNotIn('image',check.data_volume.__code__.co_names)

    def test_old_profiles_stay_strict_and_foreign_profile_rejected(self):
        import check_x86_64_shell_media as old
        import check_x86_64_wide_shell_media as wide
        p=dict(version=1,architecture='x86_64',profile=check.PROFILE,attempt='shell-media-'+'a'*32,
               artifacts={n:{} for n in check.FILES},devices=check.DEVICES)
        check.admit_package(p)
        self.assertEqual(old.FILES['file-program.prg'],1280)
        self.assertEqual(wide.FILES['system.ext2'],1048576)
        for other in (old,wide):
            with self.assertRaises(ValueError):other.admit_package(p)
            with self.assertRaises(ValueError):check.admit_package(dict(p,profile=other.PROFILE))
        for raw in (b'[]',b' '*16385,b'{"x":1,"x":2}'):
            with self.assertRaises(ValueError):check.object_json(raw)

    def test_failed_publication_preserves_old_index(self):
        folder=self.folder();index=folder/'cli-media.json';index.write_bytes(b'old')
        candidate=folder/'shell-index-unit.json';candidate.write_bytes(b'new')
        with patch.object(producer.old,'run',side_effect=ValueError('rejected')),\
             patch.object(producer.selected.os,'replace') as replace:
            with self.assertRaises(ValueError):producer.publish(folder,candidate,'openssl',folder/'log')
            replace.assert_not_called()
        self.assertEqual(index.read_bytes(),b'old');self.assertEqual(candidate.read_bytes(),b'new')
        with patch.object(producer.old,'run'),patch.object(producer.selected.os,'replace',side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):producer.publish(folder,candidate,'openssl',folder/'log')
        self.assertEqual(index.read_bytes(),b'old')

    def test_canonical_resigned_corruption_cannot_pass_on_crypto_failure(self):
        import verify_x86_64_cli_delivery as verify
        self.assertEqual(verify.canonical_descriptor({'b':2,'a':1}),b'{"a":1,"b":2}\n')
        verify.require_ext2_failure(ValueError('application media EXT2 actual file/padding'))
        for reason in ('signed index identity','signature rejected','artifact bytes system.ext2','unrelated'):
            with self.assertRaises(ValueError):verify.require_ext2_failure(ValueError(reason))

    def test_gate_stops_once(self):
        import verify_x86_64_cli_delivery as verify
        frozen=dict(candidate='unit',commands=['python first','python second'],limits=[1,1])
        with patch.object(verify,'BASE',self.folder()),patch.object(verify,'binding',return_value=frozen),\
             patch.object(verify,'command',return_value=dict(passed=False,elapsed=0)) as command:
            with self.assertRaisesRegex(ValueError,'first failed'):verify.all_gates()
            self.assertEqual(command.call_count,1)
            with self.assertRaises(ValueError):verify.all_gates()
            self.assertEqual(command.call_count,1)

if __name__=='__main__':unittest.main()
