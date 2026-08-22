"""Extra assemble coverage: validation, TOC normalisation, spec I/O, helpers."""

import os

import pytest

import rtfreporter as rr
from rtfreporter.assemble import (
    _insert_bookmark,
    _insert_pgnrestart,
    _normalize_toc,
    _read_spec,
    _rtf_drop_close,
    _rtf_extract_section_content,
    _rtf_table_label,
    _rtf_unescape,
    _spec_to_toc,
    _write_spec,
)


def _gen(path, tnum, title):
    doc = rr.rtf_document()
    doc = rr.rtf_tables(
        doc, {"S": ["1", "2"], "V": [3, 4]}, titles=[f"Table {tnum}", "", title]
    )
    doc = rr.rtf_section(doc, header=rr.rtf_header([{"l": "P", "r": "Page {AUTO_PAGE}"}]))
    rr.generate_rtfreport(doc, str(path), overwrite=True)
    return str(path)


@pytest.fixture
def two_files(tmp_path):
    return (
        _gen(tmp_path / "t14_1_1.rtf", "14.1.1", "Demographics"),
        _gen(tmp_path / "t14_2_1.rtf", "14.2.1", "Adverse Events"),
    )


# -- low-level helpers --------------------------------------------------------


def test_rtf_drop_close_no_trailing_brace_unchanged():
    assert _rtf_drop_close(["a", "b"]) == ["a", "b"]


def test_rtf_extract_section_content_requires_sectd():
    with pytest.raises(ValueError, match="No .sectd"):
        _rtf_extract_section_content(["{\\rtf1", "no section here", "}"])


def test_insert_bookmark_no_sectd_returns_input():
    content = ["\\pard hello", "}"]
    assert _insert_bookmark(content, "bk") == content


def test_insert_bookmark_after_preamble_with_outline():
    content = ["\\sectd", "\\sbkpage", "\\pgwsxn100", "\\pard body"]
    out = _insert_bookmark(content, "bk1", outline_label="My Label", outline_level=1)
    joined = "\n".join(out)
    assert "\\*\\bkmkstart bk1" in joined
    assert "\\outlinelevel1" in joined
    # Bookmark is placed after the preamble lines, before body.
    assert out.index("\\pard body") > out.index(
        "{\\*\\bkmkstart bk1}{\\*\\bkmkend bk1}"
    )


def test_insert_pgnrestart_no_sectd_returns_input():
    content = ["no sectd"]
    assert _insert_pgnrestart(content) == content


def test_insert_pgnrestart_after_sectd():
    out = _insert_pgnrestart(["\\sectd", "\\pard body"])
    assert out[1] == "\\pgnrestart\\pgndec"


def test_rtf_unescape_nbsp():
    assert _rtf_unescape("a\\u160?b") == "a b"


def test_rtf_unescape_braces_and_backslash():
    assert _rtf_unescape("\\{x\\}\\\\y") == "{x}\\y"


# -- _normalize_toc -----------------------------------------------------------


def test_normalize_toc_none():
    assert _normalize_toc(None, ["a.rtf"]) is None


def test_normalize_toc_auto_fallback_to_filename(tmp_path):
    # A file whose page has no title cell -> label falls back to the basename.
    p = tmp_path / "plain.rtf"
    p.write_text("{\\rtf1\\sectd\\sbkpage\\par}")
    q = tmp_path / "plain2.rtf"
    q.write_text("{\\rtf1\\sectd\\sbkpage\\par}")
    out = _normalize_toc("auto", [str(p), str(q)])
    assert out[0]["label"] == "plain"


def test_normalize_toc_entry_file_none_consumes_in_order():
    out = _normalize_toc([rr.toc_entry("A"), rr.toc_entry("B")], ["x.rtf", "y.rtf"])
    assert [e["file_idx"] for e in out] == [0, 1]


def test_normalize_toc_entry_by_int_index():
    out = _normalize_toc([rr.toc_entry("A", file=1)], ["x.rtf", "y.rtf"])
    assert out[0]["file_idx"] == 1


def test_normalize_toc_entry_bad_path_raises():
    with pytest.raises(ValueError, match="not in .input_files"):
        _normalize_toc([rr.toc_entry("A", file="missing.rtf")], ["x.rtf"])


def test_normalize_toc_entry_bad_file_type_raises():
    with pytest.raises(TypeError, match="path or integer"):
        _normalize_toc([rr.toc_entry("A", file=1.5)], ["x.rtf"])


def test_normalize_toc_entry_index_out_of_range():
    with pytest.raises(ValueError, match="out of range"):
        _normalize_toc([rr.toc_entry("A", file=9)], ["x.rtf"])


def test_normalize_toc_bad_element_type():
    with pytest.raises(TypeError, match="toc_heading"):
        _normalize_toc([123], ["x.rtf"])


def test_normalize_toc_bad_toc_type():
    with pytest.raises(TypeError, match="None"):
        _normalize_toc(42, ["x.rtf"])


# -- assemble_rtf validation --------------------------------------------------


