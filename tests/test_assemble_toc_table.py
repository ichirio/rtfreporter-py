"""assemble_folder() without output_file returns the table of contents, and
assemble_rtf(toc=) takes that table (or its .csv path) -- R 0.8.2.9014."""

import warnings

import pytest

import rtfreporter as rr
from rtfreporter.borders import _reset_deprecations


def _gen(path, tnum, title):
    doc = rr.rtf_document()
    doc = rr.rtf_tables(doc, {"S": ["1", "2"], "V": [3, 4]},
                        titles=[f"Table {tnum}", "", title])
    rr.generate_rtfreport(doc, str(path), overwrite=True)
    return str(path)


@pytest.fixture
def folder(tmp_path):
    d = tmp_path / "tfl"
    d.mkdir()
    _gen(d / "t14_2_1.rtf", "14.2.1", "Adverse Events")
    _gen(d / "t14_1_1.rtf", "14.1.1", "Demographics")
    return d


@pytest.fixture(autouse=True)
def no_warnings():
    _reset_deprecations()
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        yield


def test_assemble_folder_without_output_file_returns_the_table(folder):
    spec = rr.assemble_folder(str(folder))
    assert [r["table"] for r in spec] == ["14.1.1", "14.2.1"]
    assert set(spec[0]) == {"order", "file", "table", "heading", "label", "level", "pages"}
    assert spec[0]["label"] == "Table 14.1.1  Demographics"


def test_assemble_rtf_takes_the_table_and_its_files(folder, tmp_path):
    spec = rr.assemble_folder(str(folder))
    spec[0]["heading"] = "DEMOGRAPHICS"
    spec[1]["heading"] = "SAFETY ANALYSES"
    out = rr.assemble_rtf(toc=spec, output_file=str(tmp_path / "book.rtf"))
    rtf = open(out).read()
    assert "DEMOGRAPHICS" in rtf and "SAFETY ANALYSES" in rtf
    assert rtf.index("Demographics") < rtf.index("Adverse Events")
    # the same as the old spelling
    _reset_deprecations()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        old = rr.assemble_from_spec(spec, str(tmp_path / "old.rtf"),
                                    toc_page_numbering="none")
    assert open(old).read() == rtf


def test_the_table_is_ordered_by_order_and_may_be_partial(folder, tmp_path):
    spec = rr.assemble_folder(str(folder))
    rows = [{"file": spec[1]["file"], "label": "AE", "order": 1},
            {"file": spec[0]["file"], "label": "DM", "order": 2, "level": 1}]
    out = rr.assemble_rtf(toc=rows, output_file=str(tmp_path / "o.rtf"))
    rtf = open(out).read()
    assert rtf.index("AE") < rtf.index("DM")


def test_a_dataframe_and_a_csv_path_are_tables(folder, tmp_path):
    pd = pytest.importorskip("pandas")
    csv = tmp_path / "toc.csv"
    rr.assemble_folder(str(folder), spec_file=str(csv))
    a = rr.assemble_rtf(toc=str(csv), output_file=str(tmp_path / "a.rtf"))
    df = pd.read_csv(csv)  # heading is NaN there
    b = rr.assemble_rtf(toc=df, output_file=str(tmp_path / "b.rtf"))
    assert open(a).read() == open(b).read()


def test_the_table_is_checked(folder, tmp_path):
    out = str(tmp_path / "o.rtf")
    with pytest.raises(ValueError, match="`file` and `label`"):
        rr.assemble_rtf(toc=[{"file": "x.rtf"}], output_file=out)
    with pytest.raises(FileNotFoundError, match="names missing file"):
        rr.assemble_rtf(toc=[{"file": "nope.rtf", "label": "x"}] * 2, output_file=out)
    spec = rr.assemble_folder(str(folder))
    with pytest.raises(TypeError, match="output_file"):
        rr.assemble_rtf(toc=spec)
    with pytest.raises(ValueError, match="at least 2"):
        rr.assemble_rtf(output_file=out)


def test_assemble_folder_with_output_file(folder, tmp_path):
    res = rr.assemble_folder(str(folder), str(tmp_path / "o.rtf"))
    assert res["output"].endswith("o.rtf") and len(res["spec"]) == 2


@pytest.mark.parametrize("call, match", [
    (lambda d: rr.assemble_files(d), r"assemble_folder\(dir\)"),
    (lambda d: rr.assemble_spec(d), r"no `output_file`"),
    (lambda d: rr.assemble_toc(spec=rr.assemble_folder(d)), r"assemble_rtf\(toc=\)"),
    (lambda d: rr.toc_heading("H"), r"assemble_rtf\(toc=\)"),
    (lambda d: rr.toc_entry("E"), r"assemble_rtf\(toc=\)"),
])
def test_the_assembly_helpers_are_deprecated(folder, call, match):
    with pytest.warns(DeprecationWarning, match=match):
        call(str(folder))


def test_assemble_toc_from_files_still_works(folder):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        files = rr.assemble_files(str(folder))
        toc = rr.assemble_toc(files=files)
    assert [type(e).__name__ for e in toc] == ["TocEntry", "TocEntry"]
