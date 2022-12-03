from PySide6 import QtGui, QtCore, QtWidgets
from project import Page, Project


class StyledItemDelegate(QtWidgets.QStyledItemDelegate):
    def initStyleOption(self, option, index) -> None:
        super(StyledItemDelegate, self).initStyleOption(option, index)
        option.decorationPosition = QtWidgets.QStyleOptionViewItem.Top
        option.displayAlignment = QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom


class ItemImage(QtGui.QStandardItem):
    def __init__(self, page: Page) -> None:
        super().__init__()

        self.setEditable(False)
        self.setText(page.name)

        image = QtGui.QImage(page.image_path).scaledToWidth(100, QtCore.Qt.SmoothTransformation)
        self.setData(image, QtCore.Qt.DecorationRole)
        self.setData(page, QtCore.Qt.UserRole)


class PagesListStore(QtGui.QStandardItemModel):
    def __init__(self, parent) -> None:
        super().__init__(parent)

    def add_page(self, page: Page) -> None:
        self.appendRow(ItemImage(page))

    def flags(self, index) -> QtCore.Qt.ItemFlags:
        default_flags = super().flags(index)

        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled

        return default_flags


class PagesIconView(QtWidgets.QListView):
    def __init__(self, parent, project: Project) -> None:
        super().__init__(parent)
        model = PagesListStore(self)
        self.setModel(model)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.setTextElideMode(QtCore.Qt.TextElideMode.ElideMiddle)
        self.setWordWrap(True)

        delegate = StyledItemDelegate(self)
        self.setItemDelegate(delegate)

    def load_page(self, page: Page):
        self.model().add_page(page)

    def cleanup(self) -> None:
        self.model().removeRows(0, self.model().rowCount())
