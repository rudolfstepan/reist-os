"""Relocated SDK header must compile without borrowing source-tree headers."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import unittest
import uuid
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build_user_sdk as sdk
from build_user_program import find_zig,freestanding_compile_prefix


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.folder=ROOT/'build/codex-agent/b11-sdk-publication'/('headers-'+uuid.uuid4().hex)
        self.include=self.folder/'relocated/usr/include'
        self.include.mkdir(parents=True)
        self.headers=((sdk.STORAGE_INCLUDE_ROOT,sdk.STORAGE_INCLUDE_ROOT/'reist/fat32_transaction.h'),
                      (sdk.CORE_INCLUDE_ROOT,sdk.CORE_INCLUDE_ROOT/'reist/abi/syscall.h'))

    def compile(self,includes,label,language):
        fixture=self.folder/'fixture.c'
        fixture.write_text('#include <reist/fat32_transaction.h>\n'
            '#include <stddef.h>\n'
            'unsigned layout(unsigned i) { const unsigned sizes[]={sizeof(ata_journal_record_t),'
            'sizeof(ata_undo_journal_t),sizeof(reist_fat32_transaction_t),'
            'sizeof(reist_fat32_owned_transaction_io_t),offsetof(reist_fat32_transaction_t,io),'
            'offsetof(reist_fat32_transaction_t,admission),ATA_JOURNAL_MAX_ENTRIES,ATA_JOURNAL_VERSION};'
            'return i<8?sizes[i]:0; }\n',encoding='ascii')
        env=os.environ.copy()
        env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(self.folder/'cache')
        command=freestanding_compile_prefix(find_zig(),includes,include_repository_sdk=False)
        output=self.folder/(label+'.o')
        result=subprocess.run([*command,'-x',language,'-std='+('c11' if language=='c' else 'c++20'),
            '-Werror','-c',str(fixture),'-o',str(output)],capture_output=True,text=True,errors='replace',
            env=env,cwd=self.folder,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (self.folder/(label+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
        return result,output

    def test_actual_old_export_failure_and_relocated_c_cpp_layout(self):
        for root,header in self.headers:
            destination=self.include/header.relative_to(root)
            destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(header,destination)
        old,_=self.compile([self.include],'legacy','c')
        self.assertNotEqual(old.returncode,0)
        self.assertIn('ata_journal.h',old.stderr)
        sdk.install_public_headers(self.include,self.headers)
        dependency=self.include/'reist/internal/ata_journal.h'
        self.assertEqual(dependency.read_bytes(),(ROOT/'drivers/block/ata_journal.h').read_bytes())
        generated=self.include/'reist/fat32_transaction.h'
        self.assertNotIn(b'../../../../drivers',generated.read_bytes())
        for language in ('c','c++'):
            native,obj1=self.compile([sdk.STORAGE_INCLUDE_ROOT,sdk.CORE_INCLUDE_ROOT],'source-'+language,language)
            exported,obj2=self.compile([self.include],'export-'+language,language)
            self.assertEqual(native.returncode,0,native.stderr)
            self.assertEqual(exported.returncode,0,exported.stderr)
            self.assertEqual(obj1.read_bytes(),obj2.read_bytes(),'actual C/C++ layout machine code must match')
        stamps={p:p.stat().st_mtime_ns for p in self.include.rglob('*.h')}
        sdk.install_public_headers(self.include,self.headers)
        self.assertEqual(stamps,{p:p.stat().st_mtime_ns for p in self.include.rglob('*.h')})

    def test_unexpected_dependency_pattern_fails_before_publication(self):
        header=self.headers[0][1];original=Path.read_bytes
        for payload in (b'no expected include',original(header)*2):
            with patch.object(Path,'read_bytes',lambda p:payload if p==header else original(p)):
                with self.assertRaises(ValueError):sdk.install_public_headers(self.include,self.headers)
            self.assertEqual(list(self.include.rglob('*.h')),[])


if __name__=='__main__': unittest.main()
