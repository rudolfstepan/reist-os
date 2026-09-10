import shutil
import hashlib
import json
import subprocess
import sys
import time
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "scripts"))
from measure_cpp_baseline import suppress_windows_test_dialogs
BASELINE = "3e7c02add995b5c33aed045913382dc7ccce2d0f"


class ReistCriticalObjectTests(unittest.TestCase):
    def test_host_fault_injection(self):
        self.run_native(False)

    def test_reference_equivalence_and_cost(self):
        self.run_native(True)

    def test_arithmetic_scope_guard(self):
        from verify_fat32_write_artifacts import critical_protected_source_equal
        old=subprocess.check_output(["git","show",BASELINE+":kernel/init/critical_object.c"],cwd=ROOT,timeout=15).decode("utf-8")
        new=(ROOT / "kernel/init/critical_object.c").read_text(encoding="utf-8")
        self.assertTrue(critical_protected_source_equal(old,new))
        for before,after in (("if ((stored & 0x80U) != 0) return -1;",""),
            ("syndrome != 0 && !overall_mismatch","false"),
            ("copy_crc(copy) != copy->crc32","false"),
            ("object->shadow = candidate;",""),
            ("critical_object_unlock(object, irq_flags);",""),
            ("primary_status < 0 && shadow_status < 0","false")):
            self.assertIn(before,new)
            self.assertFalse(critical_protected_source_equal(old,new.replace(before,after)))

    def run_native(self, equivalence):
        suppress_windows_test_dialogs()
        compiler = shutil.which("gcc") or shutil.which("clang")
        if compiler is None:
            self.skipTest("host C compiler unavailable")
        evidence=ROOT / "build/codex-agent/r342-fat32-write" / ("integrity-"+uuid.uuid4().hex)
        evidence.mkdir(parents=True)
        sources=[ROOT / "kernel/init/critical_object.c"]
        options=[]
        if equivalence:
            old=subprocess.check_output(["git","show",BASELINE+":kernel/init/critical_object.c"],cwd=ROOT,timeout=15).decode("utf-8").replace("\r\n","\n")
            new=(ROOT / "kernel/init/critical_object.c").read_text(encoding="utf-8")
            sources=[];options=["-DCRITICAL_EQUIVALENCE_TEST"]
            for prefix,source in (("reference",old),("candidate",new)):
                names="".join(f"#define critical_object_{name} {prefix}_{name}\n" for name in ("init","read","update")) if prefix=="reference" else ""
                wrappers=f"""
uint8_t {prefix}_encode(uint32_t d) {{ return secded_encode(d); }}
int {prefix}_decode(uint32_t *d, uint8_t c) {{ return secded_decode(d,c); }}
uint32_t {prefix}_crc(const void *p, size_t n, uint32_t c) {{ return crc32_bytes(p,n,c); }}
"""
                path=evidence/(prefix+".c");path.write_text(names+source+wrappers,encoding="utf-8");sources.append(path)
            (evidence / "sources.json").write_text(json.dumps({"reference_commit":BASELINE,
                "reference_sha256":hashlib.sha256(old.encode()).hexdigest(),"candidate_sha256":hashlib.sha256(new.encode()).hexdigest()},indent=2),encoding="utf-8")
        records=[]
        for optimization in ("-O0","-O2"):
            executable=evidence/(optimization[1:]+".exe")
            commands=[[compiler,"-std=c11",optimization,"-Wall","-Wextra","-Werror",*options,"-I",str(ROOT),
                *map(str,sources),str(ROOT / "test/test_critical_object_host.c"),"-o",str(executable)],[str(executable)]]
            for index,command in enumerate(commands):
                started=time.monotonic()
                result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=90 if index==0 else 30,
                    creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                records.append(dict(command=command,returncode=result.returncode,elapsed_seconds=time.monotonic()-started,
                    stdout=result.stdout,stderr=result.stderr))
                (evidence/"result.json").write_text(json.dumps(records,indent=2),encoding="utf-8")
                self.assertEqual(result.returncode,0,str(evidence)+"\n"+result.stdout+result.stderr)
                if index: print(optimization,result.stdout.strip(),flush=True)

    def test_contract_contains_ecc_redundancy_and_semantic_validation(self):
        header = (ROOT / "include/kernel/critical_object.h").read_text(encoding="utf-8")
        source = (ROOT / "kernel/init/critical_object.c").read_text(encoding="utf-8")
        self.assertIn("critical_object_copy_t primary", header)
        self.assertIn("critical_object_copy_t shadow", header)
        self.assertIn("secded_encode", source)
        self.assertIn("secded_decode", source)
        self.assertIn("validator", source)
        self.assertIn("WORD_SEQUENCE", source)
        self.assertIn("copy_crc", source)

    def test_publication_is_bounded_and_smp_safe(self):
        header = (ROOT / "include/kernel/critical_object.h").read_text(encoding="utf-8")
        source = (ROOT / "kernel/init/critical_object.c").read_text(encoding="utf-8")
        self.assertIn("volatile uint32_t publication_lock", header)
        self.assertIn("CRITICAL_OBJECT_LOCK_RETRY_LIMIT", source)
        self.assertIn("__sync_bool_compare_and_swap(&object->publication_lock", source)
        self.assertIn("__sync_lock_release(&object->publication_lock)", source)
        self.assertIn("*irq_flags_out = irq_save()", source)
        self.assertIn("irq_restore(irq_flags)", source)
        self.assertGreaterEqual(
            source.count("critical_object_lock(object, &irq_flags)"), 2
        )


if __name__ == "__main__":
    unittest.main()
