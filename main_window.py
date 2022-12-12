import ntpath
import os
import shutil
import tempfile
from pathlib import Path

from iso639 import Lang
from papersize import SIZES
from pdf2image import convert_from_path
from PIL import Image
from PySide6 import QtCore, QtGui, QtWidgets

from box_editor.box_data import BOX_DATA_TYPE
from box_editor.box_editor_view import BoxEditorView
from document_helper import DocumentHelper
from exporter import ExporterEPUB, ExporterManager, ExporterPlainText
from ocr_engine import OCREngineManager, OCREnginePytesseract, OCREngineTesserocr
from pages_icon_view import PagesIconView
from project import Page, Project
from property_editor import PropertyEditor


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        # self.resize(1200, 800)
        self.showMaximized()
        self.setWindowTitle('PyOCR')
        self.setWindowIcon(QtGui.QIcon('resources/icons/character-recognition-line.png'))
        self.show()

        self.last_project_filename = ''
        self.last_project_directory = ''

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
        toolbar.addAction(self.export_txt_action)
        toolbar.addAction(self.export_epub_action)
        toolbar.addAction(self.analyze_layout_action)
        toolbar.addAction(self.analyze_layout_and_recognize_action)

        file_menu: QtWidgets.QMenu = menu.addMenu(self.tr('&File', 'menu_file'))
        file_menu.addAction(self.load_image_action)
        file_menu.addAction(self.open_project_action)
        file_menu.addAction(self.save_project_action)
        file_menu.addAction(self.close_project_action)
        file_menu.addAction(self.export_action)
        file_menu.addAction(self.export_txt_action)
        file_menu.addAction(self.export_epub_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        self.setup_project()

        self.statusBar().showMessage(self.tr('OCR Reader loaded', 'status_loaded'))

        self.temp_dir = tempfile.TemporaryDirectory()

        self.exporter_manager = ExporterManager()
        self.exporter_manager.add_exporter('EPUB', ExporterEPUB(self))
        self.exporter_manager.add_exporter('PlainText', ExporterPlainText(self))

        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtGui.Qt.CursorShape.ArrowCursor))

    def __del__(self):
        self.temp_dir.cleanup()

    def setup_project(self, project=None) -> None:
        # self.engine_manager = OCREngineManager([OCREngineTesseract()])
        self.engine_manager = OCREngineManager([OCREngineTesserocr()])

        if project:
            self.project = project
        else:
            # Setup an empty default project
            system_lang = Lang(QtCore.QLocale().system().languageToCode(QtCore.QLocale().system().language()))
            self.project = Project(name=self.tr('New Project', 'new_project'), default_language=system_lang)

        self.property_editor = PropertyEditor(self, self.engine_manager, self.project)
        self.property_editor.setMinimumWidth(200)
        self.property_editor.project_widget.default_paper_size_combo.setCurrentText(SIZES[self.project.default_paper_size])
        self.property_editor.page_widget.paper_size_combo.setCurrentText(SIZES[self.project.default_paper_size])

        self.box_editor = BoxEditorView(self, self.engine_manager, self.property_editor, self.project)
        self.box_editor.property_editor = self.property_editor
        self.box_editor.setMinimumWidth(500)

        self.page_icon_view = PagesIconView(self, self.project)
        self.page_icon_view.selectionModel().currentChanged.connect(self.page_selected)

        self.splitter_2 = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter_2.addWidget(self.box_editor)
        self.splitter_2.addWidget(self.property_editor)
        self.splitter_2.setSizes([1, 1])

        self.splitter_1 = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter_1.addWidget(self.page_icon_view)
        self.splitter_1.addWidget(self.splitter_2)
        self.splitter_1.setSizes([1, 1])

        self.setCentralWidget(self.splitter_1)

        self.export_action.setDisabled(True)
        self.save_project_action.setDisabled(True)
        self.analyze_layout_action.setDisabled(True)
        self.analyze_layout_and_recognize_action.setDisabled(True)
        self.close_project_action.setDisabled(True)

    def setup_actions(self) -> None:
        self.exit_action = QtGui.QAction(QtGui.QIcon('resources/icons/close-circle-line.png'), self.tr('&Exit', 'action_exit'), self)
        self.exit_action.setStatusTip(self.tr('Exit OCR Reader', 'status_exit'))
        self.exit_action.triggered.connect(self.close)
        self.exit_action.setShortcut(QtGui.QKeySequence('Ctrl+q'))

        self.open_project_action = QtGui.QAction(QtGui.QIcon('resources/icons/folder-4-line.png'), self.tr('&Open Project', 'action_open_project'), self)
        self.open_project_action.setStatusTip(self.tr('Open Project', 'status_open_project'))
        self.open_project_action.triggered.connect(self.open_project)
        self.open_project_action.setShortcut(QtGui.QKeySequence('Ctrl+o'))

        self.export_action = QtGui.QAction(QtGui.QIcon('resources/icons/folder-transfer-line.png'), self.tr('&Export Project', 'action_export_project'), self)
        self.export_action.setStatusTip(self.tr('Export Project', 'status_export_project'))
        self.export_action.triggered.connect(self.export_project)
        self.export_action.setShortcut(QtGui.QKeySequence('Ctrl+e'))

        self.export_txt_action = QtGui.QAction(QtGui.QIcon('resources/icons/folder-transfer-line.png'), self.tr('&Export Project as Plain Text', 'action_export_project_txt'), self)
        self.export_txt_action.setStatusTip(self.tr('Export Project as Plain Text', 'action_export_project_txt'))
        self.export_txt_action.triggered.connect(self.export_plaintext)

        self.export_epub_action = QtGui.QAction(QtGui.QIcon('resources/icons/folder-transfer-line.png'), self.tr('&Export Project as EPUB', 'action_export_project_epub'), self)
        self.export_epub_action.setStatusTip(self.tr('Export Project as EPUB', 'action_export_project_epub'))
        self.export_epub_action.triggered.connect(self.export_epub)

        self.save_project_action = QtGui.QAction(QtGui.QIcon('resources/icons/save-line.png'), self.tr('&Save Project', 'action_save_project'), self)
        self.save_project_action.setStatusTip(self.tr('Save Project', 'status_save_project'))
        self.save_project_action.triggered.connect(self.save_project)
        self.save_project_action.setShortcut(QtGui.QKeySequence('Ctrl+s'))

        self.load_image_action = QtGui.QAction(QtGui.QIcon('resources/icons/image-line.png'), self.tr('&Load Image or PDF', 'action_load_image'), self)
        self.load_image_action.setStatusTip(self.tr('Load Image', 'status_load_image'))
        self.load_image_action.triggered.connect(self.load_image_dialog)
        self.load_image_action.setShortcut(QtGui.QKeySequence('Ctrl+i'))

        self.analyze_layout_action = QtGui.QAction(QtGui.QIcon('resources/icons/layout-line.png'), self.tr('&Analyze Layout', 'action_analyze_layout'), self)
        self.analyze_layout_action.setStatusTip(self.tr('Analyze Layout', 'status_analyze_layout'))
        self.analyze_layout_action.triggered.connect(self.analyze_layout)
        self.analyze_layout_action.setShortcut(QtGui.QKeySequence('Ctrl+Alt+a'))

        self.analyze_layout_and_recognize_action = QtGui.QAction(QtGui.QIcon('resources/icons/layout-fill.png'), self.tr('Analyze Layout and &Recognize', 'action_analyze_layout_and_recognize'), self)
        self.analyze_layout_and_recognize_action.setStatusTip(self.tr('Analyze Layout and Recognize', 'status_analyze_layout_and_recognize'))
        self.analyze_layout_and_recognize_action.triggered.connect(self.analyze_layout_and_recognize)
        self.analyze_layout_and_recognize_action.setShortcut(QtGui.QKeySequence('Ctrl+Alt+r'))

        self.close_project_action = QtGui.QAction(QtGui.QIcon('resources/icons/close-line.png'), self.tr('&Close project', 'action_close_project'), self)
        self.close_project_action.setStatusTip(self.tr('Close project', 'status_close_project'))
        self.close_project_action.triggered.connect(self.close_current_project)
        self.close_project_action.setShortcut(QtGui.QKeySequence('Ctrl+w'))

    def page_selected(self, index: QtCore.QModelIndex):
        if self.box_editor.current_page == index.data(QtCore.Qt.UserRole):
            return

        self.box_editor.load_page(index.data(QtCore.Qt.UserRole))
        self.project.current_page_idx = self.page_icon_view.currentIndex().row()
        self.box_editor.scene().update()
        self.box_editor.setFocus()

    def project_set_active(self):
        self.export_action.setEnabled(True)
        self.save_project_action.setEnabled(True)
        self.analyze_layout_action.setEnabled(True)
        self.analyze_layout_and_recognize_action.setEnabled(True)
        self.close_project_action.setEnabled(True)

    def load_image_dialog(self) -> None:
        filenames = QtWidgets.QFileDialog.getOpenFileNames(parent=self, caption=self.tr('Load Image or PDF', 'status_load_image'),
                                                           filter=self.tr('Image and PDF files (*.jpg *.jpeg *.png *.gif *.bmp *.ppm *.pdf)', 'filter_image_files'))

        pages = []

        for filename in filenames[0]:
            pages += self.load_image(filename)

        if filenames[1]:
            # Load first page
            self.box_editor.load_page(pages[0])

        self.project_set_active()

    def load_image(self, filename: str) -> list:
        pages = []
        if filename:
            image_filenames = []

            if os.path.splitext(filename)[1] == '.pdf':
                images = convert_from_path(filename, output_folder=self.temp_dir.name)

                for image in images:
                    image_png = Image.open(image.filename)
                    image_png_filename = os.path.dirname(os.path.abspath(image.filename)) + '/' + Path(image.filename).stem + '.png'
                    image_png.save(image_png_filename)
                    os.remove(image.filename)
                    image_filenames.append(image_png_filename)

            else:
                image_filenames.append(filename)

            for image_filename in image_filenames:
                page = Page(image_filename, ntpath.basename(filename), self.project.default_paper_size)
                self.project.add_page(page)
                self.page_icon_view.load_page(page)
                pages.append(page)

                self.statusBar().showMessage(self.tr('Image loaded', 'status_image_loaded') + ': ' + page.image_path)

        if pages:
            self.project_set_active()

        return pages

    def open_project(self) -> None:
        project_filename = QtWidgets.QFileDialog.getOpenFileName(parent=self, caption=self.tr('Open project file', 'dialog_open_project_file'),
                                                                 filter=self.tr('OCR Reader project (*.orp)', 'filter_ocr_reader_project'))[0]

        if project_filename:
            self.close_project()

            project_file = QtCore.QFile(project_filename)
            project_file.open(QtCore.QIODevice.ReadOnly)
            input = QtCore.QDataStream(project_file)

            # Read project
            project = Project()
            try:
                project.read(input)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, 'Error', str(e))
                project_file.close()

                self.setup_project()
            else:
                project_file.close()

                self.setup_project(project)

                # Reconstruct pages and page elements from project file
                for page in project.pages:
                    self.page_icon_view.load_page(page)

                # index = self.page_icon_view.model().index(self.project.current_page_idx, 0)

                # self.page_icon_view.setCurrentIndex(index)
                # self.page_selected(index)

                self.box_editor.load_page(project.pages[project.current_page_idx])

                self.last_project_filename = project_filename

                self.project_set_active()
                self.statusBar().showMessage(self.tr('Project opened', 'status_project_opened') + ': ' + project_file.fileName())

    def save_project(self) -> None:
        project_filename = self.last_project_filename

        if not project_filename:
            project_filename = QtWidgets.QFileDialog.getSaveFileName(parent=self, caption=self.tr('Save project', 'dialog_save_project'),
                                                                     filter=self.tr('OCR Reader project (*.orp)', 'filter_ocr_reader_project'))[0]

        if project_filename:
            self.save_project_file(project_filename)

    def save_project_as(self) -> None:
        project_file = QtWidgets.QFileDialog.getSaveFileName(parent=self, caption=self.tr('Save project as', 'dialog_save_project'),
                                                             filter=self.tr('OCR Reader project (*.orp)', 'filter_ocr_reader_project'))[0]

        if project_file:
            self.save_project_file(project_file)

    def save_project_file(self, filename) -> None:
        extension = os.path.splitext(filename)[1]

        if extension != '.orp':
            filename += '.orp'

        save_folder = os.path.dirname(os.path.abspath(filename))
        data_folder = save_folder + '/' + Path(ntpath.basename(filename)).stem

        for page in self.project.pages:
            if page.image_path.startswith(self.temp_dir.name):
                if not os.path.exists(data_folder):
                    os.makedirs(data_folder, exist_ok=True)

                new_path = data_folder + '/' + ntpath.basename(page.image_path)

                shutil.move(page.image_path, new_path)
                page.image_path = data_folder + '/' + ntpath.basename(page.image_path)

        file = QtCore.QFile(filename)
        file.open(QtCore.QIODevice.WriteOnly)
        output = QtCore.QDataStream(file)
        self.project.write(output)
        file.close()

        self.statusBar().showMessage(self.tr('Save project', 'dialog_save_project') + ': ' + file.fileName())
        self.last_project_filename = filename
        self.last_project_directory = os.path.dirname(os.path.abspath(self.last_project_filename))

    def close_project(self) -> None:
        self.page_icon_view.close()
        self.box_editor.close()
        self.property_editor.close()

    def close_current_project(self) -> None:
        self.close_project()
        self.setup_project()

    def export_project(self) -> None:
        self.run_exporter('PlainText')

    def run_exporter(self, id):
        exporter = self.exporter_manager.get_exporter(id)

        # Exclude boxes in header or footer area
        self.box_editor.scene().disable_boxes_in_header_footer()

        if exporter.open(self.temp_dir, self.project.name):
            for p, page in enumerate(self.project.pages):
                if p > 0:
                    exporter.new_page()
                for box_data in page.box_datas:
                    if box_data.export_enabled:
                        exporter.write_box(box_data, page, p)

            exporter.close()

            self.statusBar().showMessage(self.tr('Project exported successfully', 'status_exported'))
        else:
            self.statusBar().showMessage(self.tr('Project export aborted', 'status_export_aborted'))

    def export_plaintext(self):
        self.run_exporter('PlainText')

    def export_epub(self):
        self.run_exporter('EPUB')

    # def export_odt(self):
    #     # text = QtGui.QTextDocument()
    #     # cursor = QtGui.QTextCursor(text)

    #     boxes = self.scene().selectedItems()

    #     textdoc = OpenDocumentText()

    #     for b, box in enumerate(boxes):
    #         # cursor.insertHtml(box.properties.ocr_result_block.get_text().toHtml())

    #         # if b < (len(boxes) - 1):
    #         # cursor.insertText('\n\n')

    #         p = P(text=box.properties.ocr_result_block.get_text(self.project.default_paper_size).toPlainText())
    #         textdoc.text.addElement(p)

    #     textdoc.save('/tmp/headers.odt')

    #     # print(text.toPlainText())

    def analyze_layout(self) -> None:
        self.box_editor.scene().clear_boxes()
        self.box_editor.analyze_layout()

    def analyze_layout_and_recognize(self) -> None:
        self.box_editor.scene().clear_boxes()
        boxes = self.box_editor.analyze_layout()

        # for box in boxes:
        #     self.box_editor.scene().recognize_box(box)
        #     QtCore.QCoreApplication.instance().processEvents()
        #     self.box_editor.scene().update()
        #     box.update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            # filenames = []

            for url in event.mimeData().urls():
                # filenames.append(url.toLocalFile())
                self.load_image(url.toLocalFile())
