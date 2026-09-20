"""Compose unchanged BA runtime proof with AZ BIOS entry and no-write proof."""
from pathlib import Path
import inspect,textwrap,types
import check_x86_64_wide_shell_media as check
import run_qemu_x86_64_wide_file as wide
import run_qemu_x86_64_shell_boot_media as legacy

def data_fixture(folder,app,started,limit):
    check.need(type(limit) is int and limit in (20,30,320,330),'finite composed media limit')
    source=textwrap.dedent(inspect.getsource(wide.Fixture.run))
    source=check.once(source,'limit=900 if self.wide_full else 300','limit='+str(limit))
    namespace=dict(vars(wide));exec(compile(source,'<BB bounded data media>','exec'),namespace)
    cls=wide.old.file.pio.Fixture;fixture=cls.__new__(cls)
    fixture.started=started;fixture.wide_full=False
    fixture.expected=types.MethodType(wide.Fixture.expected,fixture)
    fixture.run=types.MethodType(namespace['run'],fixture)
    cls.__init__(fixture,folder,filesystem='ext2-1k',file_program=app)
    return fixture

def composed_fixture(folder,app,started,case='normal'):
    return data_fixture(folder,app,started,300+legacy.bios_budget(case))

def function(function,namespace,changes):
    source=inspect.getsource(function)
    for before,after in changes:source=check.once(source,before,after)
    filename='<BB '+function.__name__+'>'
    check.linecache.cache[filename]=(len(source),None,source.splitlines(True),filename)
    exec(compile(source,filename,'exec'),namespace)
    return namespace[function.__name__]

selected=check.clone(legacy,[],'reist_wide_shell_bios')
selected.ay=wide.namespace();selected.check=check
selected.composed_fixture=composed_fixture;selected.data_fixture=data_fixture
run_matrix=function(legacy.run_matrix,vars(selected),[
    ('time.monotonic()-begin<560','time.monotonic()-begin<2000'),
    ('limit=45+bios_budget(case)','limit=300+bios_budget(case)'),
    ('ay.bounded_fixture(out,2,app,started-(45-limit))','data_fixture(out,app,started,limit)'),
    ("result['guest_seconds']<=455","result['guest_seconds']<=1730"),
    ("metrics['observe_seconds']<=42","metrics['observe_seconds']<=297")])
CASES=selected.CASES;capture_namespace=selected.capture_namespace
boot_arguments=selected.boot_arguments;validate_bios=selected.validate_bios
physical_entry=selected.physical_entry;entry_phase=selected.entry_phase
bios_budget=selected.bios_budget;negative_budget=selected.negative_budget
ay=selected.ay
