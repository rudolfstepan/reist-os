"""Native media admission, independent contents and publication regressions."""
from pathlib import Path
import copy
import json
import shutil
import struct
import subprocess
import sys
import unittest
import uuid
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build_x86_64_boot_media as producer
import verify_x86_64_boot_media as verifier
import run_qemu_x86_64_boot_media as guest


class NativeBootMediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=ROOT/'build/codex-agent/r83ab-media'/('host-'+uuid.uuid4().hex)
        cls.folder.mkdir(parents=True)
        command=['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
                 '-NativeProcesses','-NativeIPC','-NativeRAM','-NativeHeap',
                 '-OutputDirectory',cls.folder.relative_to(ROOT).as_posix()]
        with (cls.folder/'fixture-build.log').open('wb') as log:
            built=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=60,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if built.returncode:raise RuntimeError('native fixture compile failed: '+str(cls.folder))
        cls.directory=cls.folder/'x86_64'
        cls.nasm=shutil.which('nasm') or 'C:/tools/nasm-3.02/nasm.exe'
        cls.openssl=shutil.which('openssl') or 'openssl'
        cls.media=producer.build(cls.directory,cls.nasm,cls.openssl)
        cls.index=cls.directory/'native-media.json'
        cls.original=cls.index.read_bytes()

    def test_native_package_identity(self):
        self.assertEqual(producer.ARCHITECTURE,'x86_64')
        self.assertEqual(verifier.VERSION,1)
        self.assertEqual(verifier.verify(self.directory,openssl=self.openssl),self.media)
        self.assertEqual(len(json.loads(self.original)['package']['artifacts']),14)

    def test_each_artifact_and_signature_tamper_rejected(self):
        names=[*verifier.FILES,'package.json','package.json.sig']
        for name in names:
            with self.subTest(name=name):
                path=self.media/name
                with path.open('r+b') as stream:
                    byte=stream.read(1);stream.seek(0);stream.write(bytes([byte[0]^1]))
                try:
                    with self.assertRaises(ValueError):verifier.verify(self.directory,openssl=self.openssl)
                finally:
                    with path.open('r+b') as stream:stream.write(byte)

    def test_index_bounds_paths_duplicates_and_signature_binding(self):
        original=json.loads(self.original)
        mutations=[]
        for field,value in (('version',True),('architecture','i386'),('profile','release'),
                            ('attempt','../escape'),('attempt','C:\\escape')):
            item=copy.deepcopy(original);item['package'][field]=value;mutations.append(json.dumps(item).encode())
        item=copy.deepcopy(original);item['signature']='00'*256;mutations.append(json.dumps(item).encode())
        item=copy.deepcopy(original);item['package']['artifacts'].pop('reist-x86_64.img');mutations.append(json.dumps(item).encode())
        mutations += [b'[]',b'{}',b' '*16385,b'{"package":{},"package":{},"signature":""}']
        for raw in mutations:
            with self.subTest(raw=raw[:60]):
                self.index.write_bytes(raw)
                try:
                    with self.assertRaises((ValueError,TypeError)):verifier.verify(self.directory,openssl=self.openssl)
                finally:self.index.write_bytes(self.original)
        with self.assertRaises(ValueError):verifier.exact_path(self.directory,'../outside')
        # Same-volume junctions are resolved too; no privileged symlink creation.
        with mock.patch.object(Path,'is_symlink',return_value=True):
            with self.assertRaises(ValueError):verifier.exact_path(self.directory,'native-media.json')
            with self.assertRaises(ValueError):producer.read_input(self.directory,producer.CORE)

    def test_actual_fat_programs_and_mirrored_chain_failures(self):
        for is_fat32,name,start in ((True,'reist-x86_64.img',8192*512),(False,'reist-x86_64-floppy.img',0)):
            with (self.media/name).open('r+b') as stream:
                for path,artifact in verifier.PROGRAMS.items():
                    self.assertEqual(verifier.fat_file(stream,start,path,is_fat32),(self.media/artifact).read_bytes())
                stream.seek(start);boot=stream.read(512)
                reserved=struct.unpack_from('<H',boot,14)[0]
                cluster=struct.unpack_from('<I',boot,44)[0] if is_fat32 else 2
                offset=start+reserved*512+(cluster*4 if is_fat32 else cluster+cluster//2)
                stream.seek(offset);byte=stream.read(1)
                stream.seek(offset);stream.write(bytes([byte[0]^1]));stream.flush()
                try:
                    with self.assertRaises(ValueError):verifier.fat_file(stream,start,'bin/shell.prg',is_fat32)
                finally:stream.seek(offset);stream.write(byte);stream.flush()

    def test_stripped_user_elf64_and_wx_admission(self):
        for name in verifier.PROGRAMS.values():
            raw=(self.media/name).read_bytes();verifier.user_elf(raw)
            ph=struct.unpack_from('<Q',raw,32)[0]
            mutations=((4,'B',1),(16,'H',3),(18,'H',3),(24,'Q',0),(56,'H',17),
                       (ph+4,'I',7),(ph+32,'Q',1048577),(ph+16,'Q',0xffffffffffffffff))
            for offset,fmt,value in mutations:
                changed=bytearray(raw);struct.pack_into('<'+fmt,changed,offset,value)
                with self.assertRaises(ValueError):verifier.user_elf(changed)

    def test_vm_cannot_acquire_ambient_devices_or_external_extents(self):
        vmx=(self.media/'reist-x86_64.vmx').read_text()
        disk=(self.media/'reist-x86_64.vmdk').read_text()
        verifier.verify_vm_configuration(vmx,disk)
        for bad in (vmx.replace('numvcpus = "1"','numvcpus = "4"'),
                    vmx.replace('usb.generic.allowHID = "FALSE"','usb.generic.allowHID = "TRUE"'),
                    vmx+'ethernet1.present = "TRUE"\n',vmx+'sharedFolder0.hostPath = "C:/"\n'):
            with self.assertRaises(ValueError):verifier.verify_vm_configuration(bad,disk)
        for bad in (disk.replace('reist-x86_64.img','../other.img'),disk+'RW 1 FLAT "foreign" 0\n',
                    disk+'parentFileNameHint="foreign"\n'):
            with self.assertRaises(ValueError):verifier.verify_vm_configuration(vmx,bad)

    def test_failed_consumer_preserves_last_published_attempt(self):
        previous=set(self.directory.glob('native-media-*'))
        original_run=producer.run
        def reject_consumer(command,log):
            if 'verify_x86_64_boot_media.py' in str(command[1]):raise ValueError('injected consumer rejection')
            return original_run(command,log)
        with mock.patch.object(producer,'run',side_effect=reject_consumer):
            with self.assertRaisesRegex(ValueError,'injected consumer rejection'):
                producer.build(self.directory,self.nasm,self.openssl)
        self.assertEqual(self.index.read_bytes(),self.original)
        self.assertTrue(previous<set(self.directory.glob('native-media-*')))
        self.assertEqual(verifier.verify(self.directory,openssl=self.openssl),self.media)

    def test_bios_oracle_rejects_partial_success_and_wrong_failure(self):
        # The inherited native oracle remains authoritative, not copied here.
        prefix='x86 native BIOS loader\nVerifying kernel SHA-256/RSA-PSS...\n'
        positive=prefix+'Loading ELF32 kernel...\nStarting kernel...\nREIST_X86_64_LONG_MODE_BOOT_OK\n'
        with mock.patch.object(guest.ipc,'validate',return_value=[{'passed':'inherited'}]) as native:
            self.assertEqual(guest.validate(positive,'hdd','normal'),[{'passed':'inherited'}])
            native.assert_called_once_with(positive,0)
        for layout,case,marker,count in (('hdd','signatures',guest.SIGNATURE,2),
                ('hdd','digest',guest.DIGEST,2),('hdd','manifest',guest.MANIFEST,2),
                ('floppy','signatures',guest.SIGNATURE,1),('floppy','digest',guest.DIGEST,1)):
            trace=prefix+marker+'\n'+(guest.FALLBACK+'\n'+marker+'\n' if count==2 else '')
            self.assertEqual(guest.validate(trace,layout,case),[])
            for bad in (trace+trace,trace+'Starting kernel...\n',trace.replace(marker,'MISSING',1),
                        trace+'REIST_X86_64_LONG_MODE_BOOT_OK\n'):
                with self.assertRaises(ValueError):guest.validate(bad,layout,case)
        with self.assertRaises(ValueError):guest.validate(positive,'hdd','normal')

    def test_premature_vm_exit_cannot_pass_negative_lease(self):
        folder=self.folder/'early-vm-exit';folder.mkdir()
        (folder/'guest.log').write_text('x86 native BIOS loader\n'+guest.SIGNATURE+'\n'+
            guest.FALLBACK+'\n'+guest.SIGNATURE+'\n',encoding='ascii')
        vm=mock.Mock();vm.poll.return_value=0
        with mock.patch.object(guest.subprocess,'Popen',return_value=vm) as spawn, \
             mock.patch.object(guest,'terminate_bounded') as terminate:
            with self.assertRaisesRegex(ValueError,'exited before witness lease'):
                guest.capture(self.media/'reist-x86_64.img','hdd',folder,False,4096)
            terminate.assert_called_once_with(vm)
            command=spawn.call_args.args[0]
            self.assertIn('-snapshot',command);self.assertNotIn('-kernel',command)
            self.assertEqual(command[command.index('-display')+1],'none')


if __name__=='__main__':unittest.main()
