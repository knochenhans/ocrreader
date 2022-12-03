import re
from string import punctuation

import enchant
from iso639 import Lang
from papersize import SIZES
from PySide6 import QtCore, QtGui, QtWidgets

from boxeditor import BoxData
from ocrengine import OCREngineManager
from project import Project


class DocumentHelper():
    def __init__(self, document: QtGui.QTextDocument, lang_code: str) -> None:
        self.document = document
        self.lang_code = lang_code

    def removeHyphens(self) -> QtGui.QTextDocument:
        dictionary = enchant.Dict(self.lang_code + '_' + self.lang_code.upper())

        paragraphs = []

        lines = []

        block = self.document.begin()

        while block.isValid():

            line_fragments = []

            # Iterate over fragments
            # TODO: QTextBlock doesn’t offer Qt’s internal iterator facilities for some reason, use Python iterators
            try:
                frag_it = next(block.begin())
            except (StopIteration):
                # End of paragraph detected
                paragraphs.append(lines)
                lines = []
            else:
                for i in frag_it:
                    line_fragments.append(i.fragment())
                    # print(i.fragment().text())
                    # cursor.insertText()
                    next(i)

            if line_fragments:
                lines.append(line_fragments)
            block = block.next()

        if lines:
            paragraphs.append(lines)

        new_document = QtGui.QTextDocument()
        cursor = QtGui.QTextCursor(new_document)
        format = QtGui.QTextCharFormat()

        first_word = ''

        for p, paragraph in enumerate(paragraphs):
            for l, line in enumerate(paragraph):
                for f, fragment in enumerate(line):
                    text: str = fragment.text()

                    format: QtGui.QTextCharFormat = fragment.charFormat()
                    cursor.setCharFormat(format)

                    if first_word:
                        (first_word, a, b) = text.partition(' ')
                        text = b
                        first_word = ''

                    if f == len(line) - 1:
                        if text:
                            if text[-1] == '-':
                                if l < len(paragraph) - 1:
                                    (pre_a, pre_b, last_word) = text[:-1].rpartition(' ')
                                    (first_word, post_a, post_b) = paragraph[l + 1][0].text().partition(' ')

                                    if pre_a.strip():
                                        cursor.insertText(pre_a.strip() + ' ')

                                    if last_word and first_word:
                                        if dictionary.check((last_word + first_word).strip(punctuation + '»«›‹„“”')) and first_word[0].isalpha():
                                            # text = text[:-1] + first_word
                                            format.setUnderlineStyle(QtGui.QTextCharFormat.UnderlineStyle.DotLine)
                                            cursor.setCharFormat(format)
                                            cursor.insertText((last_word + first_word).strip())
                                        else:
                                            # text = text + first_word

                                            format.setUnderlineColor(QtGui.QColor(255, 0, 0, 255))
                                            format.setUnderlineStyle(QtGui.QTextCharFormat.UnderlineStyle.DotLine)
                                            cursor.setCharFormat(format)
                                            cursor.insertText((last_word + '-' + first_word).strip())

                                        format.setUnderlineStyle(QtGui.QTextCharFormat.UnderlineStyle.NoUnderline)
                                        format.clearBackground()
                                        cursor.setCharFormat(format)
                                        cursor.insertText(' ')
                                        continue
                    if text.strip():
                        cursor.insertText(text.strip())

                        format.clearBackground()
                        cursor.setCharFormat(format)
                        cursor.insertText(' ')

                if l == len(paragraph) - 1:
                    cursor.deletePreviousChar()

            if p < len(paragraphs) - 1:
                cursor.insertText('\n\n')

        return new_document


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
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed))

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

    def name_changed(self):
        self.project.name = self.name_edit.text()

    def language_changed(self, language_text):
        self.project.default_language = Lang(self.language_combo.currentText())

    def default_paper_size_changed(self, default_paper_size_index):
        if self.project.pages:
            paper_size = self.default_paper_size_combo.itemData(default_paper_size_index)
            self.project.default_paper_size = paper_size


class PagePage(QtWidgets.QWidget):
    def __init__(self, parent, project: Project) -> None:
        super().__init__(parent)
        self.project = project

        layout = QtWidgets.QGridLayout(self)
        self.setLayout(layout)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed))

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

        # self.current_box_datas = None

        layout = QtWidgets.QGridLayout(self)
        self.setLayout(layout)
        #self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed))

        self.language_combo = QtWidgets.QComboBox(self)
        layout.addWidget(self.language_combo, 0, 0, QtCore.Qt.AlignmentFlag.AlignTop)

        self.text_edit = TextEditor(self, project)
        self.text_edit.setAcceptRichText(True)
        layout.addWidget(self.text_edit, 1, 0)
        self.reset()

    def box_selected(self, box_datas: BoxData) -> None:
        # if box_datas.ocr_result_block.paragraphs:
        self.setEnabled(True)
        self.current_box_datas = box_datas
        self.text_edit.setEnabled(True)

        # if box_datas.ocr_result_block:
        #     self.text_edit.setDocument(box_datas.ocr_result_block.get_text(True))

        # Clone document, as text_edit will take ownership
        self.text_edit.setDocument(box_datas.text.clone())
        self.text_edit.update()

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
        self.text_edit.setDocument(document_helper.removeHyphens())
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

        for size_key in SIZES:
            self.page_widget.paper_size_combo.addItem(SIZES[size_key], size_key)
            self.project_widget.default_paper_size_combo.addItem(SIZES[size_key], size_key)

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
