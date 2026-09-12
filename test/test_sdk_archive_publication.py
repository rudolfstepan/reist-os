"""Real Windows ACL inheritance and fail-closed atomic SDK publication."""
from pathlib import Path
import io
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from publish_sdk_archive import publish_archive, MAX_ARCHIVE_BYTES, _copy_archive


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.folder = ROOT/'build/codex-agent/b11-sdk-publication'/('host-'+uuid.uuid4().hex)
        self.folder.mkdir(parents=True)
        self.source = self.folder/'candidate.a'
        self.target = self.folder/'installed.a'
        self.data = b'!<arch>\n'+bytes(range(256))*5000
        self.source.write_bytes(self.data)
        self.target.write_bytes(b'old accepted archive')

    def test_exact_bytes_atomic_replacement(self):
        publish_archive(self.source,self.target)
        self.assertEqual(self.target.read_bytes(),self.data)
        self.assertEqual(self.source.read_bytes(),self.data)
        self.assertEqual(sorted(p.name for p in self.folder.iterdir()),['candidate.a','installed.a'])

    def test_failures_preserve_old_and_remove_only_own_stage(self):
        for function in ('os.fsync','os.replace','_copy_archive'):
            with self.subTest(function=function):
                with patch('publish_sdk_archive.'+function,side_effect=OSError('injected failure')):
                    with self.assertRaises(OSError): publish_archive(self.source,self.target)
                self.assertEqual(self.target.read_bytes(),b'old accepted archive')
                self.assertEqual(self.source.read_bytes(),self.data)
                self.assertEqual(len(list(self.folder.iterdir())),2)

    def test_invalid_and_aliased_inputs(self):
        with self.assertRaises(ValueError): publish_archive(self.source,self.source)
        for data in (b'',b'not ar!!'):
            self.source.write_bytes(data)
            with self.assertRaises(ValueError): publish_archive(self.source,self.target)
            self.assertEqual(self.target.read_bytes(),b'old accepted archive')
        with self.source.open('wb') as stream:
            stream.write(b'!<arch>\n'); stream.truncate(MAX_ARCHIVE_BYTES+1)
        with self.assertRaises(ValueError): publish_archive(self.source,self.target)
        self.assertEqual(len(list(self.folder.iterdir())),2)

    def test_exclusive_stage_collision_preserves_foreign_file(self):
        collision = self.folder/'.installed.a.publish-fixed.tmp'
        collision.write_bytes(b'foreign owner')
        with patch('publish_sdk_archive.uuid.uuid4') as token:
            token.return_value.hex = 'fixed'
            with self.assertRaises(FileExistsError): publish_archive(self.source,self.target)
        self.assertEqual(collision.read_bytes(),b'foreign owner')
        self.assertEqual(self.target.read_bytes(),b'old accepted archive')

    def test_copy_rejects_truncation_and_growth(self):
        for payload in (b'short',b'too many bytes'):
            with self.assertRaises(ValueError):
                _copy_archive(io.BytesIO(payload),io.BytesIO(),8)

    @unittest.skipUnless(os.name=='nt' and sys.version_info>=(3,13),'Windows secure temporary-directory profile')
    def test_private_temp_legacy_regression_and_actual_inherited_publication(self):
        def protected(path):
            quoted=str(path).replace("'","''")
            result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',
                f"([System.IO.File]::GetAccessControl('{quoted}')).AreAccessRulesProtected"],
                capture_output=True,text=True,errors='replace',timeout=10,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn(result.stdout.strip(),('True','False'))
            return result.stdout.strip()=='True'
        self.assertFalse(protected(self.folder))
        with tempfile.TemporaryDirectory(dir=self.folder) as private:
            candidate=Path(private)/'private.a';candidate.write_bytes(self.data)
            self.assertTrue(protected(Path(private)))
            # The child inherits the private ACL; moving it out pins those
            # inherited owner/system/admin rules as a protected destination ACL.
            self.assertFalse(protected(candidate))
            legacy=self.folder/'legacy.a';candidate.replace(legacy)
            self.assertTrue(protected(legacy),'actual old replace retains protected ACL')
            publish_archive(legacy,self.target)
            self.assertFalse(protected(self.target),'ordinary sibling inherits destination ACL')
            self.assertEqual(self.target.read_bytes(),self.data)
            self.assertTrue(protected(legacy),'source ACL must not be changed')

    def test_all_three_recipes_share_publisher_and_invalidate_cache(self):
        for name in ('math','text','js'):
            source=(ROOT/f'scripts/build_user_{name}.py').read_text()
            self.assertIn('publish_archive(candidate, library)',source)
            self.assertNotIn('candidate.replace(library)',source)
            self.assertIn('Path(publish_archive.__code__.co_filename)',source)


if __name__=='__main__': unittest.main()
