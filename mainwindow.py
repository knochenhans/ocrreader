import os
from iso639 import Lang
from PySide6 import QtCore, QtGui, QtWidgets

from boxeditor import BoxEditor
from ocrengine import OCREngineManager, OCREngineTesseract
from project import Project
from propertyeditor import PropertyEditor


class PageData():
    def __init__(self, image_path: str) -> None:
        self.image_path = image_path


class StyledItemDelegate(QtWidgets.QStyledItemDelegate):
    def initStyleOption(self, option, index) -> None:
        super(StyledItemDelegate, self).initStyleOption(option, index)
        option.decorationPosition = QtWidgets.QStyleOptionViewItem.Top
        option.displayAlignment = QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom


class ItemImage(QtGui.QStandardItem):
    def __init__(self, image_name: str, page_data: PageData) -> None:
        super().__init__()

        self.setEditable(False)
        self.setText(image_name)

        image = QtGui.QImage(page_data.image_path).scaledToWidth(100, QtCore.Qt.SmoothTransformation)
        self.setData(image, QtCore.Qt.DecorationRole)

        # if page_data.image_path:
        #     image = QtGui.QImage(page_data.image_path).scaledToWidth(100, QtCore.Qt.SmoothTransformation)
        #     self.setData(image, QtCore.Qt.DecorationRole)
        #     self.setData(page_data, QtCore.Qt.UserRole)


class PagesListStore(QtGui.QStandardItemModel):

    def __init__(self, parent, list_of_images=[]) -> None:
        super().__init__(parent)
        if len(list_of_images):
            for path in list_of_images:
                self.__renderImage(path, self.__generateImageName(path))

    def addImage(self, page_data) -> None:
        image_name = self.__generateImageName(page_data.image_path)
        return self.__renderImage(image_name, page_data)

    def __renderImage(self, image_name, page_data) -> None:
        self.appendRow(ItemImage(image_name, page_data))

    # def __countEqualPathsStored(self, path):
    #     #iter = self.get_iter_first()
    #     counter = 0
    #     # while iter != None:
    #     #     page_data = self.get_value(iter, 2)
    #     #     image_path = page_data.image_path
    #     #     if image_path == path:
    #     #         counter += 1
    #     #     iter = self.iter_next(iter)
    #     return counter

    def __generateImageName(self, path) -> str:
        image_name = os.path.basename(path)
        # number_of_equal_paths = self.__countEqualPathsStored(path)
        # if number_of_equal_paths:
        #     image_name += ' (' + str(number_of_equal_paths + 1) + ')'
        return image_name

    def flags(self, index) -> QtCore.Qt.ItemFlags:
        default_flags = super().flags(index)

        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled

        return default_flags


class PagesIconView(QtWidgets.QListView):

    def __init__(self, parent) -> None:
        super().__init__(parent)
        model = PagesListStore(self)
        self.setModel(model)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)

        delegate = StyledItemDelegate(self)
        self.setItemDelegate(delegate)

        #model.appendRow(ItemImage('test', '/tmp/amiga/1_tmp.jpg'))
        # model.appendRow(ItemImage('test', '/tmp/amiga/2_tmp.jpg'))

    def getSelectedPageData(self):
        selected_items = self.selectedIndexes()
        if len(selected_items):
            return self.model().data(self.selectedIndexes()[0], QtCore.Qt.UserRole)
        return None

    def setDeleteCurrentPageFunction(self, function):
        self.delete_current_page_function = function

    def getNumberOfPages(self) -> int:
        return self.model().rowCount()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        # self.resize(1200, 800)
        self.showMaximized()
        self.setWindowTitle('PyOCR')
        self.show()

        toolbar = QtWidgets.QToolBar('Toolbar')
        toolbar.setIconSize(QtCore.QSize(32, 32))
        self.addToolBar(toolbar)

        self.setStatusBar(QtWidgets.QStatusBar(self))

        menu = self.menuBar()

        self.setup_actions()

        toolbar.addAction(self.open_project_action)

        file_menu = menu.addMenu('&File')
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        self.project = Project(language=Lang('deu'))

        self.engine_manager = OCREngineManager([OCREngineTesseract()])

        page_image_filename = '/mnt/Daten/Emulation/Amiga/Amiga Magazin/x-000.ppm'

        self.splitter_1 = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.page_icon_view = PagesIconView(self)

        page_data = PageData(page_image_filename)
        self.page_icon_view.model().addImage(page_data)

        self.splitter_1.addWidget(self.page_icon_view)

        self.splitter_2 = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.splitter_1.addWidget(self.splitter_2)

        self.property_editor = PropertyEditor(self, self.engine_manager, self.project)
        self.box_editor = BoxEditor(self, self.engine_manager, self.property_editor, self.project, page_image_filename)
        self.box_editor.property_editor = self.property_editor
        self.box_editor.setMinimumWidth(500)
        self.property_editor.box_editor = self.box_editor
        self.property_editor.setMinimumWidth(200)

        self.splitter_2.addWidget(self.box_editor)
        self.splitter_2.addWidget(self.property_editor)
        self.setCentralWidget(self.splitter_1)
        self.splitter_1.setSizes([1, 1])
        self.splitter_2.setSizes([1, 1])

    def setup_actions(self) -> None:
        self.exit_action = QtGui.QAction(QtGui.QIcon('resources/icons/close-line.png'), "&Exit", self)
        self.exit_action.setStatusTip('Exit OCR Reader')
        self.exit_action.triggered.connect(self.close)

        self.open_project_action = QtGui.QAction(QtGui.QIcon('resources/icons/folder-4-line.png'), "&Open Project", self)
        self.open_project_action.setStatusTip('Open Project')
        self.open_project_action.triggered.connect(self.open_project)

    def open_project(self) -> None:
        pass