def test_assemble_rtf_bad_toc_leader(two_files, tmp_path):
    f1, f2 = two_files
    with pytest.raises(ValueError, match="toc_leader"):
        rr.assemble_rtf([f1, f2], str(tmp_path / "o.rtf"), toc_leader="squiggle")


def test_assemble_rtf_bad_page_numbering(two_files, tmp_path):
    f1, f2 = two_files
    with pytest.raises(ValueError, match="page_numbering"):
        rr.assemble_rtf([f1, f2], str(tmp_path / "o.rtf"), toc_page_numbering="arabic")


def test_assemble_rtf_cover_with_all_fields(two_files, tmp_path):
    f1, f2 = two_files
    out = str(tmp_path / "o.rtf")
    rr.assemble_rtf(
        [f1, f2], out, overwrite=True,
        cover={"title": "T", "subtitle": "S", "date": "2026", "version": "v1",
               "meta": ["line1", "line2"]},
    )
    txt = open(out).read()
    assert "line1" in txt and "line2" in txt and "v1" in txt and "2026" in txt


def test_assemble_rtf_dedupes_bookmark_collisions(tmp_path):
    # Two files whose sanitized basenames collide -> "_1"/"_2" suffixes.
    d1 = tmp_path / "a"
    d2 = tmp_path / "b"
    d1.mkdir()
    d2.mkdir()
    f1 = _gen(d1 / "same.rtf", "1", "One")
    f2 = _gen(d2 / "same.rtf", "2", "Two")
    out = str(tmp_path / "o.rtf")
    rr.assemble_rtf([f1, f2], out, toc="auto", overwrite=True)
    txt = open(out).read()
    assert "tfl_same_1" in txt and "tfl_same_2" in txt


# -- _rtf_table_label ---------------------------------------------------------


def test_rtf_table_label_reads_table_number(two_files):
    info = _rtf_table_label(two_files[0])
    assert info["table"] == "14.1.1"
    assert info["label"].startswith("Table 14.1.1")


def test_rtf_table_label_no_title_uses_basename(tmp_path):
    p = tmp_path / "nodata.rtf"
    p.write_text("{\\rtf1\\sectd\\sbkpage\\par}")
    info = _rtf_table_label(str(p))
    assert info["table"] is None
    assert info["label"] == "nodata"


# -- assemble_files / assemble_spec / assemble_toc errors ---------------------


def test_assemble_files_dir_missing():
    with pytest.raises(FileNotFoundError, match="Directory not found"):
        rr.assemble_files("/no/such/dir/here")


def test_assemble_files_recursive(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    _gen(sub / "t1.rtf", "1", "One")
    _gen(tmp_path / "t2.rtf", "2", "Two")
    files = rr.assemble_files(str(tmp_path), recursive=True)
    assert len(files) == 2


def test_assemble_spec_needs_dir_or_files():
    with pytest.raises(ValueError, match="dir. or .files"):
        rr.assemble_spec()


def test_assemble_spec_no_files_found(tmp_path):
    with pytest.raises(ValueError, match="No RTF files"):
        rr.assemble_spec(files=[])


def test_assemble_toc_needs_files_or_spec():
    with pytest.raises(ValueError, match="files. or .spec"):
        rr.assemble_toc()


def test_assemble_toc_from_spec(two_files):
    spec = rr.assemble_spec(files=list(two_files))
    toc = rr.assemble_toc(spec=spec)
    assert len(toc) == 2


# -- spec csv I/O and spec_to_toc ---------------------------------------------


def test_write_spec_requires_csv(two_files, tmp_path):
    spec = rr.assemble_spec(files=list(two_files))
    with pytest.raises(ValueError, match="end in .csv"):
        _write_spec(spec, str(tmp_path / "spec.txt"))


def test_read_spec_requires_csv():
    with pytest.raises(ValueError, match="end in .csv"):
        _read_spec("spec.txt")


def test_spec_to_toc_dedupes_repeated_headings(two_files):
    spec = rr.assemble_spec(files=list(two_files))
    spec[0]["heading"] = "SAFETY"
    spec[1]["heading"] = "SAFETY"  # repeated -> only one heading emitted
    toc = _spec_to_toc(spec)
    headings = [t for t in toc if type(t).__name__ == "TocHeading"]
    assert len(headings) == 1


# -- assemble_from_spec validation --------------------------------------------


def test_assemble_from_spec_bad_type(tmp_path):
    with pytest.raises(TypeError, match="assembly-spec"):
        rr.assemble_from_spec([{"nope": 1}], str(tmp_path / "o.rtf"))


def test_assemble_from_spec_missing_file(tmp_path):
    spec = [{"file": str(tmp_path / "gone.rtf"), "label": "X", "order": 1, "level": 2}]
    with pytest.raises(FileNotFoundError, match="missing file"):
        rr.assemble_from_spec(spec, str(tmp_path / "o.rtf"))


def test_assemble_from_spec_sorts_by_order(two_files, tmp_path):
    f1, f2 = two_files
    spec = rr.assemble_spec(files=[f1, f2])
    spec[0]["order"], spec[1]["order"] = 2, 1  # reverse
    out = str(tmp_path / "o.rtf")
    rr.assemble_from_spec(spec, out, overwrite=True)
    assert os.path.exists(out)
