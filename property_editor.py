import re
from string import punctuation

import enchant  # type: ignore
from iso639 import Lang
from papersize import SIZES
from PySide6 import QtCore, QtGui, QtWidgets

from box_editor.box_editor_scene import BoxData
from document_helper import DocumentHelper
from ocr_engine.ocr_engine import OCREngineManager
from project import Project


class TextEditor(QtWidgets.QTextEdit):
    editingFinished = QtCore.Signal()

    def __init__(self, parent, project: Project):
        super().__init__(parent)

        self.project = project

    def focusOutEvent(self, e: QtGui.QFocusEvent) -> None:
        self.editingFinished.emit()
        return super().focusOutEvent(e)


class ProjectPage(QtWidgets.QWidget):
    def __init__(self, parent, project: Project) -> None:
        super().__init__(parent)
        self.project = project
        layout = QtWidgets.QGridLayout(self)
        self.setLayout(layout)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed))

        self.name_edit = QtWidgets.QLineEdit(self)
        self.name_edit.setText(project.name)
        self.name_edit.editingFinished.connect(self.name_changed)
        layout.addWidget(self.name_edit, 0, 0, 1, 2)

        self.language_combo = QtWidgets.QComboBox(self)
        self.language_combo.currentTextChanged.connect(self.language_changed)
        layout.addWidget(self.language_combo, 1, 0, 1, 2)

        layout.addWidget(QtWidgets.QLabel(self.tr('Default paper size', 'paper_size')), 2, 0)

        self.default_paper_size_combo = QtWidgets.QComboBox(self)
        self.default_paper_size_combo.currentIndexChanged.connect(self.default_paper_size_changed)

        if self.project.pages:
            self.default_paper_size_combo.setCurrentText(SIZES[self.project.default_paper_size])

        layout.addWidget(self.default_paper_size_combo, 2, 1)

        layout.addWidget(QtWidgets.QLabel(self.tr('Remove hyphens', 'remove_hyphens')), 3, 0)

        self.remove_hyphens_checkbox = QtWidgets.QCheckBox(self)
        self.remove_hyphens_checkbox.stateChanged.connect(self.remove_hyphens_changed)

        layout.addWidget(self.remove_hyphens_checkbox, 3, 1)

    def name_changed(self):
        self.project.name = self.name_edit.text()

    def language_changed(self, language_text: str):
        self.project.default_language = Lang(self.language_combo.currentText())

    def default_paper_size_changed(self, default_paper_size_index):
        if self.project.pages:
            paper_size = self.default_paper_size_combo.itemData(default_paper_size_index)
            self.project.default_paper_size = paper_size

    def remove_hyphens_changed(self, state: int):
        self.project.remove_hyphens = (state != 0)


class PagePage(QtWidgets.QWidget):
    def __init__(self, parent, project: Project) -> None:
        super().__init__(parent)
        self.project = project

        layout = QtWidgets.QGridLayout(self)
        self.setLayout(layout)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed))

        layout.addWidget(QtWidgets.QLabel(self.tr('Paper size', 'paper_size')), 0, 0)

        self.paper_size_combo = QtWidgets.QComboBox(self)
        self.paper_size_combo.currentIndexChanged.connect(self.paper_size_changed)

        if self.project.pages:
            self.paper_size_combo.setCurrentText(SIZES[self.project.pages[self.project.current_page_idx].paper_size])

        layout.addWidget(self.paper_size_combo, 0, 1)

    def paper_size_changed(self, paper_size_index):
        if self.project.pages:
            paper_size = self.paper_size_combo.itemData(paper_size_index)
            self.project.pages[self.project.current_page_idx].set_paper_size(paper_size)


