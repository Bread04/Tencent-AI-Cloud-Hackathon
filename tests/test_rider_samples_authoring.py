"""Public sample authoring stays repeatable and survives route regeneration."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_sample_regeneration_is_idempotent_matches_catalog_and_route_builder_retains_block(tmp_path):
    for relative in ("scripts/build_remaining_samples.py", "scripts/build_route_samples.py",
                     "prototypes/ryde-app/data.js", "data/prototype/rider-catalog.json"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    shutil.copytree(ROOT / "data/cases", tmp_path / "data/cases")
    (tmp_path / "fixtures/stub").mkdir(parents=True)
    outputs = [tmp_path / "prototypes/ryde-app/data.js", tmp_path / "data/prototype/rider-catalog.json"]
    metadata = json.loads(outputs[1].read_text(encoding="utf-8"))
    metadata.update({"schema_version": "prototype-1", "simulated": True})
    outputs[1].write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    def public_catalog(path):
        raw = subprocess.check_output(["node", "-e",
            "const d=require(process.argv[1]);process.stdout.write(JSON.stringify({riders:d.riders(),trips:d.riders().flatMap(r=>d.trips(r.id))}));",
            str(path)], cwd=tmp_path, encoding="utf-8")
        return json.loads(raw)
    baseline_public = public_catalog(outputs[0])
    protected = [ROOT / f"data/cases/disp-{number:03}.json" for number in (5, 6, 7)]
    original = {path: path.read_bytes() for path in protected}
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    def regenerate(name):
        subprocess.run([sys.executable, str(tmp_path / "scripts" / name)], cwd=tmp_path, env=env, check=True, capture_output=True)
    def hashes():
        return [hashlib.sha256(path.read_bytes()).hexdigest() for path in outputs]
    regenerate("build_remaining_samples.py")
    first = hashes()
    assert public_catalog(outputs[0]) == baseline_public
    original_catalog = json.loads(outputs[1].read_text(encoding="utf-8"))
    assert {key: original_catalog[key] for key in ("riders", "trips")} == baseline_public
    assert original_catalog["schema_version"] == "prototype-1" and original_catalog["simulated"] is True
    regenerate("build_remaining_samples.py")
    assert hashes() == first
    regenerate("build_route_samples.py")
    assert hashes()[0] == first[0]
    # The older route builder writes whole-number float amounts as 1.0 while
    # Node's public API serializes them as 1. Public records must stay identical.
    assert json.loads(outputs[1].read_text(encoding="utf-8")) == original_catalog
    public = json.loads(subprocess.check_output(["node", "-e",
        "const d=require('./prototypes/ryde-app/data.js');process.stdout.write(JSON.stringify({riders:d.riders(),trips:d.riders().flatMap(r=>d.trips(r.id))}));"],
        cwd=tmp_path, encoding="utf-8"))
    catalog = json.loads(outputs[1].read_text(encoding="utf-8"))
    assert {key: catalog[key] for key in ("riders", "trips")} == public == baseline_public
    assert len(catalog["riders"]) == 6 and len(catalog["trips"]) == 11
    assert sorted(trip["sampleReport"]["id"] for trip in catalog["trips"] if "sampleReport" in trip) == [f"DISP-{n:03}" for n in range(2, 11)]
    for path, before in original.items():
        assert path.read_bytes() == before
        assert (tmp_path / "data/cases" / path.name).read_bytes() == before
