"""Compile production ATA PIO transaction functions against a port/time model."""
import os
import json
import time
import uuid
import shutil
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from measure_cpp_baseline import suppress_windows_test_dialogs
sys.path.insert(0, str(ROOT / "test"))
from test_reist_probe_domain import function


class AtaMultipleTests(unittest.TestCase):
    def test_production_transactions(self):
        suppress_windows_test_dialogs()
        source = (ROOT / "drivers/block/ata.c").read_text(encoding="utf-8")
        begin = source.index("static bool ata_pio_wait_status(")
        end = source.index("bool ata_read_sectors(", begin)
        implementation = source[begin:end] + '\n' + '\n'.join(function(source, name) for name in (
            'static bool ata_write_sectors_pio_mode_checked(',
            'static bool ata_write_sectors_pio_deferred_checked('))
        adapters = source[end:source.index("bool ata_read_sector(", end)]
        harness = (ROOT / "test/test_ata_multiple_host.c").read_text(encoding="utf-8")
        self.assertEqual(harness.count("/* PRODUCTION */"), 1)
        tmp=ROOT / 'build/codex-agent/r342-fat32-write' / ('ata-multiple-'+uuid.uuid4().hex)
        tmp.mkdir(parents=True)
        c = tmp / "host.c"
        c.write_text(harness.replace("/* PRODUCTION */", implementation)
            .replace("/* ADAPTER */", adapters), encoding="utf-8")
        records=[]
        compiler=shutil.which('gcc')
        self.assertIsNotNone(compiler)
        for opt in ('-O0','-O2'):
            executable=tmp/(opt[1:]+'.exe')
            for command,budget in (([compiler,'-std=c11',opt,'-I'+str(ROOT),str(c),'-o',str(executable)],90),
                                    ([str(executable)],30)):
                started=time.monotonic()
                run=subprocess.run(command,capture_output=True,text=True,timeout=budget,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                records.append(dict(command=command,returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,
                    elapsed_seconds=time.monotonic()-started))
                (tmp/'result.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
                self.assertEqual(run.returncode,0,str(tmp)+'\n'+run.stdout+run.stderr)
            self.assertIn('ATA_MULTIPLE_HOST_OK',run.stdout)
            print(opt,run.stdout.strip(),flush=True)


if __name__ == "__main__":
    unittest.main()
