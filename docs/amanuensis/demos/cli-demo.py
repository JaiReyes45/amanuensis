"""Run a disposable scan/checkpoint/update demonstration; no network access."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[3]
CLI = PROJECT / 'scripts' / 'amanuensis.py'


def main():
    with tempfile.TemporaryDirectory(prefix='amanuensis-demo-') as temporary:
        root = Path(temporary)
        (root / 'package.json').write_text(json.dumps({
            'scripts': {'start': 'node index.js'},
            'dependencies': {'example-library': '1.0.0'},
        }), encoding='utf-8')
        (root / 'index.js').write_text('console.log("demo");\n', encoding='utf-8')

        def run(command):
            print(f'$ python scripts/amanuensis.py {command} --root <temporary-fixture>', flush=True)
            result = subprocess.run([sys.executable, str(CLI), command, '--root', str(root)],
                                    capture_output=True, text=True)
            print(result.stdout.strip(), flush=True)
            if result.stderr:
                print(result.stderr.strip(), flush=True)
            print(f'Exit status: {result.returncode}\n', flush=True)
            if result.returncode:
                raise RuntimeError(f'{command} failed')

        run('scan')
        manifest = json.loads((root / '.amanuensis/project-manifest.json').read_text(encoding='utf-8'))
        # Exercise the real contract without pretending the fixture is a full handoff.
        import importlib.util
        spec = importlib.util.spec_from_file_location('amanuensis_demo_cli', CLI)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        (root / 'PROJECT_DOCUMENTATION.md').write_text(
            '# Disposable CLI contract fixture\n\n' + '\n\n'.join(
                f'## {section}\n\nDemonstration fixture only; not an agent-generated project handoff.'
                for section in module.SECTIONS), encoding='utf-8')
        items = [{'id': f'fixture-{i}', 'section': section, 'status': 'unavailable',
                  'summary': 'Intentionally outside this CLI contract demonstration.'}
                 for i, section in enumerate(module.SECTIONS)]
        items[1].update(status='observed', kind='source',
                        summary='The fixture contains index.js as a JavaScript entry point.',
                        sources=['index.js'], observed_at=module.now(),
                        input_fingerprint=manifest['fingerprint'])
        (root / '.amanuensis/evidence-index.json').write_text(
            json.dumps({'items': items}), encoding='utf-8')
        print('Prepared all required headings and evidence records; 11 gaps are intentional.\n', flush=True)
        run('validate')
        run('checkpoint')
        (root / 'index.js').write_text('console.log("updated demo");\n', encoding='utf-8')
        print('Changed index.js after the documented baseline.\n', flush=True)
        run('scan')
        updated = json.loads((root / '.amanuensis/project-manifest.json').read_text(encoding='utf-8'))
        assert updated['changes']['modified'] == ['index.js']
        assert 'fixture-1' in updated['review_evidence_ids']
        print('PASS: source modification detected and architecture evidence marked for review.', flush=True)
    print('Temporary fixture cleaned up; no project code was executed.', flush=True)


if __name__ == '__main__':
    main()
