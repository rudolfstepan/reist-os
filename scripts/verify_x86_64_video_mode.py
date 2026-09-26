"""CK native mode evidence. Development VMware capture is not qualification."""
from pathlib import Path
import argparse
import hashlib
import os
import subprocess
import sys
import tomllib
import time
import struct
import functools
import re
import ctypes as c
from ctypes import wintypes as w
import verify_x86_64_vga_console as legacy
import run_qemu_x86_64_cli_media as clone_tools
import check_x86_64_video_mode_media as media

ROOT=media.ROOT
BASE=ROOT/'build/codex-agent/r83ck-video-mode'
IDENT=os.environ.get('REIST_VIDEO_QUALIFICATION','qualification01')
media.need(re.fullmatch(r'qualification[0-9]{2}',IDENT),'qualification identifier')
GATES=BASE/IDENT
COMMANDS=[['python','test/test_x86_64_video_mode.py','-v']]+[
    ['python','scripts/verify_x86_64_video_mode.py','--'+mode]
    for mode in ('defaults','package','runtime','review')]
LIMITS=(180,600,600,1200,600)
CASES=('healthy','repeated','prep-crash','prep-hang','graphics-crash',
       'graphics-hang','return-crash','return-hang','exhaustion')

def active_package():
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text())
    active=[p for p in queue['packages'] if p['status']=='active']
    media.need(len(active)==1 and active[0]['id']==queue['active_id']=='R8.3ck-video-mode',
               'one active CK package')
    p=active[0]
    media.need(p['targeted_tests']+p['package_tests']+p['runtime_tests']==
               [' '.join(c) for c in COMMANDS],'unchanged five frozen gates')
    media.need(set(legacy.common.common.changed())<=set(p['allowed_files']),'frozen CK scope')
    subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,check=True,timeout=30)
    return p

def fixture_hashes():
    paths=[* (BASE/'guest15').rglob('*'),* (BASE/'media10').rglob('*')]
    paths+=list((BASE/'build04/x86_64').glob('programs-*/video-driver.prg'))
    previous=ROOT/'build/codex-agent/r83cj-vga/qualification05'
    paths+=list(previous.glob('*.json'))
    return {p.relative_to(ROOT).as_posix():legacy.digest(p) for p in paths if p.is_file()}

def qualification_binding():
    frozen=legacy.read(GATES/'frozen.json')
    media.need(frozen['head']==legacy.git('rev-parse','HEAD') and
               frozen['package']==active_package() and frozen['sources']==legacy.common.sources() and
               frozen['tools']==legacy.common.common.all_tools(),'immutable scope/source/tools')
    media.need(frozen['contract']==legacy.digest(ROOT/'docs/architecture/NATIVE_VIDEO_MODE_CONTRACT.md') and
               frozen['fixtures']==fixture_hashes(),'immutable contract and prior evidence')
    return frozen

def require_prior(number):
    qualification_binding()
    for n in range(1,number):
        row=legacy.read(GATES/f'gate-{n:02d}.json')
        media.need(row['passed'] and row['elapsed']<=LIMITS[n-1] and
                   row['command'][1:]==COMMANDS[n-1][1:],'ordered passed gate '+str(n))

def qualify_qemu():
    p=active_package()
    media.need(legacy.git('rev-parse','--short=8','HEAD')=='022b6799','CK definition baseline')
    media.need(not GATES.exists(),'fresh qualification; retain earlier attempts')
    legacy.save(GATES/'frozen.json',dict(head=legacy.git('rev-parse','HEAD'),package=p,
        sources=legacy.common.sources(),tools=legacy.common.common.all_tools(),
        contract=legacy.digest(ROOT/'docs/architecture/NATIVE_VIDEO_MODE_CONTRACT.md'),
        fixtures=fixture_hashes(),commands=COMMANDS,limits=LIMITS))
    for n in range(1,5):
        qualification_binding()
        row=legacy.run([sys.executable,*COMMANDS[n-1][1:]],GATES/f'gate-{n:02d}.log',LIMITS[n-1])
        qualification_binding()
        print('CK_GATE_OK',n,round(row['elapsed'],3),flush=True)
    legacy.save(GATES/'pending.json',dict(accepted=False,complete=False,
        passed_gates=[1,2,3,4],pending_gate=5,
        reason='VMware hardware acceptance deferred by user; no launch or package commit',
        frozen=legacy.digest(GATES/'frozen.json'),
        gates=[legacy.digest(GATES/f'gate-{n:02d}.json') for n in range(1,5)]))

def defaults_gate():
    require_prior(2)
    result=diagnostic_defaults(GATES/'defaults')
    qualification_binding()
    legacy.save(GATES/'defaults.json',dict(passed=True,qualification=True,
        result=legacy.digest(GATES/'defaults/result.json'),profiles=result['profiles']))

def package_gate():
    require_prior(3)
    build=GATES/'enabled'
    media.need(not build.exists(),'fresh selected build')
    legacy.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
        '-NativeVideoMode','-OutputDirectory',build.relative_to(ROOT).as_posix()],
        GATES/'enabled.log',300)
    legacy.run([sys.executable,'scripts/build_x86_64_video_mode_media.py',
        '--input-directory',str(build/'x86_64'),'--output-directory',str(GATES/'media')],
        GATES/'media.log',180)
    result=diagnostic_package(GATES/'media',build/'x86_64',GATES/'package-inspection')
    # Windows delegates to the same Make producer; inspect that complete
    # forwarding path as well as actual root-tree and independent ext2 bytes.
    ps=(ROOT/'scripts/build-x86_64-bootstrap.ps1').read_text()
    make=(ROOT/'Makefile').read_text()
    media.need('"X86_64_NATIVE_VIDEO_MODE=$([int]$NativeVideoMode.IsPresent)"' in ps and
               '$(if $(filter 1,$(X86_64_NATIVE_VIDEO_MODE)),--video-mode,)' in make,
               'both frontends select the common producer')
    qualification_binding()
    legacy.save(GATES/'package.json',dict(passed=True,qualification=True,
        result=legacy.digest(GATES/'package-inspection/result.json'),
        artifacts=result['artifacts'],image=result['image']))