class BoxPage(QtWidgets.QWidget):
    def __init__(self, parent, project: Project) -> None:
        super().__init__(parent)

        layout = QtWidgets.QGridLayout(self)
        self.setLayout(layout)

        self.language_combo = QtWidgets.QComboBox(self)
        layout.addWidget(self.language_combo, 0, 0, 1, 2, QtCore.Qt.AlignmentFlag.AlignTop)

        self.text_edit = TextEditor(self, project)
        self.text_edit.setAcceptRichText(True)
        layout.addWidget(self.text_edit, 1, 0, 1, 2)

        layout.addWidget(QtWidgets.QLabel(self.tr('Tag', 'tag')), 2, 0)

        self.tag_edit = QtWidgets.QLineEdit(self)
        self.tag_edit.setPlaceholderText('Will be wrapped in EPUB/HTML export, e.g. "p" or "h1"')
        layout.addWidget(self.tag_edit, 2, 1)

        layout.addWidget(QtWidgets.QLabel(self.tr('Class(es)', 'classes')), 3, 0)

        self.class_edit = QtWidgets.QLineEdit(self)
        self.class_edit.setPlaceholderText('For EPUB/HTML export, multiple can be separated by space, e.g. "small caption"')
        layout.addWidget(self.class_edit, 3, 1)

        self.reset()

    def box_selected(self, box_datas: BoxData) -> None:
        self.setEnabled(True)
        self.current_box_datas = box_datas
        self.text_edit.setEnabled(True)

        # Clone document, as text_edit will take ownership
        self.text_edit.setDocument(box_datas.text.clone())
        self.text_edit.update()

        self.tag_edit.setText(box_datas.tag)
        self.tag_edit.update()

        self.class_edit.setText(box_datas.class_)
        self.class_edit.update()

    def reset(self) -> None:
        # Block textChanged signal to keep widget from getting focus on reset
        self.text_edit.blockSignals(True)

        self.text_edit.setDisabled(True)
        self.text_edit.setText('')
        self.text_edit.setPlaceholderText(self.tr('No text recognized yet.', 'no_text_recognized_yet'))

        self.text_edit.blockSignals(False)

        self.current_box_datas = None

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        match e.key():
            case QtCore.Qt.Key_F7:
                self.removeHyphens()
        return super().keyPressEvent(e)

    def removeHyphens(self) -> None:
        document_helper = DocumentHelper(self.text_edit.document(), Lang(self.language_combo.currentText()).pt1)
        self.text_edit.setDocument(document_helper.remove_hyphens())
        self.update()


class PropertyEditor(QtWidgets.QToolBox):
    def __init__(self, parent, engine_manager: OCREngineManager, project: Project) -> None:
        # self.box_editor: BoxEditor = None
        super().__init__(parent)

        self.project = project

        languages = engine_manager.get_current_engine().languages

        # Project
        self.project_widget = ProjectPage(self, self.project)
        self.project_widget.language_combo.addItems(languages)
        self.addItem(self.project_widget, self.tr('Project', 'project'))

        # Page
        self.page_widget = PagePage(self, self.project)

        self.project_widget.default_paper_size_combo.blockSignals(True)

        for size_key in SIZES:
            self.page_widget.paper_size_combo.addItem(SIZES[size_key], size_key)
            self.project_widget.default_paper_size_combo.addItem(SIZES[size_key], size_key)

        self.project_widget.default_paper_size_combo.blockSignals(False)

        self.addItem(self.page_widget, self.tr('Page', 'page'))

        # TODO: remove items instead of hiding
        self.page_widget.setDisabled(True)

        # Recognition
        self.box_widget = BoxPage(self, self.project)
        self.box_widget.language_combo.addItems(languages)
        self.addItem(self.box_widget, self.tr('Box', 'box'))

        self.box_widget.text_edit.textChanged.connect(self.focus_box_widget)
        # self.box_widget.text_edit.editingFinished.connect(self.update_box)
        self.project_widget.language_combo.currentTextChanged.connect(self.box_widget.language_combo.setCurrentText)

        self.box_widget.setDisabled(True)

    def cleanup(self):
        self.project = None

    def focus_box_widget(self) -> None:
        self.setCurrentWidget(self.box_widget)

    def update_box(self) -> None:
        pass
