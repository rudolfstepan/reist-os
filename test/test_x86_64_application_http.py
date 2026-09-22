"""Actual native HTTP implementation tests, bounded C behavior at O0/O2."""
from pathlib import Path
import os,subprocess,sys,unittest,uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_sdk import find_zig

class ApplicationHTTP(unittest.TestCase):
    def host(self,name,entry,sources,flags=(),source=None):
        folder=ROOT/'build/codex-agent/r83bq-application-http'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True);env=os.environ.copy()
        if source is not None:
            entry=str(folder/(name+'.c'));Path(entry).write_text(source,encoding='utf-8')
        env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        for opt in ('0','2'):
            exe=folder/(name+'-O'+opt+'.exe')
            cmd=[str(find_zig()),'cc','-std=c11','-O'+opt,'-Wall','-Wextra','-Werror',
                 '-Wno-unused-command-line-argument','-UNDEBUG','-Iuserspace/sdk/include','-I.','-Iuserspace/tls/include',*flags,entry,*sources,'-o',str(exe)]
            p=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,timeout=120)
            (folder/('compile-O'+opt+'.log')).write_bytes(p.stdout+p.stderr)
            self.assertEqual(p.returncode,0,(p.stdout+p.stderr).decode(errors='replace')[-1800:])
            p=subprocess.run([str(exe)],cwd=ROOT,capture_output=True,timeout=30)
            (folder/('run-O'+opt+'.log')).write_bytes(p.stdout+p.stderr)
            self.assertEqual(p.returncode,0,(p.stdout+p.stderr).decode(errors='replace')[-1800:])
    def test_native_header_quota(self):
        self.host('http-quota','test/x86_64_application_http_host.c',
                  ['userspace/programs/curl_http.c','userspace/sdk/lib/x86_64/application_http.c'],['-DREIST_NATIVE_APP_HTTP'])
    def test_legacy_http_parser(self):
        self.host('http-legacy','test/test_curl_http_host.c',['userspace/programs/curl_http.c'])
    def test_eleven_file_media(self):
        import build_x86_64_application_http_media as producer
        import check_x86_64_application_http_media as consumer
        files={name:bytes([n+1])*(20 if name=='data.txt' else 14*1024)
               for n,name in enumerate(consumer.NAMES)}
        raw=producer.image('ext2-1k',files)
        self.assertEqual(consumer.verify_volume(raw,files)['files'],11)
        self.assertEqual(raw[33*1024:34*1024],files['boot.prg'][:1024])
        for offset in (33*1024,32*1024,4098,1036):
            bad=bytearray(raw);bad[offset]^=1
            with self.assertRaises(ValueError):consumer.verify_volume(bytes(bad),files)

    def test_actual_curl_program(self):
        self.host('curl-program','test/x86_64_application_http_platform_host.c',
            ['userspace/programs/curl_http.c','userspace/sdk/lib/x86_64/application_http.c'],
            ['-DREIST_NATIVE_APP_HTTP'])
    def test_legacy_curl_stream(self):
        self.host('curl-stream','test/test_curl_stream_host.c',['userspace/programs/curl_http.c'],
                  ['-Wno-unused-function'])

    def test_actual_sdk(self):
        from run_qemu_x86_64_runtime_clock import once
        source=(ROOT/'test/x86_64_application_tcp_platform_host.c').read_text(encoding='utf-8')
        source=source.replace('reist_tcp_app_selection','reist_http_app_selection')
        source=once(source,'assert(argc==4&&!argv[4]);','assert(argc==2&&!argv[2]);')
        source=once(source,'.destination_port=5000','.destination_port=80')
        source=once(source,'"nc","192.0.2.3","5000","hello",','"curl","http://192.0.2.3/",')
        source=once(source,'__wrap_main(6,args)','__wrap_main(4,args)')
        source=once(source,"for(unsigned n=0;n<512;n++)assert(output[n]=='A');",'''
    for(unsigned n=0;n<512;n++)assert(output[n]=='A');
    unsigned before=calls;assert(x86os_write(1,"x",1)==-116&&calls==before);
    uint64_t untouched=123456;stamp--;
    assert(x86os_monotonic_ms(&untouched)==-84&&untouched==123456);
''')
        source=once(source,"for(unsigned n=0;n<512;n++)x86os_putchar('A');",'''
    uint64_t clock_value=0;assert(!x86os_monotonic_ms(&clock_value)&&clock_value==stamp);
    assert(x86os_monotonic_ms(0)==-22);
    before=calls;
    assert(x86os_create("/file")==-13&&x86os_close(1)==-13);
    assert(x86os_rename("a","b")==-13&&x86os_unlink("a")==-13);
    assert(!x86os_malloc(1));x86os_free(0);
    assert(x86os_ipc_send_bulk_timeout(1,0,100)==-13);
    assert(x86os_write(2,bytes,1)==-13&&x86os_write(1,0,1)==-90);
    assert(x86os_write(1,bytes,1025)==-90);
    assert(x86os_sleep_ms(0)==-22&&x86os_sleep_ms(101)==-22&&calls==before);
    memset(bytes,'A',512);assert(x86os_write(1,bytes,512)==512&&output_length==512);
''')
        self.host('http-sdk',None,[
            'userspace/sdk/lib/x86_64/application_tcp_platform.c',
            'userspace/sdk/lib/x86_64/application_http.c',
            'userspace/sdk/lib/x86_64/application_tcp.c',
            'userspace/sdk/lib/x86_64/network_session.c'],
            ['-DREIST_APP_TCP_HOST_TEST','-DREIST_NATIVE_APP_HTTP','-DREIST_NATIVE_APP_TCP'],source=source)

    def test_peer_frames_and_cases(self):
        import struct
        import run_qemu_x86_64_application_http as guest
        self.assertEqual(len(guest.CASES),25)
        for name in guest.CASES:self.assertEqual(guest.specification(name)['name'],name)
        self.assertEqual(guest.specification('denied-operands')['dialogue'][2:8],list(guest.DENIED))
        # The same framing builder produces a correctly checksummed local TX
        # after swapping the template peer tuple and changing the source port.
        template=bytearray(60);template[:12]=bytes.fromhex('525400123456525400123457')
        template[26:34]=bytes([192,0,2,3,192,0,2,2])
        def tx(seq,ack,flags,payload=b''):
            raw=bytearray(guest.tcp.PeerModel('healthy4g').frame(template,80,seq,ack,flags,payload))
            struct.pack_into('>H',raw,34,49164);raw[50:52]=b'\0\0'
            pseudo=raw[26:34]+b'\0\x06'+struct.pack('>H',len(raw)-34)
            struct.pack_into('>H',raw,50,guest.base.checksum(pseudo+raw[34:]));return bytes(raw)
        request=(b'GET / HTTP/1.1\r\nHost: 192.0.2.3\r\nUser-Agent: REIST-curl/1\r\n'
                 b'Accept: */*\r\nAccept-Encoding: identity\r\nConnection: close\r\n\r\n')
        for mode in ('healthy4g','chunked','fragmented','header-limit','body-limit','bad-header','short-body'):
            peer=guest.PeerModel(mode);self.assertEqual(len(peer.replies(tx(7,0,2))),1)
            frames=peer.replies(tx(8,0xfffffff1,24,request))
            payload=b''.join(f[34+((f[46]>>4)*4):] for f in frames)
            self.assertEqual(payload,guest.response(mode))
            for f in frames:
                self.assertEqual(guest.base.checksum(f[14:34]),0)
                self.assertEqual(guest.base.checksum(f[26:34]+b'\0\x06'+struct.pack('>H',len(f)-34)+f[34:]),0)
        self.assertEqual(guest.PeerModel('peer-loss').replies(tx(7,0,2)),[])
        peer=guest.PeerModel('healthy4g');peer.replies(tx(7,0,2))
        with self.assertRaises(Exception):peer.replies(tx(8,0xfffffff1,24,request.replace(b'GET',b'PUT')))
        bad=bytearray(tx(7,0,2));bad[50]^=1
        with self.assertRaises(Exception):guest.PeerModel('healthy4g').replies(bytes(bad))

    def test_root_operand_dispatch(self):
        source=(ROOT/'userspace/sdk/lib/x86_64/shell_application_tcp.inc').read_text(encoding='utf-8')
        function=source[source.index('static int session_http_operand('):source.index('#define reist_app_tcp_operand')]
        self.host('root-http',None,['userspace/sdk/lib/x86_64/application_http.c',
            'userspace/sdk/lib/x86_64/application_tcp.c','userspace/sdk/lib/x86_64/network_session.c'],source='''
#include <assert.h>
#include <string.h>
#include <reist/x86_64/application_http.h>
static unsigned session_http_selected;
'''+function+'''
int main(void){
 const char *http[]={"curl","http://192.0.2.3/"};
 const char *tcp[]={"nc","192.0.2.3","5000","hello"};
 reist_app_tcp_grant g,before;memset(&g,0xa5,sizeof(g));before=g;
 assert(session_http_operand(2,http,&g)&&!memcmp(&g,&before,sizeof(g)));
 assert(!session_http_operand(4,tcp,&g)&&g.peer_port==5000);
 session_http_selected=1;
 assert(!session_http_operand(2,http,&g)&&g.peer_port==80&&g.protocol==6);
 before=g;assert(session_http_operand(4,tcp,&g)&&!memcmp(&g,&before,sizeof(g)));
 return 0;
}
''')

    def test_raw_review_mutations(self):
        import json,hashlib,shutil,tempfile
        import run_qemu_x86_64_application_http as guest
        base=ROOT/'build/codex-agent/r83bq-application-http'
        old=base/'diagnostic01';image=base/'build02/x86_64/reist-x86_64-bootstrap.elf'
        self.assertEqual(guest.review(image,old,'healthy4g')['http'],2)
        self.assertEqual(guest.review(image,base/'diagnostic02','chunked')['http'],2)
        for mutation in ('authority','selector','response','cpu','wire'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory(dir=base) as temporary:
                folder=Path(temporary)
                for p in old.iterdir():
                    if p.is_file() and (p.suffix in ('.bin','.json') or p.name in ('guest.log','frame-trace.log')):
                        shutil.copyfile(p,folder/p.name)
                if mutation=='wire':
                    p=folder/'packets.json';data=json.loads(p.read_text(encoding='utf-8'))
                    data['frames'][0]['sent']=[];p.write_text(json.dumps(data),encoding='utf-8')
                else:
                    p=folder/'frame-trace.log';lines=p.read_text(encoding='utf-8').splitlines();changed=False
                    for n,line in enumerate(lines):
                        if not line.startswith('NETSESSION '):continue
                        e=json.loads(line[11:])
                        if mutation in ('authority','selector'):
                            if e['kind']!='tcp-app-start' or not e['http']:continue
                            key='profile' if mutation=='authority' else 'http_selected';offset=16 if mutation=='authority' else 0
                        elif mutation=='cpu':
                            if e['kind']!='terminal' or e['slot']!=6:continue
                            key='receipt';offset=16
                        else:
                            if e['kind']!='tcp-response':continue
                            raw=(folder/e['raw']['message']['file']).read_bytes()
                            if len(raw)<672 or int.from_bytes(raw[144:148],'little')!=4 or not int.from_bytes(raw[152:156],'little'):continue
                            key='message';offset=160
                        item=e['raw'][key];value=bytearray((folder/item['file']).read_bytes())
                        if mutation=='cpu':value[offset:offset+8]=(33).to_bytes(8,'little')
                        else:value[offset]^=1
                        (folder/item['file']).write_bytes(value);item['sha256']=hashlib.sha256(value).hexdigest()
                        lines[n]='NETSESSION '+json.dumps(e);changed=True;break
                    self.assertTrue(changed,'concrete mutation target')
                    p.write_text('\n'.join(lines)+'\n',encoding='utf-8')
                with self.assertRaises(ValueError):guest.review(image,folder,'healthy4g')

if __name__=='__main__':unittest.main()