def image_binding():
    p=legacy.read(GATES/'package.json')
    media.need(p['passed'] and p['artifacts']==legacy.common.artifacts(GATES/'enabled') and
               p['result']==legacy.digest(GATES/'package-inspection/result.json'),'immutable selected build')
    image=media.verify(GATES/'media')
    media.need(str(image)==p['image'],'signed qualification media')
    return image

def runtime_gate():
    require_prior(4);image_binding();start=time.monotonic();rows=[]
    for case in CASES:
        media.need(time.monotonic()-start<810,'reserve final guest within aggregate budget')
        folder=GATES/('guest-'+case)
        legacy.run([sys.executable,'scripts/run_qemu_x86_64_video_mode.py',
            '--case',case,'--directory',str(GATES/'media'),'--output',str(folder)],
            GATES/('capture-'+case+'.log'),90)
        row=replay_qemu(GATES/'media',folder);rows.append(row)
        legacy.save(folder/'independent-replay.json',row)
        print('CK_QEMU_OK',case,round(row['elapsed'],3),flush=True)
    elapsed=time.monotonic()-start
    media.need(elapsed<=900 and sum(r['elapsed'] for r in rows)<=900,'bounded complete guest matrix')
    # Exercise altered raw evidence against the fresh healthy capture.
    env=dict(os.environ,REIST_VIDEO_REPLAY_DIRECTORY=str(GATES/'media'),
             REIST_VIDEO_REPLAY_FOLDER=str(GATES/'guest-healthy'))
    legacy.run([sys.executable,'test/test_x86_64_video_mode.py',
        'VideoModeTests.test_independent_replay_rejects_tampered_runtime_evidence','-v'],
        GATES/'tamper.log',180,env=env)
    qualification_binding();image_binding()
    evidence={p.relative_to(GATES).as_posix():legacy.digest(p)
        for case in CASES for p in (GATES/('guest-'+case)).rglob('*') if p.is_file()}
    legacy.save(GATES/'runtime.json',dict(passed=True,elapsed=elapsed,rows=rows,evidence=evidence,
        tamper=legacy.digest(GATES/'tamper.json')))

def review_gate():
    require_prior(5);image_binding()
    matrix=legacy.read(GATES/'runtime.json')
    media.need(matrix['passed'] and len(matrix['rows'])==len(CASES),'complete runtime matrix')
    for name,digest in matrix['evidence'].items():
        media.need(legacy.digest(GATES/name)==digest,'unchanged raw evidence '+name)
    for case in CASES:replay_qemu(GATES/'media',GATES/('guest-'+case))
    # Deliberately fail closed. This entry point cannot turn a QEMU proof into
    # a VMware acceptance or launch a host window contrary to user direction.
    raise ValueError('VMware healthy/fault hardware proofs remain deferred by user; review not passed')

def diagnostic_defaults(output):
    """Bounded development comparison against the accepted CJ artifacts."""
    need=media.need;output=Path(output).resolve()
    need(output.is_relative_to(ROOT/'build/codex-agent') and not output.exists(),
         'fresh owned defaults directory')
    output.mkdir(parents=True)
    started=time.monotonic();result=dict(passed=False,qualification=False)
    try:
        previous=ROOT/'build/codex-agent/r83cj-vga/qualification05'
        accepted=legacy.read(previous/'accepted-commit.json')
        need(accepted['clean'] and accepted['commit']=='f96af9f6dabf394d0f0e49e8c91ee32eb0808d8a',
             'accepted CJ baseline')
        need(accepted['seal']==legacy.digest(previous/'acceptance-seal.json'),'CJ acceptance seal')
        seal=legacy.read(previous/'acceptance-seal.json')
        for name in ('frozen','final','review'):
            need(seal[name]==legacy.digest(previous/(name+'.json')),'CJ sealed '+name)
        need(seal['accepted'] and seal['sources_unchanged'],'accepted unchanged source')
        frozen=legacy.read(previous/'frozen.json')
        names=list(frozen['sources'])
        request=''.join(accepted['commit']+':'+name+'\n' for name in names).encode()
        blobs=subprocess.run(['git','cat-file','--batch'],cwd=ROOT,input=request,
                             capture_output=True,check=True,timeout=30).stdout
        offset=0;committed_sources={}
        for name in names:
            end=blobs.index(b'\n',offset);header=blobs[offset:end].split()
            need(len(header)==3 and header[1]==b'blob','committed source blob '+name)
            size=int(header[2]);offset=end+1
            raw=blobs[offset:offset+size]
            committed_sources[name]=hashlib.sha256(raw).hexdigest()
            offset+=size
            need(blobs[offset:offset+1]==b'\n','complete blob response');offset+=1
        need(offset==len(blobs),'complete committed source inventory')
        # The accepted commit receipt links the sealed checkout to Git. Git's
        # line-ending conversion means checkout hashes are not blob hashes.
        # Keep both inventories; never normalize delivery artifacts.
        result['baseline_committed_sources']=committed_sources
        result['baseline_checkout_sources']=frozen['sources']
        for name,tool in frozen['tools'].items():
            need(legacy.digest(Path(tool['path']))==tool['sha256'],'unchanged tool '+name)
        result['baseline']=accepted
        result['profiles']={}
        for label,flag,receipt in (('disabled','-NativeAppFiles','defaults'),
                                   ('enabled','-NativeVgaConsole','package')):
            old=legacy.read(previous/(receipt+'.json'))['artifacts']
            need(old==legacy.common.artifacts(previous/label),'unchanged baseline artifacts '+label)
            command=['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
                     flag,'-OutputDirectory',(output/label).relative_to(ROOT).as_posix()]
            legacy.run(command,output/(label+'.log'),min(300,int(590-(time.monotonic()-started))))
            new=legacy.common.artifacts(output/label)
            need(old.keys()==new.keys(),'complete artifact set '+label)
            changed=[name for name in old if old[name]!=new[name]]
            result['profiles'][label]=dict(artifacts=new,changed=changed,count=len(new))
            need(not changed,'byte-identical '+label+' artifacts: '+str(changed))
        result['passed']=True
    except Exception as exc:
        result['error']=str(exc)
        raise
    finally:
        result['elapsed']=time.monotonic()-started
        legacy.save(output/'result.json',result)
    return result

