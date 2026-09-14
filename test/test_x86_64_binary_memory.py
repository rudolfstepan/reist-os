"""Execute the RAM-only QMP reader, mapping admission and capture integration."""
from pathlib import Path
from unittest.mock import Mock, patch
import json, struct, sys, tempfile, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import qemu_binary_memory as binary
import run_qemu_x86_64_boot_programs as transport


class BinaryTests(unittest.TestCase):
    def folder(self):
        base = ROOT / 'build/codex-agent/r83am-file-launch/binary-host'
        base.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(dir=base))

    def peer(self, *rows):
        peer = Mock()
        peer.recv.side_effect = [r if isinstance(r, bytes) else json.dumps(r).encode()+b'\n' for r in rows] + [b'']
        return peer

    def test_protocol_fragmentation_identity_and_status(self):
        peer = self.peer(b'{"QMP":', b'{"version":{},"capabilities":[]}}\n',
                         {'return': {}, 'id': 1}, {'event': 'STOP'},
                         {'return': {'name': 'native-test'}, 'id': 2},
                         {'return': {'running': False, 'status': 'debug'}, 'id': 3})
        with patch.object(binary.socket, 'create_connection', return_value=peer):
            client = binary.QMP(1234, 'native-test', binary.time.monotonic()+20)
            client.stopped()
            client.close()
        self.assertEqual([json.loads(c.args[0])['execute'] for c in peer.sendall.call_args_list],
                         ['qmp_capabilities', 'query-name', 'query-status'])
        peer.close.assert_called_once()

    def test_protocol_rejects_and_closes_failed_admission(self):
        greeting = {'QMP': {'version': {}, 'capabilities': []}}
        bad = [b'', b'x'*8193, b'[]\n', {'return': {}, 'id': True},
               {'return': {}, 'id': 9}, {'return': {}, 'error': {}, 'id': 1},
               {'error': {'class': 'GenericError'}, 'id': 1}]
        for row in bad:
            peer = self.peer(greeting, row)
            with self.subTest(row=str(row)[:40]), patch.object(binary.socket, 'create_connection', return_value=peer):
                with self.assertRaises((ValueError, OSError)):
                    binary.QMP(1234, 'native-test', binary.time.monotonic()+20)
                peer.close.assert_called_once()
        peer = self.peer(greeting, *[{'event': 'STOP'}]*33)
        with patch.object(binary.socket, 'create_connection', return_value=peer):
            with self.assertRaises(ValueError):binary.QMP(1234, 'native-test', binary.time.monotonic()+20)
        self.assertLessEqual(peer.recv.call_count, 34)

    def memory(self, physical=0x100000000, huge=False):
        # Native kernel tables live below128MiB, readable through HIGH.
        tables = {n: bytearray(4096) for n in (0x100000, 0x101000, 0x102000, 0x103000)}
        va = binary.DM+physical if physical >= 1<<32 else binary.HIGH+physical
        for table, child, shift in ((0x100000,0x101000,39),(0x101000,0x102000,30),(0x102000,0x103000,21)):
            struct.pack_into('<Q', tables[table], ((va>>shift)&511)*8,
                             (physical & ~((1<<21)-1)) | 0x83 if huge and shift==21 else child|3)
        for n in range(66):
            struct.pack_into('<Q', tables[0x103000], (((va>>12)+n)&511)*8, physical+n*4096|3)
        calls=[]
        def read(address, size):
            calls.append((address,size))
            offset=address-binary.HIGH
            page=offset&~4095
            if page in tables:return bytes(tables[page][offset&4095:(offset&4095)+size])
            return bytes((i%251 for i in range(size)))
        return va, tables, read, calls

    def test_actual_identity_running_deadline_and_command_rejection(self):
        greeting={'QMP': {'version': {}, 'capabilities': []}}
        for name,status in (('wrong',None),('native-test',{'running':True,'status':'running'}),
                           ('native-test',{'running':False,'status':'shutdown'})):
            peer=self.peer(greeting,{'return':{},'id':1},{'return':{'name':name},'id':2},
                           {'return':status,'id':3})
            with patch.object(binary.socket,'create_connection',return_value=peer),self.assertRaises(ValueError):
                client=binary.QMP(1234,'native-test',binary.time.monotonic()+20)
                try:client.stopped()
                finally:client.close()
            self.assertFalse(any(json.loads(c.args[0])['execute']=='pmemsave' for c in peer.sendall.call_args_list))
        client=object.__new__(binary.QMP);client.identifier=0;client.peer=Mock();client.deadline=0
        for command in ('cont','quit','human-monitor-command'):
            with self.assertRaises(ValueError):client.request(command,{})
        with self.assertRaises(TimeoutError):client.request('query-status',{})
        client.peer.sendall.assert_not_called()

    def test_actual_mapping_batched_4k_and_2m(self):
        for physical, huge in ((0xb05000,False),(0x100000000,False),(0x100000000,True)):
            va,tables,read,calls = self.memory(physical, huge)
            self.assertEqual(binary.translate(va,270336,0x100000,4096,read),physical)
            self.assertLessEqual(len(calls),4)
            self.assertLessEqual(sum(n for a,n in calls),552)
            if not huge:
                struct.pack_into('<Q', tables[0x103000], ((va>>12)&511)*8, physical+4096|3)
                with self.assertRaises(ValueError):binary.translate(va,32768,0x100000,4096,read)

    def test_mapping_rejects_ranges_flags_and_short_reads(self):
        va,tables,read,calls = self.memory()
        for address,size,root,ram in ((va,0,0x100000,4096),(va,270337,0x100000,4096),
            (binary.HIGH+0xa0000,32768,0x100000,4096),(binary.DM+0xf0000000,32768,0x100000,4096),
            (binary.DM+(5<<30)-4096,32768,0x100000,4096),(va,32768,0x100001,4096),
            (va,32768,0x100000,2048),(1<<64,32768,0x100000,4096)):
            with self.subTest(args=(address,size,root,ram)), self.assertRaises(ValueError):
                binary.translate(address,size,root,ram,read)
        with self.assertRaises(ValueError):binary.translate(va,32768,0x100000,4096,lambda a,n:b'')
        for entry in (0, 0x101000|0x83, (1<<48)|0x101003):
            struct.pack_into('<Q',tables[0x100000],256*8,entry)
            with self.assertRaises(ValueError):binary.translate(va,32768,0x100000,4096,read)

    def test_page_table_boundary_and_unaligned_bytes(self):
        physical=0x1001ff000;va,tables,unused,calls=self.memory(physical)
        # Final entry in one PT, seven entries in its successor.
        tables[0x104000]=bytearray(4096)
        struct.pack_into('<Q',tables[0x102000],8,0x104003)
        for n in range(8):struct.pack_into('<Q',tables[0x104000],n*8,physical+(n+1)*4096|3)
        reads=[]
        def read(a,n):
            p=a-binary.HIGH;reads.append((p,n));return bytes(tables[p&~4095][p&4095:(p&4095)+n])
        self.assertEqual(binary.translate(va+31,32768,0x100000,4096,read),physical+31)
        self.assertEqual(len(reads),5)
        self.assertEqual(reads[-2:],[(0x103ff8,8),(0x104000,64)])
        struct.pack_into('<Q',tables[0x104000],7*8,0)
        with self.assertRaises(ValueError):binary.translate(va+31,32768,0x100000,4096,read)

    def reader(self, *, compare=False, short=0):
        va,tables,read,calls=self.memory()
        folder=self.folder(); qmp=Mock()
        def save(physical,size,path):
            self.assertEqual(physical,0x100000000)
            path.write_bytes(read(va,size)[:size-short] if short>=0 else read(va,size)+b'!')
        qmp.save.side_effect=save
        reader=binary.Reader(1234,'native-test',folder,4096,read,lambda:0x100000,compare)
        reader.client=qmp
        return reader,qmp,va,read,folder

    def test_binary_bytes_ledger_equivalence_and_small_default(self):
        reader,qmp,va,read,folder=self.reader(compare=True)
        reader.client=None
        self.assertEqual(reader.read(va,8),read(va,8));qmp.stopped.assert_not_called()
        reader.client=qmp
        expected=read(va,32768)
        self.assertEqual(reader.read(va,32768),expected)
        self.assertEqual(qmp.stopped.call_count,2)
        rows=[json.loads(x) for x in (folder/'reads.jsonl').read_text().splitlines()]
        self.assertEqual(rows[0]['equivalence'],'high');self.assertEqual(rows[0]['bytes'],32768)
        self.assertEqual((folder/'ram-0001.bin').read_bytes(),expected)
        with patch.object(binary,'QMP',return_value=qmp) as connect:
            reader.read(va,32768)
            connect.assert_called_once()
        self.assertEqual(json.loads((folder/'reads.jsonl').read_text().splitlines()[1])['equivalence'],None)

    def test_each_dump_reconnects_before_guest_can_accumulate_events(self):
        reader,qmp,va,read,folder=self.reader()
        reader.client=None
        with patch.object(binary,'QMP',return_value=qmp) as connect:
            for _ in range(40):
                self.assertEqual(reader.read(va,32768),read(va,32768))
                self.assertIsNone(reader.client)
        self.assertEqual(connect.call_count,40);self.assertEqual(qmp.close.call_count,40)

    def test_stop_scoped_connection_is_reused_only_until_original_returns(self):
        reader,qmp,va,read,folder=self.reader();reader.client=None
        def original(hook):
            self.assertEqual(reader.read(va,32768),read(va,32768))
            self.assertEqual(reader.read(va,32768),read(va,32768))
            return hook
        stopped=getattr(reader,'wrap_stop',lambda fn:fn)(original)
        with patch.object(binary,'QMP',return_value=qmp) as connect:
            self.assertIs(stopped(False),False)
            self.assertEqual(connect.call_count,1);self.assertEqual(qmp.close.call_count,1)
            self.assertIsNone(reader.client)
            self.assertIs(stopped(True),True)
            self.assertEqual(connect.call_count,2);self.assertEqual(qmp.close.call_count,2)
        self.assertEqual(qmp.stopped.call_count,8) # Pre/post for every read, not just every stop.
        self.assertEqual(len(list(folder.glob('ram-*.bin'))),4)

    def test_stop_scope_exception_invalid_reply_and_nested_scope_fail_closed(self):
        for kind in ('callback','short','nested'):
            reader,qmp,va,read,folder=self.reader(short=1 if kind=='short' else 0);reader.client=None
            def original(hook):
                reader.read(va,32768)
                if kind=='nested':return reader.wrap_stop(lambda h:False)(hook)
                raise ValueError('original callback')
            with patch.object(binary,'QMP',return_value=qmp),self.assertRaises(ValueError):
                reader.wrap_stop(original)(None)
            self.assertIsNone(reader.client);self.assertFalse(reader.in_stop)
            qmp.close.assert_called_once()
            self.assertTrue(reader.failed)
            with self.assertRaises(ValueError):reader.wrap_stop(lambda h:False)(None)

    def test_fail_before_export_and_no_fallback(self):
        for reason in ('running','mapping','existing','count','bytes'):
            reader,qmp,va,read,folder=self.reader()
            if reason=='running':qmp.stopped.side_effect=ValueError('running')
            if reason=='mapping':va=binary.DM+0xf0000000
            if reason=='existing':(folder/'ram-0001.bin').write_bytes(b'keep')
            if reason=='count':reader.count=2048
            if reason=='bytes':reader.total=128*1024*1024
            with self.subTest(reason=reason),self.assertRaises(ValueError):reader.read(va,32768)
            qmp.save.assert_not_called()
        for short in (1,-1):
            reader,qmp,va,read,folder=self.reader(short=short)
            with self.assertRaises(ValueError):reader.read(va,32768)
            self.assertFalse((folder/'reads.jsonl').exists())
            with self.assertRaises(ValueError):reader.read(va,8)
            qmp.close.assert_called_once()
        reader,qmp,va,read,folder=self.reader(compare=True)
        qmp.save.side_effect=lambda p,n,f:f.write_bytes(bytes(n))
        with self.assertRaises(ValueError):reader.read(va,32768)

    def test_default_capture_and_opt_in_forwarding(self):
        folder=self.folder()
        with patch.object(transport,'_capture_run',return_value=('a','b')) as run:
            transport.capture(ROOT/'build/a.elf',folder,'code',4096)
            self.assertNotIn('binary_memory',run.call_args.kwargs)
            transport.capture(ROOT/'build/a.elf',folder,'code',4096,binary_memory='full')
            self.assertEqual(run.call_args.kwargs['binary_memory'],'full')
        body='python\ndef mem(a,n):return b"original"\nend\ncontinue\n'
        args,wrapped=binary.configure(body,folder,4096,'equivalence')
        self.assertEqual(args[0],'-qmp');self.assertIn('127.0.0.1:',args[1])
        self.assertTrue(wrapped.startswith(body[:-len('end\ncontinue\n')]))
        self.assertEqual(wrapped.count('mem=binary_reader.read'),1)
        with self.assertRaises(ValueError):binary.configure('continue\n',self.folder(),4096,'full')

    def test_complete_oracle_and_media_failure_paths_preserved(self):
        import run_qemu_x86_64_file_launch as launch
        import run_qemu_x86_64_pio as pio
        import ast
        code='python\n'+launch.observer_body()+'\nend\ncontinue\n'
        args,wrapped=binary.configure(code,self.folder(),4096,'full')
        prefix=code[:-len('end\ncontinue\n')]
        self.assertTrue(wrapped.startswith(prefix))
        ast.parse(wrapped[len('python\n'):-len('end\ncontinue\n')])
        class Fixture:
            def __init__(self):self.calls=[]
            def arguments(self,folder):return []
            def verify(self,stage):self.calls.append(stage)
        for mode in ('full','equivalence'):
            media=Fixture()
            with patch.object(pio,'Fixture',Fixture),patch.object(transport,'_capture_run',side_effect=ValueError('export')):
                with self.assertRaises(ValueError):transport.capture(ROOT/'build/a.elf',self.folder(),code,4096,media,binary_memory=mode)
            self.assertEqual(media.calls,['before','after'])

    def test_binary_attempt_reservation_requires_real_correction(self):
        import diagnose_x86_64_file_transport as diagnostic
        source={name:'a' for name in ('scripts/qemu_binary_memory.py','scripts/run_qemu_x86_64_boot_programs.py',
                                     'scripts/run_qemu_x86_64_file_launch.py','docs/test')}
        base=self.folder()
        first=diagnostic.reserve_binary(base,'equivalence',source)
        (first/'summary.json').write_text(json.dumps(dict(kind='equivalence',passed=False,source_sha256=source)))
        doc_change=dict(source,**{'docs/test':'b'})
        with self.assertRaises(ValueError):diagnostic.reserve_binary(base,'equivalence',doc_change)
        with self.assertRaises(ValueError):diagnostic.reserve_binary(base,'full',source)
        changed=dict(source,**{'scripts/qemu_binary_memory.py':'b'})
        second=diagnostic.reserve_binary(base,'equivalence',changed)
        (second/'summary.json').write_text(json.dumps(dict(kind='equivalence',passed=False,source_sha256=changed)))
        third_source=dict(source,**{'scripts/qemu_binary_memory.py':'c'})
        third=diagnostic.reserve_binary(base,'equivalence',third_source)
        (third/'summary.json').write_text(json.dumps(dict(kind='equivalence',passed=True,source_sha256=third_source)))
        fourth=diagnostic.reserve_binary(base,'full',third_source)
        (fourth/'summary.json').write_text(json.dumps(dict(kind='full',passed=True,source_sha256=third_source)))
        with self.assertRaises(ValueError):diagnostic.reserve_binary(base,'full',dict(source,**{'scripts/qemu_binary_memory.py':'d'}))


if __name__=='__main__':unittest.main()
