from iso639 import Lang
from PySide6 import QtCore, QtGui, QtWidgets

from boxeditor import BoxOCRProperties
from ocrengine import OCREngineManager, OCRBlock, OCRWord
from project import Project
# import locale


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

    def select_box(self, box_properties: BoxOCRProperties):
        if box_properties.ocr_block.paragraphs:
            self.text_edit.setEnabled(True)
            self.text_edit.setDocument(self.get_text(box_properties.ocr_block))
            self.text_edit.update()
            self.setCurrentWidget(self.text_edit)

    def get_text(self, ocr_block: OCRBlock) -> QtGui.QTextDocument:
        document = QtGui.QTextDocument()
        cursor = QtGui.QTextCursor(document)
        format = QtGui.QTextCharFormat()

        for p, paragraph in enumerate(ocr_block.paragraphs):
            block_format = QtGui.QTextBlockFormat()
            # block_format.setBottomMargin(15.0)
            cursor.setBlockFormat(block_format)
            # TODO: Make this dependent on image DPI
            format.setFontPointSize(paragraph.get_avg_height())
            cursor.setCharFormat(format)
            # cursor.insertBlock(block_format)
            # cursor.deletePreviousChar()

            for l, line in enumerate(paragraph.lines):
                for w, word in enumerate(line.words):
                    if word.confidence < 90:
                        format.setBackground(QtGui.QColor(255, 0, 0, (1 - (word.confidence / 100)) * 200))
                    else:
                        format.clearBackground()
                    cursor.setCharFormat(format)

                    cursor.insertText(word.text)
                    if w < (len(line.words) - 1):
                        cursor.insertText(' ')
                if l < (len(paragraph.lines) - 1):
                    cursor.insertText('\n')
            if p < (len(ocr_block.paragraphs) - 1):
                cursor.insertText('\n\n')

        return document
