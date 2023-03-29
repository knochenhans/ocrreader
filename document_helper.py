from string import punctuation

import enchant
from PySide6 import QtGui


class DocumentHelper():
    def __init__(self, document: QtGui.QTextDocument, lang_code: str) -> None:
        self.document = document
        self.lang_code = lang_code

    def break_document_into_fragments(self) -> list[list]:
        paragraphs: list[list] = []
        
        block = self.document.begin()

        while block.isValid():
            line_fragments = []

            #     # Iterate over fragments
            #     # TODO: QTextBlock doesn’t offer Qt’s internal iterator facilities for some reason, use Python iterators
            #     try:
            #         frag_it = next(block.begin())
            #     except (StopIteration):
            #         # End of paragraph detected
            #         paragraphs.append(lines)
            #         lines = []
            #     else:
            #         if frag_it == block.end():
            #             # End of paragraph detected
            #             paragraphs.append(lines)
            #             lines = []

            #         for i in frag_it:
            #             line_fragments.append(i.fragment())
            #             # print(i.fragment().text())
            #             # cursor.insertText()
            #             next(i)

            #         if line_fragments:
            #             lines.append(line_fragments)

            frag_it = next(block.begin())

            while True:
                lines = []

                for i in frag_it:
                    line_fragments.append(i.fragment())
                    # print(i.fragment().text())
                    next(i)

                try:
                    next(frag_it)
                except (StopIteration):
                    # End of paragraph detected
                    paragraphs.append(line_fragments)
                    break

            block = block.next()

        # if lines:
        #     paragraphs.append(lines)

        return paragraphs

    def remove_hyphens(self) -> QtGui.QTextDocument:
        dictionary = enchant.Dict(self.lang_code + '_' + self.lang_code.upper())

        paragraphs = self.break_document_into_fragments()

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
