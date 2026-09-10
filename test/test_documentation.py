"""First-party documentation inventory, local links and accepted-state regressions.

Read-only repository inspection; no build, VM, network or runtime acceptance.
"""
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import time
import tomllib
import unittest
from urllib.parse import unquote, urlsplit
import uuid

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ('README.md', 'assets/audio/README.md', 'assets/fonts/README.md',
         'assets/icons/README.md', 'drivers/usb/usb_recommendations.md',
         'scripts/README_TESTING.md', 'scripts/TESTING_SUMMARY.md', 'userspace/gui/README.md')


def inventory():
    return sorted([ROOT / name for name in LOCAL] + list((ROOT / 'docs').rglob('*.md')))


def prose(text):
    return re.sub(r'(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$', '', text)


def anchors(text):
    found, counts = set(), {}
    for heading in re.findall(r'(?m)^#{1,6}\s+(.+?)\s*#*$', prose(text)):
        slug = html.unescape(re.sub(r'<[^>]+>', '', heading)).lower()
        slug = re.sub(r'[^\w\- ]', '', slug).replace(' ', '-')
        count = counts.get(slug, 0)
        found.add(slug + ('-' + str(count) if count else ''))
        counts[slug] = count + 1
    found.update(re.findall(r'(?i)<a\s+(?:name|id)=[\"\']([^\"\']+)', text))
    return found


def local_links(text):
    # Ignore examples inside fenced code, not real image or inline links.
    for raw in re.findall(r'\[[^\]\n]*\]\(([^\n]+?)\)', prose(text)):
        target = raw[1:raw.index('>')] if raw.startswith('<') else raw.split()[0]
        if not urlsplit(target).scheme and not target.startswith('//'):
            yield unquote(target)
    for raw in re.findall(r'(?m)^\[[^\]]+\]:\s*(\S+)', prose(text)):
        if not urlsplit(raw).scheme:
            yield unquote(raw.strip('<>'))


def link_errors(path, text):
    errors = []
    for link in local_links(text):
        target, _, anchor = link.partition('#')
        file = (path.parent / target).resolve() if target else path
        if not file.is_relative_to(ROOT) or not file.exists():
            errors.append(link + ' (missing/outside repository)')
        elif anchor and file.suffix.lower() == '.md' and anchor not in anchors(file.read_text(encoding='utf-8')):
            errors.append(link + ' (missing heading)')
    return errors


