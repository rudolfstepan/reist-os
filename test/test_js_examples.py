"""Packaged shell examples: layout and strict evidence, execution in the guest gate."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class ExamplesTests(unittest.TestCase):
    def test_examples_packaged_and_documented(self):
        from run_qemu_js_runner import EXAMPLE_CASES
        make = (ROOT / "Makefile").read_text()
        windows = (ROOT / "scripts/build-windows.ps1").read_text()
        docs = (ROOT / "docs/development/JS_SHELL_EXAMPLES.md").read_text()
        self.assertEqual(len(EXAMPLE_CASES), 7)
        for command, marker in EXAMPLE_CASES:
            name = [word for word in command.split() if word.startswith("/htdocs/")][-1]
            relative = name.lstrip("/")
            source = (ROOT / relative).read_text()
            self.assertLess(len(source.encode()), 4096)
            self.assertIn(marker, source)
            self.assertIn(relative + "=" + relative, make)
            self.assertIn("'" + Path(name).name + "'", windows)
            self.assertIn(command, docs)
        self.assertIn("finally", (ROOT / "htdocs/jsread.js").read_text())
        self.assertIn("file.close()", (ROOT / "htdocs/jsread.js").read_text())

    def test_existing_shell_resolution(self):
        shell = (ROOT / "userspace/bin/shell.c").read_text()
        self.assertIn('"/usr/bin"', shell.split('static char search_paths[', 1)[1].split('};', 1)[0])
        self.assertIn('x86os_spawnv(executable, argc, child_argv)', shell)
        self.assertIn('usr/bin/js.prg=$(SYSTEM_PROGRAM_DIR)/JS.PRG', (ROOT / 'Makefile').read_text())
        self.assertIn("'usr/bin/js.prg' = 'JS.PRG'", (ROOT / 'scripts/build-windows.ps1').read_text())

    def test_example_receipts_are_exact_and_ordered(self):
        from run_qemu_js_runner import EXAMPLE_CASES, validate_examples
        markers = [marker for _, marker in EXAMPLE_CASES] * 2
        text = "\n".join(markers) + "\n"
        validate_examples(text)
        validate_examples(text.replace("\n", "\r\n"))
        invalid = [text.replace(markers[0] + "\n", "", 1),
                   text + markers[0] + "\n", text.replace(markers[0], markers[1], 1),
                   text.replace(markers[0], "prefix " + markers[0], 1),
                   text.replace(markers[0], markers[0] + " suffix", 1),
                   text.replace(markers[0], markers[0].replace("_OK", "_FAIL"), 1)]
        swapped = markers.copy()
        swapped[0], swapped[1] = swapped[1], swapped[0]
        invalid.append("\n".join(swapped) + "\n")
        for bad in invalid:
            with self.subTest(bad=bad[:90]), self.assertRaises(ValueError):
                validate_examples(bad)
        for fatal in ("KERNEL PANIC", "*** USER PROCESS PAGE FAULT ***", "js: script exception"):
            with self.subTest(fatal=fatal), self.assertRaises(ValueError):
                validate_examples(text + fatal + "\n")

    def test_image_guard_rejects_changed_empty_or_stale_payloads(self):
        from verify_js_examples_artifacts import same_payload
        self.assertEqual(same_payload(b"original", b"original", "test"),
                         __import__("hashlib").sha256(b"original").hexdigest())
        for wanted, actual in ((b"original", b"changed"), (b"", b""), (b"original", b"")):
            with self.assertRaises(ValueError):
                same_payload(wanted, actual, "test")

    def test_mandelbrot_picture_not_just_success_marker(self):
        from run_qemu_js_runner import mandelbrot_reference, validate_mandelbrot
        rows = mandelbrot_reference()
        self.assertEqual(len(rows), 24)
        self.assertTrue(all(len(row) == 66 for row in rows))
        self.assertEqual(rows, rows[::-1])
        self.assertIn('@', rows[12])
        begin = 'MANDELBROT_BEGIN width=64 height=24 iterations=48\n'
        end = 'MANDELBROT_END\n'
        picture = begin + '\n'.join(rows) + '\n' + end
        validate_mandelbrot(picture * 2)
        for bad in (picture, picture * 3, (picture * 2).replace(rows[0] + '\n', '', 1),
                    (picture * 2).replace('@', '?', 1),
                    (picture * 2).replace('width=64', 'width=63', 1),
                    (picture * 2).replace('MANDELBROT_END', 'MISSING', 1)):
            with self.assertRaises(ValueError):
                validate_mandelbrot(bad)

    def test_program_alias_uses_actual_packaged_directory(self):
        from verify_js_examples_artifacts import short_path
        self.assertEqual(short_path('bin/shell.prg'), 'bin/shell.prg')
        self.assertEqual(short_path('libexec/reist/jswork.prg'), 'libexec/reist/jswork.prg')
        self.assertEqual(short_path('usr/bin/benchmark.prg'), 'usr/bin/benchm~1.prg')


if __name__ == "__main__":
    unittest.main()
