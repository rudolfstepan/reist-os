"""Independent media-layout checks and actual disposable COW integrity."""
from pathlib import Path
import hashlib,json,struct,sys,unittest,uuid
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import build_x86_64_fs_media as media
import run_qemu_x86_64_pio as pio
class FilesystemMedia(unittest.TestCase):
    def test_file_bytes_chains_and_actual_cow(self):
        program=bytes(n&255 for n in range(1536))
        base=ROOT/'build/codex-agent/r83am-file-launch'/('media-host-'+uuid.uuid4().hex);base.mkdir(parents=True)
        for layout in media.LAYOUTS:
            raw=media.image(layout,program=program)
            if layout.startswith('fat'):
                fat32=layout=='fat32';reserved=32 if fat32 else 1;fat=544 if fat32 else 9
                root=(reserved+2*fat)*512;data=root+(512 if fat32 else 14*512)
                self.assertEqual(raw[root:root+11],b'BOOT    PRG')
                self.assertEqual(raw[data:data+1536],program)
                for copy in range(2):
                    for cluster in range(3 if fat32 else 2,6 if fat32 else 5):
                        off=(reserved+copy*fat)*512
                        value=struct.unpack_from('<I',raw,off+cluster*4)[0]&0xfffffff if fat32 else (struct.unpack_from('<H',raw,off+cluster+cluster//2)[0]>>(4 if cluster&1 else 0))&0xfff
                        self.assertEqual(value,cluster+1 if cluster<(5 if fat32 else 4) else 0xfffffff if fat32 else 0xfff)
            else:
                bs=1024<<struct.unpack_from('<I',raw,1048)[0];off=5*bs+11*128
                self.assertEqual(struct.unpack_from('<I',raw,off+4)[0],1536)
                self.assertEqual(raw[22*bs:22*bs+1536],program)
                if bs==1024:self.assertEqual(struct.unpack_from('<I',raw,off+44)[0],23)
            folder=base/layout;folder.mkdir();fixture=pio.Fixture(folder,filesystem=layout,file_program=program)
            fixture.verify('before');fixture.verify('after')
            self.assertEqual(fixture.base.read_bytes(),raw)
            fixture.file_program=bytes([program[0]^1])+program[1:]
            with self.assertRaisesRegex(ValueError,'base changed'):fixture.verify('changed-program')
        for bad in (False,'ELF',b'',bytes(63),bytes(1538),bytearray(64)):
            with self.assertRaises(ValueError):media.image('fat12',program=bad)
        with self.assertRaises(ValueError):pio.Fixture(base,file_program=program)

    def test_standard_geometry_and_readonly_mutations(self):
        for layout in media.LAYOUTS:
            with self.subTest(layout=layout):
                raw=media.image(layout);bad=media.image(layout,True)
                self.assertEqual(sum(a!=b for a,b in zip(raw,bad)),1)
                self.assertEqual(len(raw),len(bad));self.assertLessEqual(len(raw),70000*512)
                if layout.startswith('fat'):
                    u16=lambda p:struct.unpack_from('<H',raw,p)[0]
                    u32=lambda p:struct.unpack_from('<I',raw,p)[0]
                    self.assertEqual((u16(11),raw[13],raw[16]),(512,1,2))
                    total=u16(19) or u32(32);reserved=u16(14);fat=u16(22) or u32(36)
                    root_sectors=(u16(17)*32+511)//512;clusters=total-reserved-2*fat-root_sectors
                    self.assertTrue(clusters<4085 if layout=='fat12' else clusters>=65525)
                    self.assertEqual(len(raw),total*512);self.assertEqual(raw[510:512],b'\x55\xaa')
                    self.assertEqual(raw[reserved*512:(reserved+fat)*512],raw[(reserved+fat)*512:(reserved+2*fat)*512])
                    root=(reserved+2*fat)*512
                    self.assertEqual(raw[root:root+11],b'README  TXT')
                    data=(reserved+2*fat+(1 if layout=='fat32' else root_sectors))*512
                    self.assertEqual(raw[data:data+len(media.CONTENT)],media.CONTENT)
                else:
                    bs=1024<<struct.unpack_from('<I',raw,1048)[0]
                    self.assertEqual(bs,{'ext2-1k':1024,'ext2-2k':2048,'ext2-4k':4096}[layout])
                    self.assertEqual(struct.unpack_from('<H',raw,1080)[0],0xef53)
                    table=struct.unpack_from('<I',raw,(2 if bs==1024 else 1)*bs+8)[0]
                    inode=table*bs+11*128
                    self.assertEqual(struct.unpack_from('<I',raw,inode+4)[0],len(media.CONTENT))
                    data=struct.unpack_from('<I',raw,inode+40)[0]*bs
                    self.assertEqual(raw[data:data+len(media.CONTENT)],media.CONTENT)
                    self.assertEqual(raw[21*bs+32:21*bs+42],b'readme.txt')
        for bad in (None,False,1,'ext4','../disk','fat16'):
            with self.assertRaises(ValueError):media.image(bad)
        for bad in (None,1,'true'):
            with self.assertRaises(ValueError):media.image('fat12',bad)
    def test_actual_cow_all_layouts_and_corruption(self):
        base=ROOT/'build/codex-agent/r83al-filesystem'/('media-host-'+uuid.uuid4().hex);base.mkdir(parents=True)
        for layout in media.LAYOUTS:
            folder=base/layout;folder.mkdir();fixture=pio.Fixture(folder,filesystem=layout)
            fixture.verify('before');fixture.verify('after')
            report=json.loads((folder/'media-after.json').read_text())
            self.assertTrue(report['passed']);self.assertEqual(report['logical_bytes'],len(media.image(layout)))
            self.assertEqual(report['overlay_allocated_data'],0)
            self.assertEqual(report['base_sha256'],hashlib.sha256(media.image(layout)).hexdigest())
            args=fixture.arguments(folder)
            nodes=[json.loads(args[i+1]) for i,v in enumerate(args) if v=='-blockdev']
            self.assertTrue(nodes[0]['read-only'] and nodes[1]['read-only'])
            self.assertEqual(nodes[2]['backing'],'pio-base')
            fixture.malformed=True
            with self.assertRaisesRegex(ValueError,'base changed'):fixture.verify('changed-selector')
            fixture.malformed=False
            original=fixture.run
            def allocated(*args):
                return json.dumps([dict(start=0,length=len(media.image(layout)),depth=0)]) if args[0]=='map' else original(*args)
            fixture.run=allocated
            with self.assertRaisesRegex(ValueError,'allocated overlay'):fixture.verify('allocated-control')
        for options in (dict(filesystem='fat12',block=True),dict(filesystem='../raw'),dict(malformed=True)):
            with self.assertRaises(ValueError):pio.Fixture(base,**options)
if __name__=='__main__':unittest.main()
