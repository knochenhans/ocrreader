import re
import enchant
from iso639 import Lang
from PySide6 import QtCore, QtGui, QtWidgets

from boxeditor import BoxProperties
from ocrengine import OCREngineManager
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
        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)

        self.name_edit = QtWidgets.QLineEdit(self)
        self.name_edit.setText(project.name)
        layout.addWidget(self.name_edit)

        self.language_combo = QtWidgets.QComboBox(self)
        self.language_combo.currentTextChanged.connect(self.language_changed)
        layout.addWidget(self.language_combo)

        layout.addStretch()

    def language_changed(self, language_text):
        self.project.default_language = Lang(self.language_combo.currentText())


class RecognitionPage(QtWidgets.QWidget):
    def __init__(self, parent, project: Project) -> None:
        super().__init__(parent)

        # self.current_box_properties = None

        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)

        self.language_combo = QtWidgets.QComboBox(self)
        layout.addWidget(self.language_combo)

        self.text_edit = TextEditor(self, project)
        self.text_edit.setAcceptRichText(True)
        # self.text_edit.textChanged.connect(self.text_changed)
        layout.addWidget(self.text_edit)
        self.reset()

    # def text_changed(self):
    #     if self.current_box_properties:
    #         self.current_box_properties.text = self.text_edit.document()

    def box_selected(self, box_properties: BoxProperties) -> None:
        # if box_properties.ocr_result_block.paragraphs:
        self.current_box_properties = box_properties
        self.text_edit.setEnabled(True)
        # if box_properties.ocr_result_block:
        #     self.text_edit.setDocument(box_properties.ocr_result_block.get_text(True))
        self.text_edit.setDocument(box_properties.text)
        self.text_edit.update()

    def reset(self) -> None:
        # Block textChanged signal to keep widget from getting focus on reset
        self.text_edit.blockSignals(True)

        self.text_edit.setDisabled(True)
        self.text_edit.setText('')
        self.text_edit.setPlaceholderText('No text recognized yet.')

        self.text_edit.blockSignals(False)

        self.current_box_properties = None


class PropertyEditor(QtWidgets.QToolBox):
    def __init__(self, parent, engine_manager: OCREngineManager, project: Project) -> None:
        # self.box_editor: BoxEditor = None
        super().__init__(parent)

        self.project = project

        languages = engine_manager.get_current_engine().languages

        # Project
        self.project_widget = ProjectPage(self, self.project)
        self.project_widget.language_combo.addItems(languages)
        self.addItem(self.project_widget, 'Project')

        # Recognition
        self.recognition_widget = RecognitionPage(self, self.project)
        self.recognition_widget.language_combo.addItems(languages)
        self.addItem(self.recognition_widget, 'Recognition')

        self.recognition_widget.text_edit.textChanged.connect(self.focus_recognition_widget)
        # self.recognition_widget.text_edit.editingFinished.connect(self.update_box)
        self.project_widget.language_combo.currentTextChanged.connect(self.recognition_widget.language_combo.setCurrentText)

    def focus_recognition_widget(self) -> None:
        self.setCurrentWidget(self.recognition_widget)

    def update_box(self) -> None:
        pass
