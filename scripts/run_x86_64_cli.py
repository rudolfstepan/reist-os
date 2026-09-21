"""Validate first, then launch one bounded serial BIOS-only research session."""
from pathlib import Path
import argparse,json,subprocess,time,uuid
import check_x86_64_cli_media as check
import run_qemu_x86_64_cli_media as guest
DEFAULT=check.ROOT/'build/codex-agent/r83bd-cli-delivery/candidate01/media'
SESSION_LIMIT=320

def launch(directory=DEFAULT,*,layout='hdd',ram=4096,check_only=False,openssl=None):
    check.need(layout in ('hdd','floppy') and type(ram) is int and ram in (4096,8192) and
               type(check_only) is bool,'supported explicit CLI session')
    attempt=check.verify(directory,openssl=openssl)
    if check_only:
        print('CLI_CHECK_OK',attempt,flush=True);return dict(passed=True,check_only=True,attempt=str(attempt))
    values={n:check.bounded(attempt/n,check.FILES[n]) for n in check.PINS}
    check.input_binding(values);files=check.medium_files(values)
    folder=check.ROOT/'build/codex-agent/cli-sessions'/('session-'+uuid.uuid4().hex)
    folder.mkdir(parents=True);started=time.monotonic();medium=None;fixture=None;vm=None
    result=dict(passed=False,attempt=str(attempt),layout=layout,ram=ram,limit=SESSION_LIMIT)
    try:
        source=attempt/('reist-x86_64.img' if layout=='hdd' else 'reist-x86_64-floppy.img')
        medium=guest.bios.BootMedium(source,folder/'boot-medium',layout,'normal',started+SESSION_LIMIT)
        medium.verify('before');fixture=guest.data_fixture(folder,files,started,SESSION_LIMIT);fixture.verify('before')
        check.need(fixture.base.read_bytes()==check.bounded(attempt/'system.ext2',1048576),'published session data')
        command=[str(guest.bios.ay.boot.resolve_qemu(None)),'-machine','pc,accel=tcg','-cpu','qemu64',
            '-m',str(ram)+'M','-smp','1','-display','none','-monitor','none','-nic','none',
            '-serial','stdio','-no-reboot','-no-shutdown']
        command+=fixture.arguments(folder)+guest.boot_arguments(medium.overlay,layout)
        (folder/'command.json').write_text(json.dumps(command),encoding='utf-8')
        remaining=started+SESSION_LIMIT-3-time.monotonic();check.need(remaining>0,'CLI setup deadline')
        print('REIST native64 CLI research: max.320s, zwei Shell-Laeufe, Ctrl+C beendet.\nNachweise: '+str(folder),flush=True)
        vm=subprocess.Popen(command,cwd=check.ROOT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            result['returncode']=vm.wait(timeout=remaining)
            check.need(result['returncode']==0,'QEMU session error')
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
            check.need(result['elapsed']<=SESSION_LIMIT and result['cleanup_seconds']<=3,'CLI whole-session cleanup deadline')
            result['passed']='reason' in result and 'error' not in result
        except BaseException as error:
            result['passed']=False;result['cleanup_error']=str(error);raise
        finally:
            with (folder/'session.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
    check.need(result['passed'],'CLI session failed');return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,default=DEFAULT)
    p.add_argument('--layout',choices=('hdd','floppy'),default='hdd');p.add_argument('--ram',type=int,choices=(4096,8192),default=4096)
    p.add_argument('--check-only',action='store_true');p.add_argument('--openssl');a=p.parse_args()
    launch(a.directory,layout=a.layout,ram=a.ram,check_only=a.check_only,openssl=a.openssl)

if __name__=='__main__':main()
