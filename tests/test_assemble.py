"""Phase 5: the assemble family and TOC generation."""

import os

import pytest

import rtfreporter as rr
from rtfreporter.assemble import (
    _count_rtf_pages,
    _extract_first_title,
    _natural_order,
    _read_lines,
    _rtf_drop_close,
    _sanitize_bookmark,
    _title_cells,
    _toc_escape,
)


def _gen(path, tnum, title):
    doc = rr.rtf_document()
    doc = rr.rtf_tables(doc, {"S": ["1", "2"], "V": [3, 4]},
                        titles=[f"Table {tnum}", "", title])
    doc = rr.rtf_section(doc, header=rr.rtf_header([{"l": "P", "r": "Page {AUTO_PAGE}"}]))
    rr.generate_rtfreport(doc, str(path), overwrite=True)
    return str(path)


@pytest.fixture
def two_files(tmp_path):
    return (
        _gen(tmp_path / "t14_1_1.rtf", "14.1.1", "Demographics"),
        _gen(tmp_path / "t14_2_1.rtf", "14.2.1", "Adverse Events"),
    )


# -- helpers ------------------------------------------------------------------


def test_sanitize_bookmark():
    assert _sanitize_bookmark("t14_1_1.rtf") == "t14_1_1"
    assert _sanitize_bookmark("14 weird!.rtf").startswith("bk_")


def test_toc_escape():
    assert _toc_escape("a{b}c\\d") == "a\\{b\\}c\\\\d"
    assert _toc_escape("café") == "caf\\u233?"


def test_natural_order():
    order = _natural_order(["t10", "t2", "t1"])
    assert [["t10", "t2", "t1"][i] for i in order] == ["t1", "t2", "t10"]


def test_rtf_drop_close():
    assert _rtf_drop_close(["a", "b", "}"]) == ["a", "b"]
    assert _rtf_drop_close(["a", "}", ""]) == ["a", ""]


def test_extract_first_title(two_files):
    f1, _ = two_files
    assert _extract_first_title(_read_lines(f1)) == "Table 14.1.1"
    assert _title_cells(_read_lines(f1)) == ["Table 14.1.1", "Demographics"]


def test_count_pages(two_files):
    f1, _ = two_files
    assert _count_rtf_pages(_read_lines(f1)) == 1


# -- toc constructors ---------------------------------------------------------


def test_toc_heading_and_entry():
    h = rr.toc_heading("SAFETY", level=1)
    e = rr.toc_entry("Table 1", file="a.rtf", level=2)
    assert h.label == "SAFETY" and h.level == 1
    assert e.label == "Table 1" and e.file == "a.rtf" and e.level == 2


# -- assemble_rtf -------------------------------------------------------------


def test_assemble_rtf_plain(two_files, tmp_path):
    f1, f2 = two_files
    out = str(tmp_path / "out.rtf")
    rr.assemble_rtf([f1, f2], out, overwrite=True)
    txt = open(out).read()
    assert txt.rstrip().endswith("}")
    assert "Table of Contents" not in txt  # no TOC requested
    assert txt.count("\\sect") >= 1  # section joins


def test_assemble_rtf_auto_toc(two_files, tmp_path):
    f1, f2 = two_files
    out = str(tmp_path / "out.rtf")
    rr.assemble_rtf([f1, f2], out, toc="auto", overwrite=True)
    txt = open(out).read()
    assert "Table of Contents" in txt
    assert txt.count("HYPERLINK") == 2
    assert "{\\fldrslt Table 14.1.1}" in txt
    assert "{\\fldrslt Table 14.2.1}" in txt
    assert "\\*\\bkmkstart tfl_t14_1_1" in txt


def test_assemble_rtf_label_list(two_files, tmp_path):
    f1, f2 = two_files
    out = str(tmp_path / "out.rtf")
    rr.assemble_rtf([f1, f2], out, toc=["First", "Second"], overwrite=True)
    txt = open(out).read()
    assert "{\\fldrslt First}" in txt and "{\\fldrslt Second}" in txt


def test_assemble_rtf_structured_toc(two_files, tmp_path):
    f1, f2 = two_files
    out = str(tmp_path / "out.rtf")
    rr.assemble_rtf(
        [f1, f2], out,
        toc=[rr.toc_heading("EFFICACY"), rr.toc_entry("Demographics", file=f1),
             rr.toc_heading("SAFETY"), rr.toc_entry("AEs", file=f2)],
        overwrite=True,
    )
    txt = open(out).read()
    assert "EFFICACY" in txt and "SAFETY" in txt
    assert "{\\fldrslt Demographics}" in txt


