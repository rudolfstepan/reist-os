"""Start the native64 input image with a bounded serial shell."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time,uuid
import check_x86_64_input_media as check
import run_qemu_x86_64_cli_media as guest
DEFAULT=check.ROOT/'build/codex-agent/r83bg-input/media05'
SESSIONS=check.ROOT/'build/codex-agent/input-sessions'
INDEX_SHA='d83233b7838ca5ee141363d147acb6c7113ef03c60ae60a1189ecef3844c5bcb'
PINS={'reist-x86_64-c-core.elf': '65738639762f1caceea2c61f0436467b6a15e75fd782d497c96b8a8e42819458', 'reist-x86_64-bootstrap.elf': '8e8aaa4873709983f741c6453dd4f2ced5e699afa8b74b5b1c8589e642b6ff38', 'boot-programs.bin': '1ffec90643c92d3ca2224b3d70eaff4fedf60b06442e17e240c5acde4e14b118', 'file-program.prg': '7ce90b71ad88fb458f194e74e171d0bc637026f0f72a4f16e4a56b4c27dbece2', 'program0.prg': '66ae9e0d8bb361892c084dc8f87b5585bd0e5c0ea4a5fde2e3ae9679bb00ba35', 'program1.prg': '2d4a362fba07a43d8f4b3583b2a6b6a799c510a8fae71c8efda2641708204a6d', 'program2.prg': '96f88b4eebe8865a3aa3a75e0407d495f664c19664740ea5e3333421d1364e89', 'program3.prg': '16cddf76ac48126b5b18c8e044f5a9cfb8c7c2a2319bc7601e018ef77afb0957', 'cat.prg': 'd5535c7b457a41fd076628520fce4cb9d9942874d531b18236c1bfa945a8009e', 'ls.prg': '6fd8aa33b1c2a69a29e18fd180930fcdb22b86af9e0b120439e6bbfff37d7088', 'probe.prg': '01570645fb1ac0aaa8ac7f809182dcfeb136ee6c03308fed745ab34ca50672ec', 'data.txt': 'e3df252557f1cb403da4b9f86a5e17a46ba708bca50dd36c6a7992b21b224d24'}
# Preserve the original absolute tool deadline and immutable media construction.
# Only this new starter accepts every integer in its documented duration range.
data_fixture=guest.bb.function(guest.data_fixture,dict(vars(guest)),[
    ('type(limit) is int and limit in (20,30,320,330)','type(limit) is int and 30<=limit<=320')])

def inputs(values):
    check.need(type(values) is dict and set(values)==set(PINS),'exact pinned input input set')
    for name,sha in PINS.items():
        check.need(type(values[name]) is bytes and hashlib.sha256(values[name]).hexdigest()==sha,'pinned input input '+name)
    check.input_binding(values)

def admit(directory,openssl=None):
    directory=Path(directory);index=directory/'input-media.json'
    check.need(hashlib.sha256(check.bounded(index,16384)).hexdigest()==INDEX_SHA,'pinned signed input index')
    attempt=check.verify(directory,openssl=openssl)
    values={n:check.bounded(attempt/n,check.FILES[n]) for n in PINS};inputs(values)
    check.need(hashlib.sha256(check.bounded(index,16384)).hexdigest()==INDEX_SHA,'stable pinned input index')
    return attempt,check.medium_files(values)

def launch(directory=DEFAULT,*,layout='hdd',ram=4096,check_only=False,headless=False,seconds=320,openssl=None):
    check.need(layout in ('hdd','floppy') and type(ram) is int and ram in (4096,8192) and
               type(check_only) is bool and type(headless) is bool and type(seconds) is int and
               30<=seconds<=320,'supported explicit input session')
    attempt,files=admit(directory,openssl)
    if check_only:
        print('INPUT_CHECK_OK',attempt,flush=True)
        return dict(passed=True,check_only=True,attempt=str(attempt))
    folder=SESSIONS/('session-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    started=time.monotonic();medium=None;fixture=None;vm=None
    result=dict(passed=False,attempt=str(attempt),layout=layout,ram=ram,headless=headless,limit=seconds)
    try:
        source=attempt/('reist-x86_64.img' if layout=='hdd' else 'reist-x86_64-floppy.img')
        medium=guest.bios.BootMedium(source,folder/'boot-medium',layout,'normal',started+seconds)
        medium.verify('before');fixture=data_fixture(folder,files,started,seconds);fixture.verify('before')
        check.need(fixture.base.read_bytes()==check.bounded(attempt/'system.ext2',1048576),'published input session data')
        command=[str(guest.bios.ay.boot.resolve_qemu(None)),'-machine','pc,accel=tcg','-cpu','qemu64',
            '-m',str(ram)+'M','-smp','1','-display','none' if headless else 'gtk',
            '-vga','none','-device','VGA,vgamem_mb=16','-monitor','none','-nic','none',
            '-serial','stdio','-no-reboot','-no-shutdown']
        command+=fixture.arguments(folder)+guest.boot_arguments(medium.overlay,layout)
        (folder/'command.json').write_text(json.dumps(command),encoding='utf-8')
        remaining=started+seconds-3-time.monotonic();check.need(remaining>0,'display setup deadline')
        print('REIST native64 Eingabe: boot.prg startet die fuenfsekundige Eingabesitzung.\n'
              'Tastatur/Maus im Grafikfenster; Befehle in dieser seriellen Shell.\nMax.'+str(seconds)+'s, zwei Shell-Laeufe, Ctrl+C beendet.\nNachweise: '+str(folder),flush=True)
        vm=subprocess.Popen(command,cwd=check.ROOT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            result['returncode']=vm.wait(timeout=remaining)
            check.need(result['returncode']==0,'QEMU input session error')
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
    check.need(result['passed'],'input session failed');return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,default=DEFAULT)
    p.add_argument('--layout',choices=('hdd','floppy'),default='hdd');p.add_argument('--ram',type=int,choices=(4096,8192),default=4096)
    p.add_argument('--check-only',action='store_true');p.add_argument('--headless',action='store_true')
    p.add_argument('--seconds',type=int,default=320);p.add_argument('--openssl');a=p.parse_args()
    launch(a.directory,layout=a.layout,ram=a.ram,check_only=a.check_only,headless=a.headless,seconds=a.seconds,openssl=a.openssl)

if __name__=='__main__':main()
