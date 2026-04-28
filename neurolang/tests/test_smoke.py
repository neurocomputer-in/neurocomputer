import neurolang


def test_version_present():
    assert hasattr(neurolang, "__version__")
    assert isinstance(neurolang.__version__, str)
    assert len(neurolang.__version__) > 0
