"""Start the accepted native64 display image with a bounded serial shell."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time,uuid
import check_x86_64_display_media as check
import run_qemu_x86_64_cli_media as guest
DEFAULT=check.ROOT/'build/codex-agent/r83be-display/media04'
SESSIONS=check.ROOT/'build/codex-agent/display-sessions'
INDEX_SHA='8c0fdfa5020ccd3e001f0225127b985ddc3f25ffcb66edb07c72f380dc1ded3e'
PINS=dict(check.accepted.PINS,**{
    'reist-x86_64-bootstrap.elf':'4285ce4d23c8827a908147fa04cce01e3b04f378c76e917c966e55d1bbddb1af',
    'reist-x86_64-c-core.elf':'65738639762f1caceea2c61f0436467b6a15e75fd782d497c96b8a8e42819458',
    'boot-programs.bin':'e871ebfe55898273142d1e3b389d1e7659d9e11b480974e12e313cc1e8263aad',
    'file-program.prg':'59294caf36df8f517c0f46a686fafcf7422449dc87fc9e9464e286115a500ae8',
    'program0.prg':'b7758f04b9be3791bdb539826a2ca21fca92f655a2204e8cb1ed81e5fb736a93'})
# Preserve the original absolute tool deadline and immutable media construction.
# Only this new starter accepts every integer in its documented duration range.
data_fixture=guest.bb.function(guest.data_fixture,dict(vars(guest)),[
    ('type(limit) is int and limit in (20,30,320,330)','type(limit) is int and 30<=limit<=320')])

def inputs(values):
    check.need(type(values) is dict and set(values)==set(PINS),'exact accepted display input set')
    for name,sha in PINS.items():
        check.need(type(values[name]) is bytes and hashlib.sha256(values[name]).hexdigest()==sha,'accepted display input '+name)
    check.input_binding(values)

def admit(directory,openssl=None):
    directory=Path(directory);index=directory/'display-media.json'
    check.need(hashlib.sha256(check.bounded(index,16384)).hexdigest()==INDEX_SHA,'accepted signed display index')
    attempt=check.verify(directory,openssl=openssl)
    values={n:check.bounded(attempt/n,check.FILES[n]) for n in PINS};inputs(values)
    check.need(hashlib.sha256(check.bounded(index,16384)).hexdigest()==INDEX_SHA,'stable accepted display index')
    return attempt,check.medium_files(values)

def launch(directory=DEFAULT,*,layout='hdd',ram=4096,check_only=False,headless=False,seconds=320,openssl=None):
    check.need(layout in ('hdd','floppy') and type(ram) is int and ram in (4096,8192) and
               type(check_only) is bool and type(headless) is bool and type(seconds) is int and
               30<=seconds<=320,'supported explicit display session')
    attempt,files=admit(directory,openssl)
    if check_only:
        print('DISPLAY_CHECK_OK',attempt,flush=True)
        return dict(passed=True,check_only=True,attempt=str(attempt))
    folder=SESSIONS/('session-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    started=time.monotonic();medium=None;fixture=None;vm=None
    result=dict(passed=False,attempt=str(attempt),layout=layout,ram=ram,headless=headless,limit=seconds)
    try:
        source=attempt/('reist-x86_64.img' if layout=='hdd' else 'reist-x86_64-floppy.img')
        medium=guest.bios.BootMedium(source,folder/'boot-medium',layout,'normal',started+seconds)
        medium.verify('before');fixture=data_fixture(folder,files,started,seconds);fixture.verify('before')
        check.need(fixture.base.read_bytes()==check.bounded(attempt/'system.ext2',1048576),'published display session data')
        command=[str(guest.bios.ay.boot.resolve_qemu(None)),'-machine','pc,accel=tcg','-cpu','qemu64',
            '-m',str(ram)+'M','-smp','1','-display','none' if headless else 'gtk',
            '-vga','none','-device','VGA,vgamem_mb=16','-monitor','none','-nic','none',
            '-serial','stdio','-no-reboot','-no-shutdown']
        command+=fixture.arguments(folder)+guest.boot_arguments(medium.overlay,layout)
        (folder/'command.json').write_text(json.dumps(command),encoding='utf-8')
        remaining=started+seconds-3-time.monotonic();check.need(remaining>0,'display setup deadline')
        print('REIST native64 Grafik: serielle Shell; boot.prg zeichnet das Testfeld.\n'
              'Max.'+str(seconds)+'s, zwei Shell-Laeufe, Ctrl+C beendet.\nNachweise: '+str(folder),flush=True)
        vm=subprocess.Popen(command,cwd=check.ROOT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            result['returncode']=vm.wait(timeout=remaining)
            check.need(result['returncode']==0,'QEMU display session error')
            result['reason']='guest-exit'
        except subprocess.TimeoutExpired:result['reason']='session-deadline'
        except KeyboardInterrupt:result['reason']='user-exit'
    except BaseException as error:result['error']=str(error);raise
    finally:
        cleanup=time.monotonic()
        try:
            try:
                if vm is not None:guest.bios.ay.boot.terminate_bounded(vm)
            finally:
                try:
                    if fixture is not None:fixture.verify('after')
                finally:
                    if medium is not None:medium.verify('after')
            result['elapsed']=time.monotonic()-started;result['cleanup_seconds']=time.monotonic()-cleanup
            check.need(result['elapsed']<=seconds and result['cleanup_seconds']<=3,'display whole-session cleanup deadline')
            result['passed']='reason' in result and 'error' not in result
        except BaseException as error:
            result['passed']=False;result['cleanup_error']=str(error);raise
        finally:
            with (folder/'session.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
    check.need(result['passed'],'display session failed');return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,default=DEFAULT)
    p.add_argument('--layout',choices=('hdd','floppy'),default='hdd');p.add_argument('--ram',type=int,choices=(4096,8192),default=4096)
    p.add_argument('--check-only',action='store_true');p.add_argument('--headless',action='store_true')
    p.add_argument('--seconds',type=int,default=320);p.add_argument('--openssl');a=p.parse_args()
    launch(a.directory,layout=a.layout,ram=a.ram,check_only=a.check_only,headless=a.headless,seconds=a.seconds,openssl=a.openssl)

if __name__=='__main__':main()
