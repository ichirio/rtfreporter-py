"""rtfplot() on plot objects (R #394): drawn at render_width x render_height
inches and render_dpi, then embedded at that size."""

import os

import pytest

import rtfreporter as rr

mpl = pytest.importorskip("matplotlib")
mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def _mpl_figure():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([1, 2, 3], [2, 1, 3])
    return fig


def test_matplotlib_figure_lands_at_the_render_size():
    fig = _mpl_figure()
    f = rr.rtfplot(fig)
    assert f.img_type == "png"
    assert (f.img_width, f.img_height) == (6.5 * 300, 4.5 * 300)
    d = f.display_twips()
    assert (d["w"], d["h"]) == (9360, 6480)  # 6.5 x 4.5 in
    assert tuple(fig.get_size_inches()) == (3, 2)  # the figure's own size is put back
    plt.close(fig)


def test_render_dpi_changes_sharpness_not_size():
    fig = _mpl_figure()
    f = rr.rtfplot(fig, render_width=4, render_height=3, render_dpi=150)
    assert (f.img_width, f.img_height) == (600, 450)
    d = f.display_twips()
    assert (d["w"], d["h"]) == (4 * 1440, 3 * 1440)
    f2 = rr.rtfplot(fig, width_twips=2880)  # an explicit size still wins
    assert f2.display_twips()["w"] == 2880
    plt.close(fig)


def test_function_of_no_arguments_draws_on_a_fresh_figure():
    calls = []

    def draw():
        calls.append(1)
        plt.plot([0, 1], [0, 1])

    f = rr.rtfplot(draw, render_width=2, render_height=1, render_dpi=100)
    assert calls == [1]
    assert (f.img_width, f.img_height) == (200, 100)
    rtf = rr.rtf_figures(rr.rtf_document(), [f]).to_rtf()
    assert "\\pngblip" in rtf


def test_object_with_save_is_asked_to_save_itself():
    # plotnine's ggplot.save(filename, width, height, dpi, units, verbose)
    class FakePlot:
        def save(self, filename, width, height, dpi, units, verbose):
            assert units == "in" and verbose is False
            fig = plt.figure(figsize=(width, height))
            fig.savefig(filename, dpi=dpi)
            plt.close(fig)

    f = rr.rtfplot(FakePlot(), render_width=1, render_height=1, render_dpi=72)
    assert (f.img_width, f.img_height) == (72, 72)


def test_render_arguments_are_refused_for_a_file(tmp_path):
    fig = _mpl_figure()
    path = tmp_path / "p.png"
    fig.savefig(path, dpi=100)
    plt.close(fig)
    assert rr.rtfplot(path).img_width == 300  # a PathLike is a file
    with pytest.raises(ValueError, match="a file already has a size"):
        rr.rtfplot(str(path), render_dpi=300)


@pytest.mark.parametrize("bad", [None, 3, ["a.png", "b.png"]])
def test_things_that_do_not_draw_are_refused(bad):
    with pytest.raises(ValueError, match="one file path, or one plot object"):
        rr.rtfplot(bad)


def test_bad_render_values_and_undrawable_objects():
    fig = _mpl_figure()
    with pytest.raises(ValueError, match="`render_dpi` must be a single positive number"):
        rr.rtfplot(fig, render_dpi=0)
    plt.close(fig)
    with pytest.raises(ValueError, match="Cannot draw a object"):
        rr.rtfplot(object())


def test_a_failed_draw_leaves_no_file(monkeypatch, tmp_path):
    made = []
    real = rr.figure.tempfile.mkstemp

    def spy(*a, **k):
        fd, p = real(*a, dir=tmp_path, **k)
        made.append(p)
        return fd, p

    monkeypatch.setattr(rr.figure.tempfile, "mkstemp", spy)

    def boom():
        raise RuntimeError("draw failed")

    with pytest.raises(RuntimeError, match="draw failed"):
        rr.rtfplot(boom)
    assert made and not os.path.exists(made[0])


def test_rtf_figures_draws_plot_objects_and_names_a_bad_item():
    fig = _mpl_figure()
    doc = rr.rtf_figures(rr.rtf_document(), [fig], width_twips=2880)
    assert doc._pages[0]["content"].display_twips()["w"] == 2880
    with pytest.raises(ValueError, match=r"figures\[1\]: A figure is one file path"):
        rr.rtf_figures(rr.rtf_document(), [fig, None])
    with pytest.raises(FileNotFoundError, match=r"figures\[0\]"):
        rr.rtf_figures(rr.rtf_document(), ["no-such-file.png"])
    plt.close(fig)