def test_assemble_rtf_cover_and_roman(two_files, tmp_path):
    f1, f2 = two_files
    out = str(tmp_path / "out.rtf")
    rr.assemble_rtf(
        [f1, f2], out, cover={"title": "Study XYZ", "subtitle": "Final"},
        toc="auto", toc_page_numbering="roman", overwrite=True,
    )
    txt = open(out).read()
    assert "Study XYZ" in txt
    assert "\\pgnlcrm" in txt  # roman TOC numbering
    assert "\\pgnrestart\\pgndec" in txt  # body restarts decimal


def test_assemble_rtf_requires_two(tmp_path):
    with pytest.raises(ValueError, match="at least 2"):
        rr.assemble_rtf(["only.rtf"], str(tmp_path / "o.rtf"))


def test_assemble_rtf_missing_input(two_files, tmp_path):
    f1, _ = two_files
    with pytest.raises(FileNotFoundError):
        rr.assemble_rtf([f1, str(tmp_path / "nope.rtf")], str(tmp_path / "o.rtf"))


def test_assemble_rtf_no_overwrite(two_files, tmp_path):
    f1, f2 = two_files
    out = tmp_path / "out.rtf"
    out.write_text("x")
    with pytest.raises(FileExistsError):
        rr.assemble_rtf([f1, f2], str(out))


def test_assemble_rtf_bad_toc_length(two_files, tmp_path):
    f1, f2 = two_files
    with pytest.raises(ValueError, match="same length"):
        rr.assemble_rtf([f1, f2], str(tmp_path / "o.rtf"), toc=["only one"])


# -- spec / files / folder ----------------------------------------------------


def test_assemble_files_natural_sorted(tmp_path):
    _gen(tmp_path / "t10.rtf", "10", "Ten")
    _gen(tmp_path / "t2.rtf", "2", "Two")
    files = rr.assemble_files(str(tmp_path))
    assert [os.path.basename(f) for f in files] == ["t2.rtf", "t10.rtf"]


def test_assemble_spec_reads_titles(two_files):
    f1, f2 = two_files
    spec = rr.assemble_spec(files=[f1, f2])
    assert spec[0]["table"] == "14.1.1"
    assert "Demographics" in spec[0]["label"]
    assert spec[0]["pages"] == 1


def test_assemble_toc_from_files(two_files):
    from rtfreporter.assemble import TocEntry

    f1, f2 = two_files
    toc = rr.assemble_toc(files=[f1, f2])
    assert len(toc) == 2
    assert all(isinstance(t, TocEntry) for t in toc)


def test_assemble_from_spec_with_heading(two_files, tmp_path):
    f1, f2 = two_files
    spec = rr.assemble_spec(files=[f1, f2])
    spec[0]["heading"] = "EFFICACY"
    out = str(tmp_path / "out.rtf")
    rr.assemble_from_spec(spec, out, overwrite=True)
    assert "EFFICACY" in open(out).read()


def test_assemble_from_spec_csv_roundtrip(two_files, tmp_path):
    f1, f2 = two_files
    spec = rr.assemble_spec(files=[f1, f2])
    csv_path = str(tmp_path / "spec.csv")
    from rtfreporter.assemble import _read_spec, _write_spec

    _write_spec(spec, csv_path)
    reloaded = _read_spec(csv_path)
    assert reloaded[0]["file"] == spec[0]["file"]
    out = str(tmp_path / "out.rtf")
    rr.assemble_from_spec(csv_path, out, overwrite=True)
    assert os.path.exists(out)


def test_assemble_folder_end_to_end(tmp_path):
    _gen(tmp_path / "t14_1_1.rtf", "14.1.1", "Demographics")
    _gen(tmp_path / "t14_2_1.rtf", "14.2.1", "Adverse Events")
    out = str(tmp_path / "deliverable.rtf")
    spec_file = str(tmp_path / "spec.csv")
    res = rr.assemble_folder(str(tmp_path), out, spec_file=spec_file, overwrite=True)
    assert os.path.exists(out)
    assert os.path.exists(spec_file)
    assert len(res["spec"]) == 2
    txt = open(out).read()
    assert "Table of Contents" in txt
    assert txt.count("HYPERLINK") == 2
