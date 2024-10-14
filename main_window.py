import ntpath
import os
import shutil
import tempfile
from pathlib import Path

import darkdetect
from iso639 import Lang  # type: ignore
from papersize import SIZES  # type: ignore
from pdf2image import convert_from_path  # type: ignore
from PIL import Image
from PySide6 import QtCore, QtGui, QtWidgets

from box_editor.box_data import BOX_DATA_TYPE
from box_editor.box_editor_view import BoxEditorView
from exporter import ExporterEPUB, ExporterManager, ExporterODT, ExporterPlainText
from ocr_engine.ocr_engine import OCREngineManager
from ocr_engine.ocr_engine_tesserocr import OCREngineTesserocr
from pages_icon_view import PagesIconView
from preferences import Preferences
from project import Page, Project
from property_editor import PropertyEditor


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        app_name = "OCR Reader"

        QtCore.QCoreApplication.setOrganizationName(app_name)
        QtCore.QCoreApplication.setOrganizationDomain(app_name)
        QtCore.QCoreApplication.setApplicationName(app_name)

        self.theme_folder = "light-theme"

        if darkdetect.isLight():
            self.theme_folder = "dark-theme"

        # self.restoreState(self.settings.value('windowState'))
        self.setWindowTitle(app_name)
        self.setWindowIcon(
            QtGui.QIcon(
                f"resources/icons/{self.theme_folder}/character-recognition-line.png"
            )
        )
        self.show()

        self.last_project_filename = ""
        self.last_project_directory = ""

        self.toolbar = QtWidgets.QToolBar("Toolbar")
        self.toolbar.setIconSize(QtCore.QSize(32, 32))
        self.addToolBar(self.toolbar)

        self.setStatusBar(QtWidgets.QStatusBar(self))

        self.setAcceptDrops(True)

        menu = self.menuBar()

        self.undo_stack = QtGui.QUndoStack(self)

        self.file_menu: QtWidgets.QMenu = menu.addMenu(
            QtCore.QCoreApplication.translate("menu_file", "&File")
        )
        self.edit_menu: QtWidgets.QMenu = menu.addMenu(
            QtCore.QCoreApplication.translate("menu_edit", "&Edit")
        )

        self.page_icon_view_context_menu = QtWidgets.QMenu(self)

        self.setup_actions()
        self.setup_toolbar()
        self.setup_menus()

        self.load_settings()

        self.setup_project()

        self.statusBar().showMessage(
            QtCore.QCoreApplication.translate("status_loaded", "OCR Reader loaded")
        )

        self.temp_dir = tempfile.TemporaryDirectory()

        self.exporter_manager = ExporterManager()
        self.exporter_manager.add_exporter("EPUB", ExporterEPUB(self))
        self.exporter_manager.add_exporter("PlainText", ExporterPlainText(self))
        self.exporter_manager.add_exporter("ODT", ExporterODT(self))

        from recent_files_manager import RecentFilesManager
        self.recent_files_manager = RecentFilesManager(self)

    def __del__(self):
        self.temp_dir.cleanup()

    def setup_project(self, project=None) -> None:
        # self.engine_manager = OCREngineManager([OCREngineTesseract()])
        self.engine_manager = OCREngineManager([OCREngineTesserocr()])

        if project:
            self.project = project
        else:
            # Setup an empty default project
            system_lang = Lang(
                QtCore.QLocale()
                .system()
                .languageToCode(QtCore.QLocale().system().language())
            )
            self.project = Project(
                name=QtCore.QCoreApplication.translate("new_project", "New Project"),
                default_language=system_lang,
            )

        self.property_editor = PropertyEditor(self, self.engine_manager, self.project)
        self.property_editor.setMinimumWidth(200)
        self.property_editor.project_widget.default_paper_size_combo.setCurrentText(
            SIZES[self.project.default_paper_size]
        )
        self.property_editor.page_widget.paper_size_combo.setCurrentText(
            SIZES[self.project.default_paper_size]
        )

        self.box_editor = BoxEditorView(
            self,
            self.undo_stack,
            self.engine_manager,
            self.property_editor,
            self.project,
        )
        self.box_editor.property_editor = self.property_editor
        self.box_editor.setMinimumWidth(500)

        self.page_icon_view = PagesIconView(self, self.project)
        self.page_icon_view.selectionModel().currentChanged.connect(self.page_selected)
        self.page_icon_view.customContextMenuRequested.connect(
            self.on_page_icon_view_context_menu
        )

        self.splitter_2 = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.splitter_2.addWidget(self.box_editor)
        self.splitter_2.addWidget(self.property_editor)
        self.splitter_2.setSizes([1, 1])

        self.splitter_1 = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
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
        self.exit_action = QtGui.QAction(
            QtGui.QIcon(f"resources/icons/{self.theme_folder}/close-circle-line.png"),
            QtCore.QCoreApplication.translate("action_exit", "&Exit"),
            self,
        )
        self.exit_action.setStatusTip(
            QtCore.QCoreApplication.translate("status_exit", "Exit OCR Reader")
        )
        self.exit_action.triggered.connect(self.close)
        self.exit_action.setShortcut(QtGui.QKeySequence("Ctrl+q"))

        self.open_project_action = QtGui.QAction(
            QtGui.QIcon(f"resources/icons/{self.theme_folder}/folder-4-line.png"),
            QtCore.QCoreApplication.translate("action_open_project", "&Open Project"),
            self,
        )
        self.open_project_action.setStatusTip(
            QtCore.QCoreApplication.translate("status_open_project", "Open Project")
        )
        self.open_project_action.triggered.connect(self.open_project)
        self.open_project_action.setShortcut(QtGui.QKeySequence("Ctrl+o"))

        self.export_action = QtGui.QAction(
            QtGui.QIcon(
                f"resources/icons/{self.theme_folder}/folder-transfer-line.png"
            ),
            QtCore.QCoreApplication.translate(
                "action_export_project", "&Export Project"
            ),
            self,
        )
        self.export_action.setStatusTip(
            QtCore.QCoreApplication.translate("status_export_project", "Export Project")
        )
        self.export_action.triggered.connect(self.export_project)
        self.export_action.setShortcut(QtGui.QKeySequence("Ctrl+e"))

        self.export_txt_action = QtGui.QAction(
            QtGui.QIcon(
                f"resources/icons/{self.theme_folder}/folder-transfer-line.png"
            ),
            QtCore.QCoreApplication.translate(
                "action_export_project_txt", "&Export Project as Plain Text"
            ),
            self,
        )
        self.export_txt_action.setStatusTip(
            QtCore.QCoreApplication.translate(
                "action_export_project_txt", "Export Project as Plain Text"
            )
        )
        self.export_txt_action.triggered.connect(self.export_plaintext)

        self.export_epub_action = QtGui.QAction(
            QtGui.QIcon(
                f"resources/icons/{self.theme_folder}/folder-transfer-line.png"
            ),
            QtCore.QCoreApplication.translate(
                "action_export_project_epub", "&Export Project as EPUB"
            ),
            self,
        )
        self.export_epub_action.setStatusTip(
            QtCore.QCoreApplication.translate(
                "action_export_project_epub", "Export Project as EPUB"
            )
        )
        self.export_epub_action.triggered.connect(self.export_epub)

        self.export_odt_action = QtGui.QAction(
            QtGui.QIcon(
                f"resources/icons/{self.theme_folder}/folder-transfer-line.png"
            ),
            QtCore.QCoreApplication.translate(
                "action_export_project_odt", "&Export Project as ODT"
            ),
            self,
        )
        self.export_odt_action.setStatusTip(
            QtCore.QCoreApplication.translate(
                "action_export_project_odt", "Export Project as ODT"
            )
        )
        self.export_odt_action.triggered.connect(self.export_odt)

        self.save_project_action = QtGui.QAction(
            QtGui.QIcon(f"resources/icons/{self.theme_folder}/save-line.png"),
            QtCore.QCoreApplication.translate("action_save_project", "&Save Project"),
            self,
        )
        self.save_project_action.setStatusTip(
            QtCore.QCoreApplication.translate("status_save_project", "Save Project")
        )
        self.save_project_action.triggered.connect(self.save_project)
        self.save_project_action.setShortcut(QtGui.QKeySequence("Ctrl+s"))

        self.load_image_action = QtGui.QAction(
            QtGui.QIcon(f"resources/icons/{self.theme_folder}/image-line.png"),
            QtCore.QCoreApplication.translate(
                "action_load_image", "&Load Image or PDF"
            ),
            self,
        )
        self.load_image_action.setStatusTip(
            QtCore.QCoreApplication.translate("status_load_image", "Load Image")
        )
        self.load_image_action.triggered.connect(self.load_image_dialog)
        self.load_image_action.setShortcut(QtGui.QKeySequence("Ctrl+i"))

        self.analyze_layout_action = QtGui.QAction(
            QtGui.QIcon(f"resources/icons/{self.theme_folder}/layout-line.png"),
            QtCore.QCoreApplication.translate(
                "action_analyze_layout", "&Analyze Layout"
            ),
            self,
        )
        self.analyze_layout_action.setStatusTip(
            QtCore.QCoreApplication.translate("status_analyze_layout", "Analyze Layout")
        )
        self.analyze_layout_action.triggered.connect(self.analyze_layout_current)
        self.analyze_layout_action.setShortcut(QtGui.QKeySequence("Ctrl+Alt+a"))

        self.analyze_layout_and_recognize_action = QtGui.QAction(
            QtGui.QIcon(f"resources/icons/{self.theme_folder}/layout-fill.png"),
            QtCore.QCoreApplication.translate(
                "action_analyze_layout_and_recognize", "Analyze Layout and &Recognize"
            ),
            self,
        )
        self.analyze_layout_and_recognize_action.setStatusTip(
            QtCore.QCoreApplication.translate(
                "status_analyze_layout_and_recognize", "Analyze Layout and Recognize"
            )
        )
        self.analyze_layout_and_recognize_action.triggered.connect(
            self.analyze_layout_and_recognize_current
        )
        self.analyze_layout_and_recognize_action.setShortcut(
            QtGui.QKeySequence("Ctrl+Alt+r")
        )

        self.analyze_layout_action_selected = QtGui.QAction(
            QtGui.QIcon(f"resources/icons/{self.theme_folder}/layout-line.png"),
            QtCore.QCoreApplication.translate(
                "action_analyze_layout", "&Analyze Layout for Selected Pages"
            ),
            self,
        )
        self.analyze_layout_action_selected.setStatusTip(
            QtCore.QCoreApplication.translate("status_analyze_layout", "Analyze Layout")
        )
        self.analyze_layout_action_selected.triggered.connect(
            self.analyze_layout_selected
        )

        self.analyze_layout_and_recognize_action_selected = QtGui.QAction(
            QtGui.QIcon(f"resources/icons/{self.theme_folder}/layout-fill.png"),
            QtCore.QCoreApplication.translate(
                "action_analyze_layout_and_recognize",
                "Analyze Layout and &Recognize Selected Pages",
            ),
            self,
        )
        self.analyze_layout_and_recognize_action_selected.setStatusTip(
            QtCore.QCoreApplication.translate(
                "status_analyze_layout_and_recognize", "Analyze Layout and Recognize"
            )
        )
        self.analyze_layout_and_recognize_action_selected.triggered.connect(
            self.analyze_layout_and_recognize_selected
        )

        self.close_project_action = QtGui.QAction(
            QtGui.QIcon(f"resources/icons/{self.theme_folder}/close-line.png"),
            QtCore.QCoreApplication.translate("action_close_project", "&Close project"),
            self,
        )
        self.close_project_action.setStatusTip(
            QtCore.QCoreApplication.translate("status_close_project", "Close project")
        )
        self.close_project_action.triggered.connect(self.close_current_project)
        self.close_project_action.setShortcut(QtGui.QKeySequence("Ctrl+w"))

        self.undo_action = self.undo_stack.createUndoAction(
            self, QtCore.QCoreApplication.translate("Undo", "&Undo")
        )
        self.undo_action.setIcon(
            QtGui.QIcon(f"resources/icons/{self.theme_folder}/arrow-go-back-line.png")
        )
        self.undo_action.setShortcut(QtGui.QKeySequence("Ctrl+z"))
        # self.undo_action.triggered.connect(self.undo)

        self.redo_action = self.undo_stack.createRedoAction(
            self, QtCore.QCoreApplication.translate("Redo", "&Redo")
        )
        self.redo_action.setIcon(
            QtGui.QIcon(
                f"resources/icons/{self.theme_folder}/arrow-go-forward-line.png"
            )
        )
        self.redo_action.setShortcut(QtGui.QKeySequence("Ctrl+y"))
        # self.redo_action.triggered.connect(self.redo)

        self.preferences_action = QtGui.QAction(
            QtGui.QIcon(f"resources/icons/{self.theme_folder}/settings-3-line.png"),
            QtCore.QCoreApplication.translate("action_preferences", "&Preferences"),
            self,
        )
        self.preferences_action.setStatusTip(
            QtCore.QCoreApplication.translate("status_preferences", "Preferences")
        )
        self.preferences_action.triggered.connect(self.open_preferences)
        self.preferences_action.setShortcut(QtGui.QKeySequence("Ctrl+p"))
        # self.redo_action.triggered.connect(self.redo)

        self.delete_selected_pages_action = QtGui.QAction(
            QtCore.QCoreApplication.translate("delete_pages", "Delete"), self
        )
        self.delete_selected_pages_action.setShortcut(QtGui.QKeySequence("Delete"))

        self.page_icon_view_context_menu.addAction(self.load_image_action)

    def setup_toolbar(self):
        # Toolbar
        self.toolbar.addAction(self.load_image_action)
        self.toolbar.addAction(self.open_project_action)
        self.toolbar.addAction(self.save_project_action)
        self.toolbar.addAction(self.export_action)
        self.toolbar.addAction(self.export_txt_action)
        self.toolbar.addAction(self.export_epub_action)
        self.toolbar.addAction(self.export_odt_action)
        self.toolbar.addAction(self.analyze_layout_action)
        self.toolbar.addAction(self.analyze_layout_and_recognize_action)
        self.toolbar.addAction(self.undo_action)
        self.toolbar.addAction(self.redo_action)

    def setup_menus(self):
        # File menu
        self.file_menu.addAction(self.load_image_action)
        self.file_menu.addAction(self.open_project_action)
        self.file_menu.addAction(self.save_project_action)
        self.file_menu.addAction(self.close_project_action)
        self.file_menu.addAction(self.export_action)
        self.file_menu.addAction(self.export_txt_action)
        self.file_menu.addAction(self.export_epub_action)
        self.file_menu.addAction(self.export_odt_action)
        self.file_menu.addSeparator()

        # Recent documents/projects
        self.recent_docs_menu: QtWidgets.QMenu = QtWidgets.QMenu(
            QtCore.QCoreApplication.translate("menu_recent_docs", "Recent Documents"),
            self,
        )
        self.recent_projects_menu = QtWidgets.QMenu(
            QtCore.QCoreApplication.translate(
                "menu_recent_projects", "Recent Projects"
            ),
            self,
        )

        self.recent_docs: list[QtGui.QAction] = []
        self.recent_projects: list[QtGui.QAction] = []

        self.file_menu.addMenu(self.recent_docs_menu)
        self.file_menu.addMenu(self.recent_projects_menu)

        self.file_menu.addAction(self.exit_action)

        # Edit menu
        self.edit_menu.addAction(self.preferences_action)
        self.file_menu.addSeparator()
        self.edit_menu.addAction(self.undo_action)
        self.edit_menu.addAction(self.redo_action)

    def on_page_icon_view_context_menu(self, point):
        if self.page_icon_view.selectedIndexes():
            self.page_icon_view_context_menu.addAction(
                self.delete_selected_pages_action
            )
            self.page_icon_view_context_menu.addAction(
                self.analyze_layout_action_selected
            )
            self.page_icon_view_context_menu.addAction(
                self.analyze_layout_and_recognize_action_selected
            )

        action = self.page_icon_view_context_menu.exec_(
            self.page_icon_view.mapToGlobal(point)
        )

        if action == self.delete_selected_pages_action:
            self.page_icon_view.remove_selected_pages()
            self.update()
        # elif action == self.action_select_all:
        #     # self.model().removeRows(0, self.model().rowCount())

    # def undo(self):
    #     pass

    # def redo(self):
    #     pass

    def analyze_pages(self, recognize=False, current=False):
        # if selected:
        #     indexes = self.page_icon_view.selectedIndexes()
        # else:
        #     for row in range(self.page_icon_view.model().rowCount()):
        #         indexes.append(self.page_icon_view.model().index(row, 0))

        indexes = self.page_icon_view.selectedIndexes()

        if indexes:
            if current:
                indexes = [indexes[0]]

            for index in indexes:
                self.page_icon_view.clearSelection()
                self.page_icon_view.setCurrentIndex(index)
                self.page_selected(index)
                self.page_icon_view.update(index)
                app_instance = QtCore.QCoreApplication.instance()
                if app_instance:
                    app_instance.processEvents()

                self.box_editor.scene().clear_boxes()
                self.box_editor.update()
                if app_instance:
                    app_instance.processEvents()

                self.box_editor.analyze_layout(recognize)
                self.box_editor.update()
                if app_instance:
                    app_instance.processEvents()

    def analyze_layout_current(self) -> None:
        self.analyze_pages(current=True)

    def analyze_layout_and_recognize_current(self) -> None:
        self.analyze_pages(current=True, recognize=True)

    def analyze_layout_selected(self) -> None:
        self.analyze_pages()

    def analyze_layout_and_recognize_selected(self) -> None:
        self.analyze_pages(recognize=True)

    def page_selected(self, index: QtCore.QModelIndex):
        page = index.data(QtCore.Qt.ItemDataRole.UserRole)

        if page:
            if self.box_editor.current_page == page:
                return

            self.box_editor.load_page(page)
            self.project.current_page_idx = self.page_icon_view.currentIndex().row()
            self.box_editor.scene().update()
            # self.box_editor.setFocus()
        else:
            self.box_editor.clear()

    def project_set_active(self):
        self.export_action.setEnabled(True)
        self.save_project_action.setEnabled(True)
        self.analyze_layout_action.setEnabled(True)
        self.analyze_layout_and_recognize_action.setEnabled(True)
        self.close_project_action.setEnabled(True)

    def load_image_dialog(self) -> None:
        filenames = QtWidgets.QFileDialog.getOpenFileNames(
            parent=self,
            caption=QtCore.QCoreApplication.translate(
                "status_load_image", "Load Image or PDF"
            ),
            filter=QtCore.QCoreApplication.translate(
                "filter_image_files",
                "Image and PDF files (*.jpg *.jpeg *.png *.gif *.bmp *.ppm *.pdf)",
            ),
        )

        pages: list[Page] = []

        for filename in filenames[0]:
            pages += self.load_images([filename])

        if filenames[1]:
            # Load first page
            self.box_editor.load_page(pages[0])

        self.project_set_active()

    def load_images(self, filenames: list[str]) -> list[Page]:
        load_image_command = LoadImageCommand(self, filenames)
        self.undo_stack.push(load_image_command)

        return load_image_command.pages

    def open_project_file(self, filename: str) -> None:
        self.close_project()

        project_file = QtCore.QFile(filename)
        project_file.open(QtCore.QIODevice.OpenModeFlag.ReadOnly)
        input = QtCore.QDataStream(project_file)

        # Read project
        project = Project()
        try:
            project.read(input)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
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

            if project.current_page_idx:
                self.box_editor.load_page(project.pages[project.current_page_idx])

            self.last_project_filename = filename

            self.project_set_active()
            self.statusBar().showMessage(
                QtCore.QCoreApplication.translate(
                    "status_project_opened", "Project opened"
                )
                + ": "
                + project_file.fileName()
            )

        # Add file path to recent projects menu
        self.recent_files_manager.add_recent_project(filename)

    def open_project(self) -> None:
        filename = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            caption=QtCore.QCoreApplication.translate(
                "dialog_open_project_file", "Open project file"
            ),
            filter=QtCore.QCoreApplication.translate(
                "filter_ocr_reader_project", "OCR Reader project (*.orp)"
            ),
        )[0]

        if filename:
            self.open_project_file(filename)

    def save_project(self) -> None:
        filename = self.last_project_filename

        if not filename:
            filename = QtWidgets.QFileDialog.getSaveFileName(
                parent=self,
                caption=QtCore.QCoreApplication.translate(
                    "dialog_save_project", "Save project"
                ),
                filter=QtCore.QCoreApplication.translate(
                    "filter_ocr_reader_project", "OCR Reader project (*.orp)"
                ),
            )[0]

        if filename:
            self.save_project_file(filename)

    def save_project_as(self) -> None:
        project_file = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption=QtCore.QCoreApplication.translate(
                "dialog_save_project", "Save project as"
            ),
            filter=QtCore.QCoreApplication.translate(
                "filter_ocr_reader_project", "OCR Reader project (*.orp)"
            ),
        )[0]

        if project_file:
            self.save_project_file(project_file)

    def save_project_file(self, filename) -> None:
        extension = os.path.splitext(filename)[1]

        if extension != ".orp":
            filename += ".orp"

        save_folder = os.path.dirname(os.path.abspath(filename))
        data_folder = save_folder + "/" + Path(ntpath.basename(filename)).stem

        for page in self.project.pages:
            if page.image_path.startswith(self.temp_dir.name):
                if not os.path.exists(data_folder):
                    os.makedirs(data_folder, exist_ok=True)

                new_path = data_folder + "/" + ntpath.basename(page.image_path)

                shutil.move(page.image_path, new_path)
                page.image_path = data_folder + "/" + ntpath.basename(page.image_path)

        file = QtCore.QFile(filename)
        file.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        output = QtCore.QDataStream(file)
        self.project.write(output)
        file.close()

        self.statusBar().showMessage(
            QtCore.QCoreApplication.translate("dialog_save_project", "Save project")
            + ": "
            + file.fileName()
        )
        self.last_project_filename = filename
        self.last_project_directory = os.path.dirname(
            os.path.abspath(self.last_project_filename)
        )

        # Add file path to recent projects menu
        self.recent_files_manager.add_recent_project(filename)

    def close_project(self) -> None:
        self.page_icon_view.close()
        self.box_editor.close()
        self.property_editor.close()
        self.last_project_filename = ""

    def close_current_project(self) -> None:
        self.close_project()
        self.setup_project()

    def export_project(self) -> None:
        self.run_exporter("PlainText")

    def run_exporter(self, id):
        exporter = self.exporter_manager.get_exporter(id)

        # Exclude boxes in header or footer area
        self.box_editor.scene().disable_boxes_in_header_footer()

        if exporter.open(self.temp_dir, self.project):
            any_recognized = False

            for p, page in enumerate(self.project.pages):
                for box_data in page.box_datas:
                    if box_data.type == BOX_DATA_TYPE.TEXT:
                        if box_data.recognized:
                            any_recognized = True
                    else:
                        any_recognized = True

            if any_recognized:
                if exporter.open(self.temp_dir, self.project):
                    for p, page in enumerate(self.project.pages):
                        exporter.new_page(page, p + 1)

                        for box_data in page.box_datas:
                            if box_data.recognized:
                                if box_data.export_enabled:
                                    exporter.write_box(box_data)

                    exporter.finish()

                    self.statusBar().showMessage(
                        QtCore.QCoreApplication.translate(
                            "status_exported", "Project exported successfully"
                        )
                    )
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    QtCore.QCoreApplication.translate(
                        "export_canceled", "Export Canceled"
                    ),
                    QtCore.QCoreApplication.translate(
                        "export_canceled_message",
                        "There are no recognized text boxes or images that can be exported for this document. The export process has been canceled.",
                    ),
                    QtWidgets.QMessageBox.StandardButton.Ok,
                )

        else:
            self.statusBar().showMessage(
                QtCore.QCoreApplication.translate(
                    "status_export_aborted", "Project export aborted"
                )
            )

    def export_plaintext(self):
        self.run_exporter("PlainText")

    def export_epub(self):
        self.run_exporter("EPUB")

    def export_odt(self):
        self.run_exporter("ODT")

    def open_preferences(self):
        options = Preferences(self, self.settings)

        if options.exec():
            return True
        else:
            return False

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            filenames = []

            for url in event.mimeData().urls():
                filenames.append(url.toLocalFile())

            self.load_images(filenames)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.save_settings()
        return super().closeEvent(event)

    def save_settings(self) -> None:
        self.settings.setValue("geometry", self.saveGeometry())

        recent_docs: list[str] = []

        for recent_doc in self.recent_docs:
            recent_docs.append(recent_doc.text())

        self.settings.setValue("recentDocs", recent_docs)

        recent_projects: list[str] = []

        for recent_project in self.recent_projects:
            recent_projects.append(recent_project.text())

        self.settings.setValue("recentProjects", recent_projects)

    def load_settings(self) -> None:
        self.settings = QtCore.QSettings()

        value = self.settings.value("geometry")

        if isinstance(value, QtCore.QByteArray):
            geometry: QtCore.QByteArray = value

            if geometry:
                self.restoreGeometry(geometry)
            else:
                self.resize(1280, 800)

        value = self.settings.value("recentDocs")

        if isinstance(value, list):
            recent_docs: list[str] = value

            if recent_docs:
                for recent_doc in reversed(recent_docs):
                    self.recent_files_manager.add_recent_doc(recent_doc)

        value = self.settings.value("recentProjects")

        if isinstance(value, list):
            recent_projects: list[str] = value

            if recent_projects:
                for recent_project in reversed(recent_projects):
                    self.recent_files_manager.add_recent_project(recent_project)


