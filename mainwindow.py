import ntpath
import os

from iso639 import Lang
from papersize import SIZES
from PySide6 import QtCore, QtGui, QtWidgets

from boxeditor import BoxEditor
from ocrengine import OCREngineManager, OCREngineTesseract
from project import Page, Project
from propertyeditor import PropertyEditor


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

        # if page_data.image_path:
        #     image = QtGui.QImage(page_data.image_path).scaledToWidth(100, QtCore.Qt.SmoothTransformation)
        #     self.setData(image, QtCore.Qt.DecorationRole)
        self.setData(page, QtCore.Qt.UserRole)


class PagesListStore(QtGui.QStandardItemModel):

    def __init__(self, parent) -> None:
        super().__init__(parent)

    # def __init__(self, parent, list_of_images=[]) -> None:
    #     super().__init__(parent)
    #     if len(list_of_images):
    #         for path in list_of_images:
    #             self.render_image(path, self.generate_image_name(path))

    def add_page(self, page: Page) -> None:
        self.appendRow(ItemImage(page))
        # image_name = self.generate_image_name(page.image_path)
        # return self.render_image(image_name, page)

    # def render_image(self, image_name, page_data) -> None:
    #     self.appendRow(ItemImage(image_name, page_data))

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

    # def generate_image_name(self, path) -> str:
    #     image_name = os.path.basename(path)
    #     # number_of_equal_paths = self.__countEqualPathsStored(path)
    #     # if number_of_equal_paths:
    #     #     image_name += ' (' + str(number_of_equal_paths + 1) + ')'
    #     return image_name

    def flags(self, index) -> QtCore.Qt.ItemFlags:
        default_flags = super().flags(index)

        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled

        return default_flags


class PagesIconView(QtWidgets.QListView):

    def __init__(self, parent, project) -> None:
        super().__init__(parent)
        model = PagesListStore(self)
        self.setModel(model)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)

        delegate = StyledItemDelegate(self)
        self.setItemDelegate(delegate)

    def load_page(self, page: Page):
        self.model().add_page(page)

    # def get_selected_page(self):
    #     selected_items = self.selectedIndexes()
    #     if len(selected_items):
    #         return self.model().data(self.selectedIndexes()[0], QtCore.Qt.UserRole)
    #     return None

    # def setDeleteCurrentPageFunction(self, function):
    #     self.delete_current_page_function = function

    # def getNumberOfPages(self) -> int:
    #     return self.model().rowCount()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        # self.resize(1200, 800)
        self.showMaximized()
        self.setWindowTitle('PyOCR')
        self.setWindowIcon(QtGui.QIcon('resources/icons/character-recognition-line.png'))
        self.show()

        toolbar = QtWidgets.QToolBar('Toolbar')
        toolbar.setIconSize(QtCore.QSize(32, 32))
        self.addToolBar(toolbar)

        self.setStatusBar(QtWidgets.QStatusBar(self))

        self.setAcceptDrops(True)

        menu = self.menuBar()

        self.setup_actions()

        toolbar.addAction(self.load_image_action)
        toolbar.addAction(self.open_project_action)
        toolbar.addAction(self.save_project_action)
        toolbar.addAction(self.export_action)

        file_menu = menu.addMenu('&File')
        file_menu.addAction(self.load_image_action)
        file_menu.addAction(self.save_project_action)
        file_menu.addAction(self.export_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        # Create test project

        # page = Page('/mnt/Daten/Emulation/Amiga/Amiga Magazin/x-000.ppm', '1', SIZES['a4'])

        self.project = Project(default_language=Lang('deu'))
        # self.project.load_page('/mnt/Daten/Emulation/Amiga/Amiga Magazin/x-000.ppm', SIZES['a4'])
        # self.project.load_page('/mnt/Daten/Emulation/Amiga/Amiga Magazin/x-000.ppm', SIZES['a4'])

        self.engine_manager = OCREngineManager([OCREngineTesseract()])

        self.splitter_1 = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.page_icon_view = PagesIconView(self, self.project)
        self.page_icon_view.clicked.connect(self.page_selected)

        self.splitter_1.addWidget(self.page_icon_view)

        self.splitter_2 = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.splitter_1.addWidget(self.splitter_2)

        self.property_editor = PropertyEditor(self, self.engine_manager, self.project)
        self.box_editor = BoxEditor(self, self.engine_manager, self.property_editor, self.project)
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
        self.exit_action = QtGui.QAction(QtGui.QIcon('resources/icons/close-line.png'), '&Exit', self)
        self.exit_action.setStatusTip('Exit OCR Reader')
        self.exit_action.triggered.connect(self.close)
        self.exit_action.setShortcut(QtGui.QKeySequence('Ctrl+q'))

        self.open_project_action = QtGui.QAction(QtGui.QIcon('resources/icons/folder-4-line.png'), '&Open Project', self)
        self.open_project_action.setStatusTip('Open Project')
        self.open_project_action.triggered.connect(self.open_project)
        self.open_project_action.setShortcut(QtGui.QKeySequence('Ctrl+o'))

        self.export_action = QtGui.QAction(QtGui.QIcon('resources/icons/folder-transfer-line.png'), '&Export Project', self)
        self.export_action.setStatusTip('Export Project')
        self.export_action.triggered.connect(self.export_project)
        self.export_action.setShortcut(QtGui.QKeySequence('Ctrl+e'))

        self.save_project_action = QtGui.QAction(QtGui.QIcon('resources/icons/save-line.png'), '&Save Project', self)
        self.save_project_action.setStatusTip('Save Project')
        self.save_project_action.triggered.connect(self.save_project)
        self.save_project_action.setShortcut(QtGui.QKeySequence('Ctrl+s'))

        self.load_image_action = QtGui.QAction(QtGui.QIcon('resources/icons/image-line.png'), '&Load Image', self)
        self.load_image_action.setStatusTip('Load Image')
        self.load_image_action.triggered.connect(self.load_image_dialog)
        self.load_image_action.setShortcut(QtGui.QKeySequence('Ctrl+i'))

    def page_selected(self, index: QtCore.QModelIndex):
        if self.box_editor.current_page != index.data(QtCore.Qt.UserRole):
            self.box_editor.load_page(index.data(QtCore.Qt.UserRole))

    def load_image_dialog(self) -> None:
        filenames = QtWidgets.QFileDialog.getOpenFileNames(parent=self, caption='Open images', filter='Image files (*.jpg *.png *.gif *.bmp *.ppm)')

        pages = []

        for filename in filenames[0]:
            pages.append(self.load_image(filename))

        # Load first page
        self.box_editor.load_page(pages[0])

    def load_image(self, filename: str) -> Page | None:
        if filename:
            page = Page(filename, ntpath.basename(filename), self.project.default_paper_size)
            self.project.add_page(page)
            self.page_icon_view.load_page(page)
            return page

    def open_project(self) -> None:
        file = QtCore.QFile('/tmp/file.dat')
        file.open(QtCore.QIODevice.ReadOnly)
        input = QtCore.QDataStream(file)

        project = Project()
        project.read(input)

        file.close()

    def save_project(self) -> None:
        file = QtCore.QFile('/tmp/file.dat')
        file.open(QtCore.QIODevice.WriteOnly)
        output = QtCore.QDataStream(file)
        self.project.write(output)
        file.close()

    def export_project(self) -> None:
        self.box_editor.export_odt()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            # filenames = []

            for url in event.mimeData().urls():
                # filenames.append(url.toLocalFile())
                self.load_image(url.toLocalFile())