def diagnostic_package(directory,build,output):
    """Inspect the existing selected build without restarting any guest."""
    need=media.need;output=Path(output).resolve();build=Path(build).resolve()
    need(output.is_relative_to(ROOT/'build/codex-agent') and not output.exists(),
         'fresh owned package diagnostic directory')
    output.mkdir(parents=True);started=time.monotonic()
    result=dict(passed=False,qualification=False)
    try:
        image=media.verify(Path(directory))
        attempts=list(build.glob('programs-*'));need(len(attempts)==1,'one selected producer')
        attempt=attempts[0]
        for name in (media.KERNEL,media.CORE):
            need(legacy.digest(build/name)==legacy.digest(image/name),'signed build '+name)
        for name in ('video.prg','cat.prg','ls.prg','probe.prg'):
            need((attempt/'root'/name).read_bytes()==(image/name).read_bytes(),'ordinary file '+name)
        need((attempt/'root/bin/shell.prg').read_bytes()==(image/'program0.prg').read_bytes(),
             'ordinary userspace shell')
        usage=[]
        for path in build.rglob('*.su'):
            for line in path.read_text().splitlines():
                if line.startswith(('userspace/drivers/video/','userspace/drivers/vga/',
                                    'userspace/drivers/ps2/','userspace/gui/compositor/native_mode_probe.c:')):
                    location,size,kind=line.split('\t')
                    need(kind=='static' and 0<=int(size)<=4096,'fixed actual stack frame')
                    usage.append((location,int(size)))
        need(usage and sum(n for _,n in usage)<=16384,'conservative total stack frames')
        need(any('native_mode_main.c:' in n for n,_ in usage) and
             any('native_mode_probe.c:' in n for n,_ in usage),'both selected role stacks')
        tools=legacy.read(ROOT/'build/codex-agent/r83cj-vga/qualification05/frozen.json')['tools']
        nm=tools['nm'];need(legacy.digest(Path(nm['path']))==nm['sha256'],'accepted nm tool')
        for name in (media.KERNEL,media.CORE):
            check=subprocess.run([nm['path'],'--undefined-only',str(build/name)],
                                 capture_output=True,check=True,timeout=20)
            need(not check.stdout.strip(),'no undefined symbols '+name)
        roles={}
        for name in ('video-driver.prg','video.prg'):
            raw=(attempt/name).read_bytes();media.selected.programs.prepare(raw,[],True)
            phoff=struct.unpack_from('<Q',raw,32)[0];count=struct.unpack_from('<H',raw,56)[0]
            segments=[struct.unpack_from('<II6Q',raw,phoff+56*i) for i in range(count)]
            writable=sum(s[6] for s in segments if s[0]==1 and s[1]&2)
            need(writable<=65536,'fixed writable role storage '+name)
            roles[name]=dict(sha256=legacy.digest(attempt/name),writable_bytes=writable)
        result.update(passed=True,stack=usage,stack_total=sum(n for _,n in usage),roles=roles,
                      image=str(image),artifacts=legacy.common.artifacts(build.parent))
    except Exception as exc:
        result['error']=str(exc);raise
    finally:
        result['elapsed']=time.monotonic()-started
        legacy.save(output/'result.json',result)
    return result

