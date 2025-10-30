from backend import config


def test_config_paths_created(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", "data/test_artifacts")
    resolved = config.ensure_dirs()
    data_dir = config.REPO_ROOT / resolved["DATA_DIR"]
    assert (data_dir / "db").exists()
    assert (data_dir / "transcripts").exists()
    assert (data_dir / "uploads").exists()
    assert (data_dir / "raw").exists()
    sample_dir = config.REPO_ROOT / resolved["SAMPLE_DIR"]
    assert sample_dir.exists()