class LoadImageCommand(QtGui.QUndoCommand):
    def __init__(self, main_window: MainWindow, filenames: list[str]):
        super().__init__()
        self.main_window = main_window
        self.filenames: list[str] = filenames
        self.pages: list[Page] = []

    def redo(self) -> None:
        pages: list[Page] = []

        for filename in self.filenames:
            if filename:
                image_filenames: list[str] = []

                # Split PDFs into images and save them in an image folder
                if os.path.splitext(filename)[1] == ".pdf":
                    images = convert_from_path(
                        filename, output_folder=self.main_window.temp_dir.name
                    )

                    for image in images:
                        image_png_filename = os.path.join(
                            self.main_window.temp_dir.name,
                            f"{Path(filename).stem}_{images.index(image)}.png",
                        )
                        image.save(image_png_filename, "PNG")
                        image_filenames.append(image_png_filename)

                        # TODO: Delete images from folder on undo

                else:
                    image_filenames.append(filename)

                for image_filename in image_filenames:
                    page = Page(
                        image_path=image_filename,
                        name=ntpath.basename(filename),
                        paper_size=self.main_window.project.default_paper_size,
                    )
                    self.main_window.project.add_page(page)
                    self.main_window.page_icon_view.load_page(page)
                    pages.append(page)

                    self.main_window.statusBar().showMessage(
                        QtCore.QCoreApplication.translate(
                            "status_image_loaded", "Image loaded", "MainWindow"
                        )
                        + ": "
                        + page.image_path
                    )

                # Add file path to recent documents menu
                self.main_window.recent_files_manager.add_recent_doc(filename)

        if pages:
            self.main_window.project_set_active()

        self.pages = pages

    def undo(self) -> None:
        for page in self.pages:
            self.main_window.project.remove_page(page)
            self.main_window.page_icon_view.remove_page(page)
