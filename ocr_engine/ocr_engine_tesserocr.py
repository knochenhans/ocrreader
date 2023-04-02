import math
from dataclasses import dataclass, field

import debugpy
import tesserocr as tesserocr
from box_editor.box_editor_scene import Box
from iso639 import Lang  # type: ignore
from PySide6 import QtCore, QtGui

from ocr_engine.ocr_engine import OCREngine
from ocr_engine.ocr_results import (OCR_RESULT_BLOCK_TYPE, OCRResultBlock,
                                    OCRResultLine, OCRResultParagraph,
                                    OCRResultWord)


class WorkerSignals(QtCore.QObject):
    finished = QtCore.Signal()
    result = QtCore.Signal(object)


class OCR_Worker(QtCore.QRunnable):
    def __init__(self, engine, box: Box, image: QtGui.QPixmap, ppi: float, language: Lang = Lang('English'), raw=False) -> None:
        super().__init__()

        self.engine = engine
        self.original_box = box
        self.ppi = ppi
        self.language = language
        self.raw = raw
        self.image = image

        self.signals = WorkerSignals()

    def run(self) -> None:
        debugpy.debug_this_thread()

        blocks: list[OCRResultBlock] = []

        with tesserocr.PyTessBaseAPI(psm=tesserocr.PSM.AUTO, lang=self.language.pt2t) as api:
            api.SetImage(self.engine.pixmap_to_pil(self.image))
            api.SetSourceResolution(self.ppi)
            api.SetRectangle(self.original_box.rect().left(), self.original_box.rect().top(), self.original_box.rect().width(), self.original_box.rect().height())
            api.Recognize()

            ri = api.GetIterator()

            current_block = None
            current_paragraph = None
            current_line = None

            # for result_word in tesserocr.iterate_level(ri, tesserocr.RIL.SYMBOL):
            #     pass

            for result_word in tesserocr.iterate_level(ri, tesserocr.RIL.WORD):
                if result_word.IsAtBeginningOf(tesserocr.RIL.BLOCK):
                    current_block = OCRResultBlock()
                    current_block.text = ri.GetUTF8Text(tesserocr.RIL.BLOCK)
                    current_block.confidence = ri.Confidence(tesserocr.RIL.BLOCK)
                    current_block.set_bbox(ri.BoundingBox(tesserocr.RIL.BLOCK))
                    current_block.set_baseline(ri.Baseline(tesserocr.RIL.BLOCK))
                    current_block.language = self.language
                    blocks.append(current_block)

                if result_word.IsAtBeginningOf(tesserocr.RIL.PARA):
                    current_paragraph = OCRResultParagraph()
                    current_paragraph.text = ri.GetUTF8Text(tesserocr.RIL.PARA)
                    current_paragraph.confidence = ri.Confidence(tesserocr.RIL.PARA)
                    current_paragraph.set_bbox(ri.BoundingBox(tesserocr.RIL.PARA))
                    current_paragraph.set_baseline(ri.Baseline(tesserocr.RIL.PARA))
                    if current_block:
                        current_block.paragraphs.append(current_paragraph)

                if result_word.IsAtBeginningOf(tesserocr.RIL.TEXTLINE):
                    current_line = OCRResultLine()
                    current_line.text = ri.GetUTF8Text(tesserocr.RIL.TEXTLINE)
                    current_line.confidence = ri.Confidence(tesserocr.RIL.TEXTLINE)
                    current_line.set_bbox(ri.BoundingBox(tesserocr.RIL.TEXTLINE))
                    current_line.set_baseline(ri.Baseline(tesserocr.RIL.TEXTLINE))
                    if current_paragraph:
                        current_paragraph.lines.append(current_line)

                if not result_word.Empty(tesserocr.RIL.WORD):
                    current_word = OCRResultWord()
                    current_word.text = result_word.GetUTF8Text(tesserocr.RIL.WORD)
                    current_word.confidence = ri.Confidence(tesserocr.RIL.WORD)
                    current_word.set_bbox(ri.BoundingBox(tesserocr.RIL.WORD))
                    current_word.set_baseline(ri.Baseline(tesserocr.RIL.WORD))
                    current_word.blanks_before = result_word.BlanksBeforeWord()
                    row_attributes = ri.RowAttributes()
                    # TODO: Not sure this is the right way, also check ascenders
                    # current_word.font_size = 1 / self.ppi * (row_attributes['row_height'] + row_attributes['descenders']) * 72
                    current_word.font_size = math.ceil(1 / self.ppi * row_attributes['row_height'] * 72)
                    if current_line:
                        current_line.words.append(current_word)

            # TODO: GetTextlines (before recognition)
            # TODO: GetWords (before recognition)

        self.signals.result.emit([blocks, self.raw, self.original_box])
        self.signals.finished.emit()

