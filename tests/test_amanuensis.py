"""Behavioral tests; fixtures never execute project code or access the network."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "amanuensis.py"


class AmanuensisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_cli(self, *args, ok=True):
        result = subprocess.run(
            [__import__('sys').executable, str(SCRIPT), *args, '--root', str(self.root)],
            capture_output=True, text=True,
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    def read_json(self, name):
        return json.loads((self.root / '.amanuensis' / name).read_text(encoding='utf-8'))

    def test_scan_is_compact_and_excludes_secrets_generated_and_own_output(self):
        self.write('web/package.json', json.dumps({'scripts': {'dev': 'TOKEN=SECRET vite'},
                   'dependencies': {'react': '^19.0.0'}}))
        self.write('api/pyproject.toml', '[project]\nname="api"\ndependencies=["fastapi>=0.1"]\n')
        for name in ['.env', '.env.local', 'private.pem', 'node_modules/lib/index.js',
                     'PROJECT_DOCUMENTATION.md', 'docs/amanuensis/screenshots/a.png']:
            self.write(name, 'TOP_SECRET')
        self.write('.env.example', 'API_TOKEN=TOP_SECRET\nPORT=3000\n')
        result = self.run_cli('scan')
        manifest = self.read_json('project-manifest.json')
        serialized = json.dumps(manifest)
        self.assertNotIn('TOP_SECRET', serialized)
        self.assertNotIn('TOKEN=SECRET', serialized)
        self.assertEqual(manifest['packages'][0]['dependencies'], ['fastapi'])
        self.assertEqual(manifest['environment_keys'][0]['keys'], ['API_TOKEN', 'PORT'])
        paths = [item['path'] for item in manifest['files']]
        self.assertNotIn('.env', paths)
        self.assertNotIn('private.pem', paths)
        self.assertNotIn('PROJECT_DOCUMENTATION.md', paths)
        self.assertFalse((self.root / '.amanuensis/state.json').exists())
        self.assertLess(len(result.stdout), 14000)

    def prepare_document(self):
        self.write('main.py', 'print("hello")\n')
        self.run_cli('scan')
        spec = importlib.util.spec_from_file_location('amanuensis', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.module = module
        self.write('PROJECT_DOCUMENTATION.md', '# Example\n\n' + '\n\n'.join(
            '## ' + title + '\n\nFixture documentation.' for title in module.SECTIONS))
        self.write('.amanuensis/evidence-index.json', json.dumps({'items': [
            {'id': 'e' + str(i), 'section': title, 'status': 'unavailable',
             'summary': 'Fixture: live access unavailable.'}
            for i, title in enumerate(module.SECTIONS)]}))

    def test_checkpoint_requires_document_and_evidence(self):
        self.write('main.py', 'pass\n')
        self.run_cli('scan')
        self.run_cli('checkpoint', ok=False)
        self.assertFalse((self.root / '.amanuensis/state.json').exists())

    def test_checkpoint_tracks_add_modify_delete_and_keeps_pending_separate(self):
        self.prepare_document()
        self.run_cli('checkpoint')
        before = self.read_json('state.json')
        self.write('main.py', 'print("changed")\n')
        self.write('new.txt', 'new')
        self.run_cli('scan')
        self.assertEqual(self.read_json('state.json'), before)
        changes = self.read_json('project-manifest.json')['changes']
        self.assertEqual(changes['modified'], ['main.py'])
        self.assertEqual(changes['added'], ['new.txt'])
        (self.root / 'main.py').unlink()
        self.run_cli('scan')
        self.assertEqual(self.read_json('project-manifest.json')['changes']['deleted'], ['main.py'])

    def test_source_changed_after_scan_rejects_checkpoint(self):
        self.prepare_document()
        self.write('main.py', 'new source\n')
        self.run_cli('checkpoint', ok=False)

    def test_missing_media_and_path_escape_are_errors(self):
        self.prepare_document()
        with (self.root / 'PROJECT_DOCUMENTATION.md').open('a', encoding='utf-8') as doc:
            doc.write('\n![missing](docs/amanuensis/missing.png)\n[escape](../private.txt)\n')
        result = self.run_cli('validate', ok=False)
        self.assertIn('missing', result.stderr)
        self.assertIn('outside', result.stderr)

    def test_incomplete_scan_cannot_be_checkpointed(self):
        self.write('one.txt', 'one')
        self.write('two.txt', 'two')
        self.run_cli('scan', '--max-files', '1')
        self.assertFalse(self.read_json('project-manifest.json')['complete'])
        self.run_cli('checkpoint', ok=False)

    def test_project_exclusions_and_observed_evidence_freshness(self):
        self.prepare_document()
        self.write('.amanuensisignore', 'private/\n*.sqlite\n')
        self.write('private/secret.json', '{"token":"secret"}')
        self.write('cache.sqlite', 'private data')
        self.run_cli('scan')
        manifest = self.read_json('project-manifest.json')
        self.assertNotIn('private/secret.json', manifest['hashes'])
        self.assertNotIn('cache.sqlite', manifest['hashes'])
        evidence = self.read_json('evidence-index.json')
        evidence['items'][0].update(status='observed', kind='source', sources=['main.py'],
                                    observed_at='2026-11-21T00:00:00+00:00')
        self.write('.amanuensis/evidence-index.json', json.dumps(evidence))
        self.run_cli('checkpoint', ok=False)
        evidence['items'][0]['input_fingerprint'] = manifest['fingerprint']
        self.write('.amanuensis/evidence-index.json', json.dumps(evidence))
        self.run_cli('checkpoint')

    def test_symlinked_sources_are_not_followed(self):
        self.write('main.py', 'pass')
        try:
            (self.root / 'linked.py').symlink_to(self.root / 'main.py')
        except OSError:
            self.skipTest('Host does not allow unprivileged symlinks')
        self.run_cli('scan')
        self.assertNotIn('linked.py', self.read_json('project-manifest.json')['hashes'])

    def test_parentheses_in_valid_local_links(self):
        self.prepare_document()
        self.write('docs/setup(v2).md', '# Setup')
        self.run_cli('scan')
        with (self.root / 'PROJECT_DOCUMENTATION.md').open('a', encoding='utf-8') as doc:
            doc.write('\n[Setup](docs/setup(v2).md)\n')
        self.run_cli('validate')

    def test_observed_source_requires_a_real_project_file(self):
        self.prepare_document()
        evidence = self.read_json('evidence-index.json')
        evidence['items'][0].update(status='observed', kind='source', sources=['#anchor'],
                                    observed_at='2026-11-21T00:00:00+00:00')
        self.write('.amanuensis/evidence-index.json', json.dumps(evidence))
        self.run_cli('validate', ok=False)

    def test_reparse_detection_and_observation_timestamps(self):
        from types import SimpleNamespace
        self.prepare_document()
        junction = SimpleNamespace(is_symlink=lambda: False,
                                   lstat=lambda: SimpleNamespace(st_file_attributes=1024))
        self.assertTrue(self.module.linked(junction))
        evidence = self.read_json('evidence-index.json')
        evidence['items'][0].update(status='observed', kind='source', sources=['main.py'],
                                    observed_at='not-an-ISO-date')
        self.write('.amanuensis/evidence-index.json', json.dumps(evidence))
        result = self.run_cli('validate', ok=False)
        self.assertIn('ISO 8601', result.stderr)

    def test_disappearing_entry_produces_incomplete_inventory(self):
        from unittest.mock import patch
        self.prepare_document()
        with patch.object(self.module, 'linked', side_effect=FileNotFoundError):
            manifest = self.module.collect(self.root)
        self.assertFalse(manifest['complete'])
        self.assertTrue(manifest['warnings'])

    def test_ancestor_repository_is_not_used(self):
        parent = self.root / 'parent'
        child = parent / 'project'
        child.mkdir(parents=True)
        subprocess.run(['git', 'init', str(parent)], check=True, capture_output=True)
        self.root = child
        self.write('main.py', 'pass')
        self.run_cli('scan')
        self.assertIsNone(self.read_json('project-manifest.json')['git']['commit'])
        self.assertIn('ancestor', ' '.join(self.read_json('project-manifest.json')['warnings']))


if __name__ == '__main__':
    unittest.main()
