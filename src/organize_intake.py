from pathlib import Path
import csv
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = ROOT / 'context/FILE_RELOCATION_MANIFEST.csv'
    if manifest.exists():
        rows = list(csv.DictReader(manifest.open()))
        for row in rows:
            assert digest(ROOT / row['new_path']) == row['sha256_before']
        print(f'Verified {len(rows)} previously relocated originals')
        return
    mapping = [('C题/C题.pdf', 'docs/problem/2026C/C题.pdf', 'official problem')]
    mapping += [(f'C题/附件/附件{i}.xlsx', f'data/raw/2026C/附件{i}.xlsx', 'original data') for i in range(1, 5)]
    mapping += [(str(p.relative_to(ROOT)), f'data/templates/2026C/{p.name}', 'empty official template') for p in sorted((ROOT / 'C题/附件/附件5').glob('*.xlsx'))]
    mapping += [('format2026.doc', 'docs/rules/format2026.doc', 'official format rules')]
    rows = []
    for old, new, purpose in mapping:
        src, dst = ROOT / old, ROOT / new
        if not src.is_file() or dst.exists():
            raise RuntimeError(f'Relocation conflict or missing source: {old} -> {new}')
        rows.append(dict(old_path=old, new_path=new, purpose=purpose, size_bytes=src.stat().st_size,
                         sha256_before=digest(src), sha256_after='', status='PLANNED', notes='byte-preserving move'))
    def save():
        with manifest.open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    save()
    for row in rows:
        src, dst = ROOT / row['old_path'], ROOT / row['new_path']
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        row['sha256_after'] = digest(dst)
        assert row['sha256_before'] == row['sha256_after']
        row['status'] = 'MOVED_VERIFIED'
        save()
    config = dict(problem='docs/problem/2026C/C题.pdf', raw_dir='data/raw/2026C',
                  template_dir='data/templates/2026C', processed_dir='data/processed/2026C',
                  efficiency_charge=0.9, efficiency_discharge=0.9, capacity_kwh=12000,
                  minimum_kwh=1200, maximum_kwh=10800, initial_kwh=6000,
                  power_kw=5000, dt_hours=1/6, source_time_semantics='preceding_interval_average',
                  seed=2026, mip_gap=1e-8, solver_time_limit_seconds=60)
    (ROOT / 'configs').mkdir(exist_ok=True)
    (ROOT / 'configs/2026c.json').write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n')
    print(f'Moved and hash-verified {len(rows)} originals')


if __name__ == '__main__':
    main()
