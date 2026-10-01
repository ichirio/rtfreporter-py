"""The four recipes of docs/recipes.md (DM, AE, PK, LB), compared byte-for-byte
with the same programs run by the R package (``data-raw/xcheck/recipes_r.R``
writes ``tests/xcheck_golden/recipes/``)."""

from pathlib import Path

import rtfreporter as rr

GOLDEN = Path(__file__).parent / "xcheck_golden" / "recipes"


def _golden(name):
    return (GOLDEN / f"{name}.rtf").read_text(encoding="ascii").replace("\r\n", "\n")


def _rendered(doc, tmp_path):
    path = tmp_path / "out.rtf"
    rr.generate_rtfreport(doc, str(path), overwrite=True)
    return path.read_text(encoding="ascii").replace("\r\n", "\n")


def test_dm_recipe_matches_r(tmp_path):
    dm = {
        "Characteristic": ["Age (years)", "Age (years)", "Age (years)", "Sex", "Sex"],
        "Statistic": ["n", "Mean (SD)", "Median", "Male, n (%)", "Female, n (%)"],
        "Drug A": ["60", "54.2 (11.3)", "55.0", "31 (51.7%)", "29 (48.3%)"],
        "Drug B": ["58", "56.8 (10.1)", "57.5", "27 (46.6%)", "31 (53.4%)"],
    }
    doc = rr.rtf_tables(
        rr.rtf_document(page=rr.rtf_page(orientation="landscape")),
        rr.as_rtftables(dm, group_col="Characteristic", split="group_safe",
                        max_rows=20, border="tfl"),
        titles=[["Table 14.1.1", "Demographic and Baseline Characteristics",
                 "<Safety Analysis Set>"]],
    )
    assert _rendered(doc, tmp_path) == _golden("dm")


def test_ae_recipe_matches_r(tmp_path):
    ae = {
        "SOC": ["Cardiac disorders"] * 2 + ["Gastrointestinal disorders"] * 3,
        "PT": ["Atrial fibrillation", "Bradycardia", "Nausea", "Vomiting", "Diarrhoea"],
        "Drug A": ["3 (5.0%)", "1 (1.7%)", "8 (13.3%)", "4 (6.7%)", "2 (3.3%)"],
        "Drug B": ["2 (3.4%)", "0", "6 (10.3%)", "3 (5.2%)", "5 (8.6%)"],
    }
    doc = rr.rtf_tables(
        rr.rtf_document(page=rr.rtf_page(orientation="landscape")),
        rr.as_rtftables(ae, stub=rr.stub_spec(["SOC", "PT"]), group_by="indent",
                        blank_rows="between_groups", split="group_safe",
                        max_rows=20, border="tfl"),
        titles=[["Table 14.3.1",
                 "Adverse Events by System Organ Class and Preferred Term",
                 "<Safety Analysis Set>"]],
        footnotes=[["Percentages use the number of treated subjects."]],
    )
    assert _rendered(doc, tmp_path) == _golden("ae")


def test_pk_recipe_matches_r(tmp_path):
    pk = {
        "Time": ["1 h"] * 3 + ["2 h"] * 3,
        "Statistic": ["n", "Mean", "SD"] * 2,
        "Day 1": ["24", "1104.5", "233.41"] * 2,
        "Day 7": ["24", "88.012", "19.223"] * 2,
        "Day 14": ["24", "9.0125", "2.1044"] * 2,
        "Day 28": ["24", "1234.5", "301.22"] * 2,
    }
    pages = rr.as_rtftables(pk, stub=rr.stub_spec(["Time", "Statistic"]), group_by="indent",
                            blank_rows="between_groups",
                            column_widths_twips=[2000] + [1800] * 4, border="tfl")
    pages = rr.set_decimal_split(pages, cols=["Day 1", "Day 7", "Day 14", "Day 28"])
    pages = rr.paginate_cols(pages, at=3, carry=0)
    doc = rr.rtf_document(page=rr.rtf_page(orientation="landscape"))
    for p in pages:
        doc = rr.rtf_tables(doc, p)
    assert _rendered(doc, tmp_path) == _golden("pk")


def test_lb_recipe_matches_r(tmp_path):
    lb = {
        "PARAMCD": ["ALT"] * 3 + ["AST"] * 3,
        "Baseline": ["Normal", "Grade 1", "Grade 2"] * 2,
        "Normal": ["40", "5", "1", "38", "6", "2"],
        "Grade 1": ["8", "12", "3", "9", "11", "4"],
        "Grade 2": ["1", "4", "7", "2", "3", "6"],
    }
    doc = rr.rtf_tables(
        rr.rtf_document(page=rr.rtf_page(orientation="landscape")),
        rr.as_rtftables(lb, group_col="PARAMCD", drop_cols="PARAMCD",
                        blank_rows="between_groups", border="tfl"),
        titles=[["Table 14.4.1", "Shift from Baseline in Laboratory Grade",
                 "<Safety Analysis Set>"]],
    )
    assert _rendered(doc, tmp_path) == _golden("lb")