class DocumentationTests(unittest.TestCase):
    def test_full_inventory_local_links_and_index(self):
        started = time.monotonic()
        files = inventory()
        index = (ROOT / 'docs/README.md').read_text(encoding='utf-8')
        indexed = {(ROOT / 'docs' / link.split('#')[0]).resolve() for link in local_links(index)}
        report = {'documents': [], 'errors': [], 'external_links_checked': False}
        for file in files:
            content = file.read_text(encoding='utf-8')
            name = file.relative_to(ROOT).as_posix()
            errors = link_errors(file, content)
            if file.name != 'README.md' or file.parent != ROOT / 'docs':
                if file.resolve() not in indexed:
                    errors.append('not linked from the complete documentation index')
            report['documents'].append({'path': name, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
                                        'local_links': len(list(local_links(content)))})
            report['errors'].extend(name + ': ' + error for error in errors)
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        target = ROOT / 'build/codex-agent/d11-documentation' / ('inventory-' + uuid.uuid4().hex + '.json')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print('Documentation inventory:', len(files), 'files;', target.relative_to(ROOT))
        self.assertGreaterEqual(len(files), 105)
        self.assertEqual(report['errors'], [], '\n'.join(report['errors']))

    def test_scanner_negative_and_heading_cases(self):
        path = ROOT / 'README.md'
        self.assertTrue(link_errors(path, '[broken](does-not-exist.md)'))
        self.assertTrue(link_errors(path, '[bad](README.md#not-a-real-heading)'))
        self.assertTrue(link_errors(path, '[outside](../../outside.md)'))
        self.assertEqual(link_errors(path, '[valid](docs/README.md)'), [])
        self.assertEqual(list(local_links('```text\n[example](missing.md)\n```')), [])
        self.assertEqual(list(local_links('[web](https://example.test/a)')), [])
        self.assertEqual(anchors('# Test\n## Test\n## Größe und `API`\n'),
                         {'test', 'test-1', 'größe-und-api'})

    def test_current_overviews_and_pending_authority(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertRegex(readme, r'Stand dieser Dokumentation:\s+\d{1,2}\. \w+ \d{4}')
        for value in ('512 MiB', '1024 MiB', 'js /htdocs/mandel.js'):
            self.assertIn(value, readme)
        status = (ROOT / 'docs/development/PROJECT_STATUS.md').read_text(encoding='utf-8')[:10000]
        for value in ('R3.43', 'R3.42', 'R3.36', 'R341-H1', 'R341-H2', 'Farbausgabe'):
            self.assertIn(value, status)
        issues = (ROOT / 'docs/development/KNOWN_ISSUES.md').read_text(encoding='utf-8')
        for value in ('R341-H1', 'R341-H2', 'R3.6b', 'JS-Schreibrechte', 'Farbausgabe'):
            self.assertIn(value, issues)

    def test_documented_abi_matches_authoritative_header(self):
        abi = (ROOT / 'include/reist/abi/syscall.h').read_text()
        count = int(re.search(r'#define REIST_SYSCALL_COUNT (\d+)U', abi)[1])
        architecture = (ROOT / 'docs/architecture/REIST_ARCHITECTURE.md').read_text(encoding='utf-8')[:6000]
        self.assertIn(f'0 bis {count-1}', architecture)
        self.assertIn(f'{count} Einträge', architecture)
        for name in ('PROCESS_RESTRICT', 'FILE_OBJECT_GUARD', 'STORAGE_JOURNAL_IO'):
            self.assertIn(name, architecture)

    def test_proposed_cli_and_policy_do_not_claim_current_authority(self):
        paper = (ROOT / 'docs/development/OS_JAVASCRIPT_SCRIPTING_WORK_PAPER.md').read_text(encoding='utf-8')
        for text in ('noch nicht implementiert', 'system.exit', 'setExitCode',
                     'Kernel und zuständiger', 'Signaturen belegen Herkunft und Integrität',
                     'niemals Privilegien erzeugen', 'dieselben geladenen Skriptbytes',
                     'Kindprozesse erben nicht automatisch', 'R3.36', 'R3.42'):
            self.assertIn(text, paper)
        issues = (ROOT / 'docs/development/KNOWN_ISSUES.md').read_text(encoding='utf-8')
        self.assertIn('signierte Skriptmanifeste', issues)

    def test_shell_guide_does_not_invent_quote_or_color_support(self):
        guide = (ROOT / 'docs/features/SHELL_ENHANCEMENTS.md').read_text(encoding='utf-8')
        self.assertNotIn('doppelte Anführungszeichen schützen', guide)
        self.assertIn('keine Quote-Auswertung', guide)
        self.assertIn('Farbausgabe', guide)
        self.assertIn('noch nicht', guide)
        shell = (ROOT / 'userspace/bin/shell.c').read_text()
        self.assertIn('#define SHELL_LINE_CAPACITY 256', shell)
        self.assertIn('#define SHELL_MAX_ARGUMENTS 16', shell)

    def test_only_documentation_scope_and_prior_evidence_unchanged(self):
        def git(*args):
            return subprocess.check_output(['git', *args], cwd=ROOT, timeout=15).decode('utf-8')
        current = tomllib.loads((ROOT / 'automation/reist-s03b.toml').read_text(encoding='utf-8'))
        # This is a candidate-scope check, not a permanent prohibition on later
        # runtime packages. The definition HEAD also admits final queue bookkeeping.
        if current['active_id'] != 'D1.1-documentation-refresh':
            if git('rev-parse', 'HEAD').strip() != git('rev-parse', 'baaa962b').strip():
                self.skipTest('D1.1 candidate scope does not govern later packages')
        baseline = tomllib.loads(git('show', 'a3fa8dfb:automation/reist-s03b.toml'))
        self.assertEqual([p['id'] for p in current['packages'] if p['status'] == 'active'], [current['active_id']])
        by_id = {p['id']: p for p in current['packages']}
        frozen = tomllib.loads(git('show', 'baaa962b:automation/reist-s03b.toml'))
        definition = next(p for p in frozen['packages'] if p['id'] == 'D1.1-documentation-refresh')
        for key, value in definition.items():
            if key not in ('status', 'evidence'):
                self.assertEqual(by_id[definition['id']][key], value, key)
        for old in baseline['packages']:
            now = by_id[old['id']].copy()
            previous = old.copy()
            if old['id'] == 'R3.6b-vmware-pointer-pinned-mutex':
                previous.pop('status'); now.pop('status')
            self.assertEqual(previous, now, old['id'])
        changed = set(git('diff', '--name-only', 'a3fa8dfb').splitlines())
        changed.update(git('ls-files', '--others', '--exclude-standard').splitlines())
        allowed = {p.relative_to(ROOT).as_posix() for p in inventory()}
        allowed.update(('automation/reist-s03b.toml', 'test/test_documentation.py'))
        self.assertLessEqual(changed, allowed)


if __name__ == '__main__':
    unittest.main()
