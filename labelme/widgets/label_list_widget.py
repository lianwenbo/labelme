from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtGui import QPalette
from qtpy.QtWidgets import QStyle


#: 「上一次选中的标注」标记。用自定义 role 存，不碰 item 的文本和选中状态——
#: 选中状态会被 clearSelection 抹掉，而这个标记要一直留着。
LAST_SELECTED_ROLE = Qt.UserRole + 1

LAST_SELECTED_BG = QtGui.QColor("#fff2cc")
LAST_SELECTED_ACCENT = QtGui.QColor("#e08a00")
LAST_SELECTED_TEXT = QtGui.QColor("#3a2c00")
LAST_SELECTED_BAR_WIDTH = 3


# https://stackoverflow.com/a/2039745/4158863
class HTMLDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super(HTMLDelegate, self).__init__()
        self.doc = QtGui.QTextDocument(self)

    def paint(self, painter, option, index):
        painter.save()

        options = QtWidgets.QStyleOptionViewItem(option)

        self.initStyleOption(options, index)

        is_last_selected = bool(index.data(LAST_SELECTED_ROLE))
        is_selected = bool(option.state & QStyle.State_Selected)
        # 已选中的行由样式自己画高亮底，再叠一层淡黄会脏；没选中时才铺底色
        if is_last_selected and not is_selected:
            options.backgroundBrush = QtGui.QBrush(LAST_SELECTED_BG)
            options.font.setBold(True)

        self.doc.setDefaultFont(options.font)
        self.doc.setHtml(options.text)
        options.text = ""

        style = (
            QtWidgets.QApplication.style()
            if options.widget is None
            else options.widget.style()
        )
        style.drawControl(QStyle.CE_ItemViewItem, options, painter)

        if is_last_selected:
            # 左侧竖条画在最上层：选中时底色被高亮盖掉，竖条仍然能指出「上一次是这条」
            painter.fillRect(
                QtCore.QRect(
                    option.rect.left(),
                    option.rect.top(),
                    LAST_SELECTED_BAR_WIDTH,
                    option.rect.height(),
                ),
                LAST_SELECTED_ACCENT,
            )

        ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()

        if is_selected:
            ctx.palette.setColor(
                QPalette.Text,
                option.palette.color(QPalette.Active, QPalette.HighlightedText),
            )
        elif is_last_selected:
            ctx.palette.setColor(QPalette.Text, LAST_SELECTED_TEXT)
        else:
            ctx.palette.setColor(
                QPalette.Text,
                option.palette.color(QPalette.Active, QPalette.Text),
            )

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText, options)

        if index.column() != 0:
            textRect.adjust(5, 0, 0, 0)

        thefuckyourshitup_constant = 4
        margin = (option.rect.height() - options.fontMetrics.height()) // 2
        margin = margin - thefuckyourshitup_constant
        textRect.setTop(textRect.top() + margin)

        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        self.doc.documentLayout().draw(painter, ctx)

        painter.restore()

    def sizeHint(self, option, index):
        thefuckyourshitup_constant = 4
        return QtCore.QSize(
            int(self.doc.idealWidth()),
            int(self.doc.size().height() - thefuckyourshitup_constant),
        )


class LabelListWidgetItem(QtGui.QStandardItem):
    def __init__(self, text=None, shape=None):
        super(LabelListWidgetItem, self).__init__()
        self.setText(text or "")
        self.setShape(shape)

        self.setCheckable(True)
        self.setCheckState(Qt.Checked)
        self.setEditable(False)
        self.setTextAlignment(Qt.AlignBottom)

    def clone(self):
        return LabelListWidgetItem(self.text(), self.shape())

    def setShape(self, shape):
        self.setData(shape, Qt.UserRole)

    def shape(self):
        return self.data(Qt.UserRole)

    def setLastSelected(self, value):
        """标记 / 取消「上一次选中的标注」。

        和 Qt 自己的选中状态是两回事：选中状态会被 clearSelection 清掉，
        这个标记要一直留到下一次选中别的标注为止。
        """
        value = bool(value)
        current = self.data(LAST_SELECTED_ROLE)
        # 值没变就不写，避免每次改选都刷一轮 dataChanged
        if current is not None and bool(current) == value:
            return
        self.setData(value, LAST_SELECTED_ROLE)

    def isLastSelected(self):
        return bool(self.data(LAST_SELECTED_ROLE))

    def __hash__(self):
        return id(self)

    def __repr__(self):
        return '{}("{}")'.format(self.__class__.__name__, self.text())


class StandardItemModel(QtGui.QStandardItemModel):
    itemDropped = QtCore.Signal()

    def removeRows(self, *args, **kwargs):
        ret = super().removeRows(*args, **kwargs)
        self.itemDropped.emit()
        return ret


class LabelListWidget(QtWidgets.QListView):
    itemDoubleClicked = QtCore.Signal(LabelListWidgetItem)
    itemSelectionChanged = QtCore.Signal(list, list)

    def __init__(self):
        super(LabelListWidget, self).__init__()
        self._selectedItems = []

        self.setWindowFlags(Qt.Window)
        self.setModel(StandardItemModel())
        self.model().setItemPrototype(LabelListWidgetItem())
        self.setItemDelegate(HTMLDelegate())
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

        self.doubleClicked.connect(self.itemDoubleClickedEvent)
        self.selectionModel().selectionChanged.connect(self.itemSelectionChangedEvent)

    def __len__(self):
        return self.model().rowCount()

    def __getitem__(self, i):
        return self.model().item(i)

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    @property
    def itemDropped(self):
        return self.model().itemDropped

    @property
    def itemChanged(self):
        return self.model().itemChanged

    def itemSelectionChangedEvent(self, selected, deselected):
        selected = [self.model().itemFromIndex(i) for i in selected.indexes()]
        deselected = [self.model().itemFromIndex(i) for i in deselected.indexes()]
        self.itemSelectionChanged.emit(selected, deselected)

    def itemDoubleClickedEvent(self, index):
        self.itemDoubleClicked.emit(self.model().itemFromIndex(index))

    def selectedItems(self):
        return [self.model().itemFromIndex(i) for i in self.selectedIndexes()]

    def scrollToItem(self, item):
        self.scrollTo(self.model().indexFromItem(item))

    def addItem(self, item):
        if not isinstance(item, LabelListWidgetItem):
            raise TypeError("item must be LabelListWidgetItem")
        self.model().setItem(self.model().rowCount(), 0, item)
        item.setSizeHint(self.itemDelegate().sizeHint(None, None))

    def removeItem(self, item):
        index = self.model().indexFromItem(item)
        self.model().removeRows(index.row(), 1)

    def selectItem(self, item):
        index = self.model().indexFromItem(item)
        self.selectionModel().select(index, QtCore.QItemSelectionModel.Select)

    def findItemByShape(self, shape):
        for row in range(self.model().rowCount()):
            item = self.model().item(row, 0)
            if item.shape() == shape:
                return item
        raise ValueError("cannot find shape: {}".format(shape))

    def clear(self):
        self.model().clear()