def replay_qemu(directory,folder,fifo_bytes=4096):
    """Independent raw state/media/page/pixel replay, without capture predicates."""
    image=media.verify(Path(directory));folder=Path(folder);need=media.need
    need(fifo_bytes in (4096,16384),'explicit FIFO replay profile')
    row=legacy.read(folder/'result.json');case=row['case']
    need(row['passed'] and row['stopped'] and 0<row['elapsed']<=90 and
         row['kernel_sha256']==legacy.digest(image/media.KERNEL) and 'cleanup_error' not in row,
         'complete bounded capture and exact kernel')
    need(case in ('healthy','repeated','prep-crash','prep-hang','graphics-crash',
                  'graphics-hang','return-crash','return-hang','exhaustion'),'replay case')
    def words(path,count):
        raw=path.read_bytes();need(len(raw)==count*8,'complete raw '+path.name)
        return struct.unpack('<'+str(count)+'Q',raw)
    def sealed(path,count):
        values=words(path,count*2)
        need(all(values[i]^values[i+count]==2**64-1 for i in range(count)), 'sealed '+path.name)
        return values[:count]
    for phase in ('before','after'):
        boot=legacy.read(folder/'boot-medium'/(phase+'.json'))
        data=legacy.read(folder/('media-'+phase+'.json'))
        for receipt,size in ((boot,1474560),(data,1048576)):
            need(receipt['passed'] and receipt['phase']==phase and receipt['overlay_allocated_data']==0,
                 'no guest media writes')
            end=0
            for extent in receipt['extents']:
                need(extent['start']==end and extent['length']>0 and extent['depth']==1,'backing extent')
                end+=extent['length']
            need(end==size,'complete unchanged backing medium')
        need(boot['base']==dict(size=1474560,sha256=legacy.digest(image/'reist-x86_64-floppy.img')) and
             data['base_sha256']==legacy.digest(image/'system.ext2'),'signed media binding')
    raw=(folder/'serial.log').read_bytes()
    need(len(raw)<=262144 and not any(x in raw for x in (b'EXCEPTION_FATAL',b'_STATE_ERROR',b'PANIC')),
         'bounded serial without kernel failure')
    reaps=[struct.unpack('<4I2Q',bytes.fromhex(m.decode())) for m in
           re.findall(rb'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-F]{64})\r\n',raw)]
    need(all(r[0]<=7 and 0<r[1]<2**31 and r[3] in (1,2,3,4) for r in reaps),'canonical reaps')
    user=re.sub(rb'REIST_X86_64_PROCESS_REAP_OK v1=[0-9A-F]{64}\r\n',b'',raw)
    modes={};consoles={};screens={}
    for path in sorted(folder.iterdir()):
        if not path.is_dir() or not (path/'mode.bin').exists():continue
        m=sealed(path/'mode.bin',12);d=sealed(path/'display.bin',8)
        need(m[3]<=3 and m[4]<=1 and m[9]<=1 and not any(m[10:]),'bounded mode state')
        need(d[3]<=1 and d[6]<=64 and d[7]<=1048576,'bounded display state')
        modes[path.name]=m
        vraw=(path/'vga.bin').read_bytes();need(len(vraw)==2272,'complete VGA transport')
        v=struct.unpack_from('<20Q',vraw)
        need(all(v[i]^v[i+10]==2**64-1 for i in range(10)),'VGA seals')
        consoles[path.name]=v[:10]
        cells=(path/'cells.bin').read_bytes();need(len(cells)==4000,'complete text cells')
        screen='\n'.join(cells[i*160:i*160+160:2].decode('cp437') for i in range(25))
        need(screen==(path/'screen.txt').read_text(encoding='utf-8'),'independent text reconstruction')
        screens[path.name]=screen
        if v[3]==2:
            tasks=words(path/'tasks.bin',1024);family=words(path/'family.bin',64)
            profiles=words(path/'profiles.bin',32)
            need(v[0]&0xffffffff==4 and tasks[513]==v[0]>>32 and
                 family[32:34]==v[:2] and v[1]==tasks[1]<<32,'live VGA generation and parent')
            need(profiles[16:20]==(v[0]>>32,sum(1<<n for n in (9,22,41,42)),1<<49,0),
                 'attenuated VGA profile')
        if path.name!='graphics':
            need(m[3]==0 and m[4]==1 and m[9]==0,'text mode fenced without hardware quarantine')
            need((path/'display-boot.bin').read_bytes()==bytes(32) and
                 words(path/'mode-pdpt.bin',512)[509]==0,'graphics descriptor and mapping removed')
    need('REIST OS userspace shell' in screens['startup'] and consoles['startup'][3]==2,'real initial shell')
    if case not in ('healthy','repeated'):
        injected=legacy.read(folder/'fault-injection.json')
        mode={'prep-crash':1,'prep-hang':2,'graphics-crash':3,'graphics-hang':4,
              'return-crash':5,'return-hang':6,'exhaustion':1}[case]
        need(struct.unpack('<4Q',bytes.fromhex(injected['before']))==(0x3145444f4d564b43,1,0,0) and
             struct.unpack('<4Q',bytes.fromhex(injected['after']))==(0x3145444f4d564b43,1,mode,0),
             'exact private fault selection only')
    final='exhausted' if case=='exhaustion' else 'commands'
    need(final in modes,'final recovery snapshot')
    worker=modes[final][0]
    worker_reaps=[r for r in reaps if (r[1]<<32)|r[0]==worker]
    need(len(worker_reaps)==1,'exact last mode worker actually reaped')
    expected_exit=134 if case.endswith('crash') or case=='exhaustion' else 0
    expected_reason=4 if case in ('healthy','repeated') else 3
    need(worker_reaps[0][2:4]==(expected_exit,expected_reason),'actual selected worker failure/exit receipt')
    need(not any(words(folder/final/'family.bin',64)[40:48]),'last mode worker family slot reaped')
    if case in ('healthy','repeated','return-crash','return-hang'):
        need(sum(r[0]==4 and r[2:4]==(0,4) for r in reaps)==(2 if case=='repeated' else 1),
             'each renderer actually completed successfully')
    if case in ('prep-hang','graphics-hang'):
        need(modes[final][5]-modes[final][6]>=1000,'actual unchanged heartbeat timeout before fencing')
    if case=='exhaustion':
        need(user.count(b'VGA return: 00000000')==2 and user.count(b'VGA return: fffffff5')==1 and
             consoles[final][3]==1 and 'VGA CONSOLE STOPPED' in screens[final] and b'Built-ins:' in user,
             'two recoveries then visible exhaustion with COM1')
    else:
        need(consoles[final][3]==2 and consoles[final][0]!=consoles['startup'][0] and
             consoles[final][2]==consoles['startup'][2]+(2 if case=='repeated' else 1),'new VGA generation/epoch')
        for label,token in (('command-cat','REIST native application file objects'),('command-ls','data.txt'),
                            ('commands','Bad command or program file.')):
            need(token in screens[label] and token.encode() in user,'actual command output '+label)
            proof=legacy.read(folder/label/'cursor.json');lines=screens[label].splitlines()[:24]
            r=max(i for i,line in enumerate(lines) if line.rstrip()=='C:\\>')
            need(proof['row']==r and proof['column']==4 and 1<=len(proof['frames'])<=8,'current cursor cell')
            # Reconstruct underline raster independently of observer.cursor_pixels.
            ppm=(folder/label/proof['frames'][-1]).read_bytes();header=b'P6\n720 400\n255\n'
            need(ppm.startswith(header) and len(ppm)==len(header)+720*400*3,'complete text raster')
            pixels=ppm[len(header):]
            need(any(sum(pixels[((r*16+y)*720+36+x)*3:((r*16+y)*720+36+x)*3+3]!=b'\0\0\0'
                         for x in range(9))>=8 for y in range(13,16)),'independent current-line cursor pixels')
    if case in ('healthy','repeated','graphics-crash','graphics-hang','return-crash','return-hang'):
        path=folder/'graphics';need(path.exists(),'graphics phase evidence')
        m=modes['graphics'];d=sealed(path/'display.bin',8)
        need(m[3]==2 and not m[4] and not m[9] and m[8]==9 and m[0]&0xffffffff==5 and
             d[0]&0xffffffff==4 and not d[3] and d[1]==m[1],'live separated graphics roles')
        profiles=words(path/'profiles.bin',32);budgets=words(path/'budgets.bin',32);windows=words(path/'windows.bin',32)
        family=words(path/'family.bin',64)
        for slot,owner,bits in ((4,d[0],(9,22,41,42)),(5,m[0],(9,22,41,42,54))):
            need(profiles[slot*4:slot*4+4]==(owner>>32,sum(1<<n for n in bits),1<<49,0) and
                 family[slot*8:slot*8+2]==(owner,m[1]),'exact graphics authority')
            need(budgets[slot*4:slot*4+2]==(owner>>32,32) and windows[slot*4]==100 and
                 windows[slot*4+3]<=32,'unchanged periodic32 CPU limit')
        boot=words(path/'display-boot.bin',4);base=boot[0]
        need(0xfd000000<=base<=0xfe000000-3145728 and base%4096==0 and
             boot[1:]==((1024<<32)|4096,(3145728<<32)|768,(3145728<<32)|base),'fixed admitted framebuffer geometry')
        symbols=media.payload.elf((image/media.KERNEL).read_bytes(),32)['symbols']
        address=lambda name:symbols[name]['value']
        clean=lambda word:word&~0x60
        need(clean(words(path/'mode-pdpt.bin',512)[509])==address('native_display_pd')|3,'supervisor display PDPT')
        pd=words(path/'native_display_pd.bin',512);pts=words(path/'native_display_pts.bin',3072)
        fp=words(path/'native_video_fifo_pt.bin',512)
        need(all(clean(pd[i])==(address('native_display_pts')+i*4096)|3 for i in range(6)) and
             clean(pd[6])==address('native_video_fifo_pt')|3 and not any(pd[7:]),'exact bounded display directory')
        need(all(clean(pts[i])==(base+i*4096)|0x800000000000001b for i in range(768)) and
             not any(pts[768:]) and
             all(clean(fp[i])==(0xfe000000+i*4096)|0x800000000000001b for i in range(fifo_bytes//4096)) and
             not any(fp[fifo_bytes//4096:]),
             'only exact supervisor RW/NX/UC framebuffer and selected FIFO mappings')
    if case in ('healthy','repeated','return-crash','return-hang'):
        expected_row=b'\x33\x66\x99'*320+b'\x33\x99\x66'*384+b'\x99\x66\x33'*320
        expected=b'P6\n1024 768\n255\n'+expected_row*768
        frames=sorted(folder.glob('mode-*.ppm'));need(1<=len(frames)<=40,'bounded graphics frame set')
        need(any(p.read_bytes()==expected for p in frames),'complete actual1024x768 graphics raster')
        if case=='repeated':
            groups=row['mode_groups'];names=['mode-'+str(i)+'.ppm' for i in range(len(frames))]
            need(len(groups)==2 and all(groups) and [n for group in groups for n in group]==names and
                 set(names)=={p.name for p in frames},'two disjoint consecutive transition frame groups')
            need(all(any((folder/name).read_bytes()==expected for name in group) for group in groups),
                 'complete raster observed separately for both transitions')
    if fifo_bytes==16384 and case in ('healthy','repeated'):
        groups=row['mode_groups']
        need(len(groups)==(2 if case=='repeated' else 1),'FIFO generation groups')
        for group in groups:
            consumed=[]
            for name in group:
                index=int(Path(name).stem.split('-')[1])
                raw=(folder/('fifo-'+str(index)+'.bin')).read_bytes()
                need(len(raw)==16384,'complete FIFO evidence')
                minimum,maximum,next_,stop=struct.unpack_from('<4I',raw)
                if not (folder/name).read_bytes().startswith(b'P6\n1024 768\n255\n'):
                    continue # Text-phase captures are not active graphics evidence.
                need(minimum==16 and maximum==16384 and maximum-minimum>=10240 and
                     minimum<=next_<maximum and minimum<=stop<maximum and
                     next_%4==0 and stop%4==0,'valid native QEMU FIFO header')
                if next_==stop and stop==16+192*20:consumed.append(index)
            need(consumed,'all192 real UPDATE commands consumed in each generation')
    return dict(passed=True,case=case,elapsed=row['elapsed'],snapshots=sorted(modes),reaps=len(reaps))

def vmware_transition(capture,hwnd,folder,result,start,manual=False):
    """Input is sent only to the exact owned foreground VMware window."""
    need=media.need
    class Keyboard(c.Structure):
        _fields_=[('vk',w.WORD),('scan',w.WORD),('flags',w.DWORD),('time',w.DWORD),('extra',c.c_size_t)]
    class Payload(c.Union):
        _fields_=[('keyboard',Keyboard),('mouse_storage',c.c_byte*32)]
    class Input(c.Structure):
        _fields_=[('kind',w.DWORD),('payload',Payload)]
    need(c.sizeof(Input)==40,'Win64 INPUT layout')
    capture.u.SendInput.argtypes=[w.UINT,c.POINTER(Input),c.c_int]
    capture.u.SendInput.restype=w.UINT
    result['host_inputs']=[]
    result['manual_input']=manual
    def event(code,up=False):
        need(capture.u.GetForegroundWindow()==hwnd,'owned foreground before input')
        scan=capture.u.MapVirtualKeyW(code,0)
        need(0<scan<256,'mapped native keyboard scan code')
        item=Input();item.kind=1;item.payload.keyboard=Keyboard(0,scan,8|(2 if up else 0),0,0)
        c.set_last_error(0)
        accepted=capture.u.SendInput(1,c.byref(item),c.sizeof(item))
        result['host_inputs'].append(dict(code=code,scan=scan,up=up,accepted=accepted,error=c.get_last_error()))
        need(accepted==1,'Windows accepted scan-code input')
    def key(code):
        event(code)
        try:time.sleep(.05)
        finally:event(code,True)
    def serial():
        raw=(folder/'serial.log').read_bytes()
        need(len(raw)<=262144 and b'EXCEPTION_FATAL' not in raw,'bounded VMware serial')
        return raw
    def send(command):
        if manual:
            print('CK_MANUAL_INPUT_REQUIRED',command,flush=True)
            return
        for code in [*(ord(c.upper()) for c in command),13]:key(code)
    try:
        hostlog=(folder/'vmware.log').read_text(errors='replace')
        need('SVGA-PCI: BAR gfbSize=134217728, fifoSize=8388608' in hostlog,
             'positive actual VMware aperture inventory before mode request')
        result['apertures']={'framebuffer':134217728,'fifo':8388608}
        _,_,_,rect=capture.capture(hwnd,folder/'before-mode.png')
        if not manual:need(capture.u.GetForegroundWindow()==hwnd,'owned foreground before capture focus')
        # VMware's explicit grab shortcut avoids a host chrome/viewport click.
        if not manual:
            event(17)
            try:key(ord('G'))
            finally:event(17,True)
        time.sleep(.5)
        send('video')
        witnessed=False;returned=False;frames=[]
        for i in range(240 if manual else 80):
            need(time.monotonic()-start<130,'VMware transition deadline')
            path=folder/('mode-'+str(i)+'.png')
            pixels,width,height,_=capture.capture(hwnd,path)
            need(len(pixels)==width*height*4,'complete owned mode capture')
            colors=[0,0,0]
            # Windows DIB is BGRX; count exact probe pixels, not window chrome.
            for offset in range(0,len(pixels),16):
                rgb=pixels[offset:offset+3]
                if rgb==b'\x99\x66\x33':colors[0]+=1
                elif rgb==b'\x66\x99\x33':colors[1]+=1
                elif rgb==b'\x33\x66\x99':colors[2]+=1
            frames.append(dict(file=path.name,colors=colors,width=width,height=height))
            if min(colors)>500:witnessed=True
            raw=serial()
            if not manual:need(i<8 or b'video' in raw,'injected VIDEO reached actual VMware shell')
            # Other manually entered commands cannot masquerade as VIDEO return.
            if b'video\r\n' in raw and b'C:\\>' in raw.split(b'video\r\n',1)[1]:
                returned=True;break
            time.sleep(.1)
        result['mode_frames']=frames
        need(witnessed,'actual VMware three-band graphics pixels')
        need(returned and b'Video start failed:' not in raw and b'VGA return failed:' not in raw,
             'successful VMware graphics to text return')
        # Decode existing kernel receipts independently: renderer4/worker5
        # must both exit normally; console4 must have a different generation.
        import re
        records=[struct.unpack('<4I2Q',bytes.fromhex(x.decode())) for x in
                 re.findall(rb'PROCESS_REAP_OK v1=([0-9A-F]{64})',raw)]
        need(any(r[0]==4 and r[2]==0 and r[3]==4 for r in records) and
             any(r[0]==5 and r[2]==0 and r[3]==4 for r in records),'normal renderer and worker retirement')
        before=raw.count(b'Built-ins:');send('help')
        for _ in range(300 if manual else 100):
            need(time.monotonic()-start<140,'VMware post-return keyboard deadline')
            if serial().count(b'Built-ins:')>before:break
            time.sleep(.1)
        need(serial().count(b'Built-ins:')==before+1,'actual VMware post-return PS2 shell dispatch')
        capture.capture(hwnd,folder/'returned-shell.png')
    finally:
        # Release guest capture without injecting into any other application.
        if not manual and capture.u.GetForegroundWindow()==hwnd:
            capture.u.keybd_event(17,0,0,0);capture.u.keybd_event(18,0,0,0)
            capture.u.keybd_event(18,0,2,0);capture.u.keybd_event(17,0,2,0)

def diagnostic_vmware(directory,output,manual=False):
    image=media.verify(Path(directory))
    output=Path(output).absolute()
    media.need(output==output.resolve() and output.is_relative_to(ROOT/'build/codex-agent') and
               not output.exists(),'fresh owned CK VMware diagnostic directory')
    media.need(legacy.digest(legacy.CAPTURE)==legacy.CAPTURE_SHA,'accepted owned-window helper')
    output.mkdir(parents=True)
    ns=dict(vars(legacy),GATES=output,IDENT=output.name,
            vmware_transition=functools.partial(vmware_transition,manual=manual))
    callback=clone_tools.bb.function(legacy.vmware,ns,[
        ("'REIST native64 - CJ '","'REIST native64 - CK '"),
        ("need(capture.u.GetForegroundWindow() == hwnd, 'exact foreground window')",
         "need(True, 'manual capture does not inject input')" if manual else
         "need(capture.u.GetForegroundWindow() == hwnd, 'exact foreground window')"),
        ("        while time.monotonic() < ready+20:\n"
         "            raw = (folder/'serial.log').read_bytes()\n"
         "            need(len(raw) <= 262144 and b'EXCEPTION_FATAL' not in raw and b'VGA console unavailable' not in raw, 'VMware remains healthy')\n"
         "            time.sleep(.1)",
         "        vmware_transition(capture,hwnd,folder,result,start)")])
    return callback(image)

def prepare_manual(directory,output):
    """Separate user-owned visual artifact; never modify captured evidence."""
    image=media.verify(Path(directory));output=Path(output).absolute()
    media.need(output==output.resolve() and output.is_relative_to(ROOT/'build/codex-agent') and
               not output.exists(),'fresh manual VMware artifact directory')
    output.mkdir(parents=True)
    ns=dict(vars(legacy),GATES=output,IDENT=output.name)
    prepare=clone_tools.bb.function(legacy.vmware,ns,[
        ("'REIST native64 - CJ '","'REIST native64 - CK '"),
        ("    pinned = {n: digest(folder/n) for n in ('boot.img', 'system-flat.vmdk')}",
         "    return vmx\n    pinned = {n: digest(folder/n) for n in ('boot.img', 'system-flat.vmdk')}")])
    vmx=prepare(image)
    media.need(legacy.digest(vmx.parent/'boot.img')==legacy.digest(image/'reist-x86_64-floppy.img') and
               legacy.digest(vmx.parent/'system-flat.vmdk')==legacy.digest(image/'system.ext2'),
               'exact signed candidate in separate manual artifact')
    legacy.save(output/'manual-artifact.json',dict(vmx=str(vmx),source=str(image),
        kernel=legacy.digest(image/media.KERNEL),qualification=False,user_owned=True))
    return vmx

# Separate CL transaction. Original CK evidence/gates above remain historical.
FIFO_BASE=ROOT/'build/codex-agent/r83cl-video-fifo'
FIFO_IDENT=os.environ.get('REIST_FIFO_QUALIFICATION','qualification01')
media.need(re.fullmatch(r'qualification[0-9]{2}',FIFO_IDENT),'FIFO qualification identifier')
FIFO_GATES=FIFO_BASE/FIFO_IDENT
FIFO_CASES=('healthy','repeated','graphics-crash','graphics-hang')
FIFO_COMMANDS=[['python','test/test_x86_64_video_mode.py','-v']]+[
    ['python','scripts/verify_x86_64_video_mode.py','--fifo-'+mode]
    for mode in ('defaults','package','runtime','review')]
FIFO_LIMITS=(180,600,600,600,300)

def fifo_package_definition():
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    active=[p for p in queue['packages'] if p['status']=='active']
    media.need(len(active)==1 and active[0]['id']==queue['active_id']=='R8.3cl-video-fifo','one CL package')
    p=active[0]
    media.need(p['targeted_tests']+p['package_tests']+p['runtime_tests']==
               [' '.join(c) for c in FIFO_COMMANDS],'frozen CL gates')
    media.need(set(legacy.common.common.changed())<=set(p['allowed_files']),'CL source scope')
    subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,check=True,timeout=30)
    return p

def fifo_binding():
    f=legacy.read(FIFO_GATES/'frozen.json')
    media.need(f['head']==legacy.git('rev-parse','HEAD') and f['package']==fifo_package_definition() and
               f['sources']==legacy.common.sources() and f['tools']==legacy.common.common.all_tools() and
               f['contract']==legacy.digest(ROOT/'docs/architecture/NATIVE_VIDEO_MODE_CONTRACT.md'),
               'immutable CL source/tool/contract binding')
    return f

def fifo_prior(number):
    fifo_binding()
    for n in range(1,number):
        r=legacy.read(FIFO_GATES/f'gate-{n:02d}.json')
        media.need(r['passed'] and r['elapsed']<=FIFO_LIMITS[n-1] and
                   r['command'][1:]==FIFO_COMMANDS[n-1][1:],'passed ordered CL gate')

def qualify_fifo():
    p=fifo_package_definition();media.need(not FIFO_GATES.exists(),'fresh CL qualification')
    legacy.save(FIFO_GATES/'frozen.json',dict(head=legacy.git('rev-parse','HEAD'),package=p,
        sources=legacy.common.sources(),tools=legacy.common.common.all_tools(),
        contract=legacy.digest(ROOT/'docs/architecture/NATIVE_VIDEO_MODE_CONTRACT.md'),
        commands=FIFO_COMMANDS,limits=FIFO_LIMITS))
    for n,command in enumerate(FIFO_COMMANDS,1):
        fifo_binding()
        r=legacy.run([sys.executable,*command[1:]],FIFO_GATES/f'gate-{n:02d}.log',FIFO_LIMITS[n-1])
        fifo_binding();print('CL_GATE_OK',n,round(r['elapsed'],3),flush=True)
    legacy.save(FIFO_GATES/'accepted.json',dict(passed=True,qemu_only=True,vmware_accepted=False,
        frozen=legacy.digest(FIFO_GATES/'frozen.json'),
        gates=[legacy.digest(FIFO_GATES/f'gate-{n:02d}.json') for n in range(1,6)]))

def fifo_defaults():
    fifo_prior(2);diagnostic_defaults(FIFO_GATES/'defaults');fifo_binding()

def fifo_package():
    fifo_prior(3);build=FIFO_GATES/'enabled'
    legacy.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
        '-NativeVideoMode','-OutputDirectory',build.relative_to(ROOT).as_posix()],FIFO_GATES/'build.log',300)
    legacy.run([sys.executable,'scripts/build_x86_64_video_mode_media.py','--input-directory',
        str(build/'x86_64'),'--output-directory',str(FIFO_GATES/'media')],FIFO_GATES/'media.log',180)
    diagnostic_package(FIFO_GATES/'media',build/'x86_64',FIFO_GATES/'package')
    fifo_binding()

def fifo_image():
    p=legacy.read(FIFO_GATES/'package/result.json')
    media.need(p['passed'] and p['artifacts']==legacy.common.artifacts(FIFO_GATES/'enabled'),
               'CL selected artifact binding')
    image=media.verify(FIFO_GATES/'media');media.need(str(image)==p['image'],'CL signed image')
    return image

def fifo_runtime():
    fifo_prior(4);fifo_image();start=time.monotonic();rows=[]
    for case in FIFO_CASES:
        media.need(time.monotonic()-start<270,'reserve final bounded CL guest')
        folder=FIFO_GATES/('guest-'+case)
        legacy.run([sys.executable,'scripts/run_qemu_x86_64_video_mode.py','--fifo-proof','--case',case,
            '--directory',str(FIFO_GATES/'media'),'--output',str(folder)],
            FIFO_GATES/('capture-'+case+'.log'),90)
        row=replay_qemu(FIFO_GATES/'media',folder,16384);rows.append(row)
        legacy.save(folder/'independent-replay.json',row)
        print('CL_QEMU_OK',case,round(row['elapsed'],3),flush=True)
    elapsed=time.monotonic()-start
    media.need(elapsed<=360 and sum(r['elapsed'] for r in rows)<=360,'CL runtime aggregate')
    evidence={p.relative_to(FIFO_GATES).as_posix():legacy.digest(p)
        for case in FIFO_CASES for p in (FIFO_GATES/('guest-'+case)).rglob('*') if p.is_file()}
    legacy.save(FIFO_GATES/'runtime.json',dict(passed=True,elapsed=elapsed,rows=rows,evidence=evidence))
    fifo_binding()

def fifo_review():
    fifo_prior(5);fifo_image()
    matrix=legacy.read(FIFO_GATES/'runtime.json')
    media.need(matrix['passed'] and [r['case'] for r in matrix['rows']]==list(FIFO_CASES),'complete CL matrix')
    for name,digest in matrix['evidence'].items():
        media.need(legacy.digest(FIFO_GATES/name)==digest,'unchanged CL raw proof')
    for case in FIFO_CASES:replay_qemu(FIFO_GATES/'media',FIFO_GATES/('guest-'+case),16384)
    # Independent raw tampering: deny extra user mapping and never-consumed FIFO.
    from unittest.mock import patch
    original=Path.read_bytes;folder=FIFO_GATES/'guest-healthy'
    for mode in ('mapping','consumption'):
        def read(path):
            data=original(path)
            if mode=='mapping' and path==folder/'graphics/native_video_fifo_pt.bin':
                raw=bytearray(data);raw[3*8]|=4;return bytes(raw)
            if mode=='consumption' and path.parent==folder and path.name.startswith('fifo-'):
                raw=bytearray(data);struct.pack_into('<I',raw,12,16);return bytes(raw)
            return data
        rejected=False
        with patch.object(Path,'read_bytes',read):
            try:replay_qemu(FIFO_GATES/'media',folder,16384)
            except ValueError:rejected=True
        media.need(rejected,'CL rejects tampered '+mode)
    fifo_binding()
    legacy.save(FIFO_GATES/'review.json',dict(passed=True,qemu_only=True,
        cases=list(FIFO_CASES),files=len(matrix['evidence']),tamper_denied=['mapping','consumption']))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    modes=parser.add_mutually_exclusive_group(required=True)
    for name in ('qualify-qemu','defaults','package','runtime','review','qualify-fifo','fifo-defaults','fifo-package','fifo-runtime','fifo-review'):
        modes.add_argument('--'+name,action='store_true')
    modes.add_argument('--diagnostic-vmware',action='store_true')
    modes.add_argument('--prepare-manual',action='store_true')
    modes.add_argument('--replay-qemu',action='store_true')
    modes.add_argument('--diagnostic-defaults',action='store_true')
    modes.add_argument('--diagnostic-package',action='store_true')
    parser.add_argument('--manual-input',action='store_true')
    parser.add_argument('--directory',type=Path)
    parser.add_argument('--build',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    for name,callback in (('qualify_fifo',qualify_fifo),('fifo_defaults',fifo_defaults),
                          ('fifo_package',fifo_package),('fifo_runtime',fifo_runtime),('fifo_review',fifo_review),
                          ('qualify_qemu',qualify_qemu),('defaults',defaults_gate),
                          ('package',package_gate),('runtime',runtime_gate),('review',review_gate)):
        if getattr(args,name):
            callback();raise SystemExit(0)
    if args.output is None:
        parser.error('--output is required for development operations')
    if not args.diagnostic_defaults and args.directory is None:
        parser.error('--directory is required for media operations')
    if args.diagnostic_package and args.build is None:
        parser.error('--build is required for package inspection')
    print(diagnostic_defaults(args.output) if args.diagnostic_defaults else
          diagnostic_package(args.directory,args.build,args.output) if args.diagnostic_package else
          replay_qemu(args.directory,args.output) if args.replay_qemu else
          prepare_manual(args.directory,args.output) if args.prepare_manual else
          diagnostic_vmware(args.directory,args.output,args.manual_input))