@dataclass
class OCREngineTesserocr(OCREngine):
    name = 'TesserOCR'

    def __post_init__(self):
        self.languages = tesserocr.get_languages()[1]

        self.result_blocks: list[OCRResultBlock] = []

    def pixmap_strip_header_footer(self, image: QtGui.QPixmap, from_header=0, to_footer=0) -> QtGui.QPixmap:
        rect = image.rect()
        rect.setTop(from_header)
        if to_footer:
            rect.setBottom(to_footer)
        return image.copy(rect)

    def start_recognize_thread(self, callback, box: Box, image: QtGui.QPixmap, ppi: float, language: Lang = Lang('English'), raw=False):
        worker = OCR_Worker(self, box, image, ppi, language, raw)
        worker.signals.result.connect(callback)
        # worker.signals.finished.connect(self.thread_complete)

        self.threadpool.start(worker)

    # def recognize_finished(self, blocks):
    #     self.result_blocks = blocks

    # def thread_complete(self):
    #     pass

    def recognize_raw(self, image: QtGui.QPixmap, language: Lang = Lang('English')) -> list[OCRResultBlock] | None:
        blocks: list[OCRResultBlock] = []

        # with tesserocr.PyTessBaseAPI(psm=tesserocr.PSM.SINGLE_BLOCK, lang=language.pt2t) as api:
        #     api.SetImage(self.pixmap_to_pil(image))
        #     api.Recognize()
        #     hocr = api.GetHOCRText(0)

        #     blocks = self.parse_hocr(hocr, image.size(), ppi, language)

        return blocks

    def analyse_layout(self, image: QtGui.QPixmap, from_header=0, to_footer=0) -> list[OCRResultBlock] | None:
        blocks: list[OCRResultBlock] = []

        with tesserocr.PyTessBaseAPI(psm=tesserocr.PSM.AUTO_ONLY) as api:
            api.SetImage(self.pixmap_to_pil(self.pixmap_strip_header_footer(image, from_header, to_footer)))
            api.SetPageSegMode(tesserocr.PSM.AUTO_ONLY)
            page_it = api.AnalyseLayout()

            if page_it:
                for result in tesserocr.iterate_level(page_it, tesserocr.RIL.BLOCK):
                    block = OCRResultBlock(tesserocr.RIL.BLOCK)

                    left, top, right, bottom = result.BoundingBox(tesserocr.RIL.BLOCK, padding = 5)

                    block.bbox_rect = QtCore.QRect(QtCore.QPoint(left, top + from_header), QtCore.QPoint(right, bottom))

                    match result.BlockType():
                        case tesserocr.PT.FLOWING_TEXT | tesserocr.PT.PULLOUT_TEXT:
                            block.type = OCR_RESULT_BLOCK_TYPE.TEXT
                        case tesserocr.PT.HEADING_TEXT:
                            block.tag = 'h1'
                        case tesserocr.PT.CAPTION_TEXT:
                            block.tag = 'figcaption'
                        case tesserocr.PT.FLOWING_IMAGE | tesserocr.PT.HEADING_IMAGE | tesserocr.PT.PULLOUT_IMAGE:
                            block.type = OCR_RESULT_BLOCK_TYPE.IMAGE
                        case tesserocr.PT.HORZ_LINE:
                            block.type = OCR_RESULT_BLOCK_TYPE.H_LINE
                        case tesserocr.PT.VERT_LINE:
                            block.type = OCR_RESULT_BLOCK_TYPE.V_LINE
                        case _:
                            block.type = OCR_RESULT_BLOCK_TYPE.UNKNOWN

                    match result.BlockType():
                        case tesserocr.PT.FLOWING_TEXT | tesserocr.PT.FLOWING_IMAGE:
                            block.class_ = 'flowing'
                        case tesserocr.PT.HEADING_TEXT | tesserocr.PT.HEADING_IMAGE:
                            block.class_ = 'heading'
                        case tesserocr.PT.PULLOUT_TEXT | tesserocr.PT.PULLOUT_IMAGE:
                            block.class_ = 'pullout'

                    # TODO:
                    #  EQUATION
                    #  INLINE_EQUATION
                    #  TABLE
                    #  VERTICAL_TEXT
                    #  NOISE

                    blocks.append(block)

        return blocks
