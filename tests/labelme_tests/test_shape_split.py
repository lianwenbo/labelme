# -*- encoding: utf-8 -*-

import pytest
from qtpy import QtCore

from labelme.shape import Shape


def _linestrip(points, shape_type="linestrip"):
    shape = Shape(shape_type=shape_type)
    for x, y in points:
        shape.addPoint(QtCore.QPointF(x, y))
    return shape


@pytest.mark.parametrize(
    "click, expect_index, expect_point",
    [
        # 点在线段右侧，投影回线段上
        ((140, 50), 2, (100, 50)),
        # 靠近第一段
        ((50, 3), 1, (50, 0)),
        # 点在很远的地方，夹到最后一个端点
        ((900, 900), 3, (200, 100)),
    ],
)
def test_splitPoint_projects_onto_nearest_segment(click, expect_index, expect_point):
    shape = _linestrip([(0, 0), (100, 0), (100, 100), (200, 100)])

    index, point = shape.splitPoint(QtCore.QPointF(*click))

    assert index == expect_index
    assert point.x() == pytest.approx(expect_point[0])
    assert point.y() == pytest.approx(expect_point[1])


def test_splitPoint_ignores_wraparound_edge():
    """两点 line 只有一段，不能被当成回绕边而返回 0。

    nearestEdge() 会返回 0（points[-1] -> points[0]，方向相反），
    照着它切会得到 [P, p0, p1] 这种错误结果，所以分割单独算。
    """
    shape = _linestrip([(0, 0), (100, 0)], shape_type="line")
    shape.close()

    index, point = shape.splitPoint(QtCore.QPointF(30, 20))

    assert index == 1
    assert point.x() == pytest.approx(30)
    assert point.y() == pytest.approx(0)


def test_splitPoint_requires_two_points():
    shape = _linestrip([(0, 0)])

    assert shape.splitPoint(QtCore.QPointF(1, 1)) == (None, None)
