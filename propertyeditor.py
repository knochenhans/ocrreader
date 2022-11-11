from iso639 import Lang
from PySide6 import QtCore, QtGui, QtWidgets

from boxeditor import BoxOCRProperties
from ocrengine import OCREngineManager, OCRBlock, OCRWord
from project import Project
import enchant


class ProjectPage(QtWidgets.QWidget):
    def __init__(self, parent, engine_manager: OCREngineManager, project: Project):
        super().__init__(parent)
        self.project = project
        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)

        self.name_edit = QtWidgets.QLineEdit(self)
        self.name_edit.setText(project.name)
        layout.addWidget(self.name_edit)

        self.lang_combo = QtWidgets.QComboBox(self)
        layout.addWidget(self.lang_combo)
        self.lang_combo.currentTextChanged.connect(self.language_changed)

        layout.addStretch()

        languages = engine_manager.get_current_engine().languages
        self.lang_combo.addItems(languages)

        # #TODO: Should probably go to settings
        # system_locale = locale.getlocale()[0]
        # Lang.

    def language_changed(self):
        self.project.language = Lang(self.lang_combo.currentText())

class PropertyEditor(QtWidgets.QToolBox):
    def __init__(self, parent, engine_manager: OCREngineManager, project: Project):
        self.box_editor: BoxEditor = None
        super().__init__(parent)

        self.project = project

        # Project
        self.addItem(ProjectPage(self, engine_manager, self.project), 'Project')

        # Recognition
        self.text_edit = QtWidgets.QTextEdit(self)
        self.text_edit.setAcceptRichText(True)
        self.addItem(self.text_edit, 'Recognition')
        self.text_edit.setDisabled(True)
        self.text_edit.setPlaceholderText('No text recognized yet.')
        self.text_edit.textChanged.connect(self.text_changed)

        self.current_box_properties = None
    
    def text_changed(self):
        if self.current_box_properties:
            self.current_box_properties.text = self.text_edit.document()

    def box_selected(self, box_properties: BoxOCRProperties):
        # if box_properties.ocr_block.paragraphs:
        self.current_box_properties = box_properties
        self.text_edit.setEnabled(True)
        self.text_edit.setDocument(box_properties.ocr_block.get_text(True))
        self.text_edit.update()
        self.setCurrentWidget(self.text_edit)

