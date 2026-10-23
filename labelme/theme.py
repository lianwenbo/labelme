# -*- encoding: utf-8 -*-
"""界面配色。

为什么要显式指定配色：labelme 用的是 Qt 的原生样式，macOS 上就是
``macintosh`` 样式。系统切到深色模式后，Qt 从平台主题取到的是一套自相矛盾的
调色板——实测 ``ButtonText`` 是纯黑 ``#000000``，而 ``Button`` 是深灰
``#323232``，工具栏的文字和图标几乎看不见；同时原生样式只把一部分控件画成
深色，最终是「浅色工具栏 + 深色侧边栏」的混合外观。

所以这里改成显式指定 ``Fusion`` 样式 + 一套完整调色板：不依赖系统主题，
界面在任何机器上都是同一个样子。默认取浅色——标注是长时间对着扫描图做精细
操作，浅色中性背景更省眼睛，也便于看清标注本身的颜色。

``system`` 保留原行为（完全交给 Qt 和系统），需要时可以改回来。
"""

from qtpy import QtGui

from labelme.logger import logger

# 浅色配色。数值取自实测效果，不是随手挑的：
# Window 略灰于 Base，列表和画布才能和侧边栏底色分开；
# Highlight 用低饱和蓝，避免和地图上的红/绿标注撞色。
LIGHT = {
    "Window": "#f0f0f0",
    "WindowText": "#202020",
    "Base": "#ffffff",
    "AlternateBase": "#f5f5f5",
    "Text": "#202020",
    "Button": "#e8e8e8",
    "ButtonText": "#202020",
    "BrightText": "#d64541",
    "Highlight": "#3f638b",
    "HighlightedText": "#ffffff",
    "ToolTipBase": "#ffffdc",
    "ToolTipText": "#202020",
    "PlaceholderText": "#808080",
    "Link": "#0b66c3",
    # 立体边框用的几个过渡色，不设的话 Fusion 会自己推算，深浅不统一
    "Light": "#ffffff",
    "Midlight": "#f7f7f7",
    "Mid": "#dcdcdc",
    "Dark": "#c0c0c0",
    "Shadow": "#a0a0a0",
    "DisabledText": "#9a9a9a",
}

PALETTES = {"light": LIGHT}

#: 不做任何改动、完全跟随系统主题的取值
SYSTEM_ALIASES = ("system", "auto", "default")


def _build_palette(spec):
    palette = QtGui.QPalette()
    for role_name, color in spec.items():
        if role_name == "DisabledText":
            continue
        role = getattr(QtGui.QPalette, role_name, None)
        if role is None:
            # PlaceholderText 是 Qt 5.12 才有的，老版本直接跳过
            continue
        palette.setColor(role, QtGui.QColor(color))

    disabled = QtGui.QColor(spec["DisabledText"])
    for role_name in ("Text", "WindowText", "ButtonText"):
        role = getattr(QtGui.QPalette, role_name, None)
        if role is not None:
            palette.setColor(QtGui.QPalette.Disabled, role, disabled)
    return palette


def apply_theme(app, name):
    """按 ``name`` 给 QApplication 设置样式与调色板。

    必须在创建任何窗口之前调用——``setPalette`` 之后新建的控件才会拿到新配色。
    """
    if not name:
        name = "light"
    name = str(name).strip().lower()

    if name in SYSTEM_ALIASES:
        return False

    spec = PALETTES.get(name)
    if spec is None:
        logger.warning(
            "未知的 appearance.theme 取值 {!r}，可选 {} 或 {}，已按 light 处理".format(
                name, "/".join(PALETTES), "/".join(SYSTEM_ALIASES)
            )
        )
        spec = LIGHT

    app.setStyle("Fusion")
    app.setPalette(_build_palette(spec))
    return True
