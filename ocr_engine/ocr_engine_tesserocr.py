import tesserocr as tesserocr
from box_editor.box_editor_scene import Box
from iso639 import Lang
from ocr_result_block import OCRResultBlock
from PySide6 import QtCore, QtGui

from ocr_engine.ocr_engine import OCREngine

import debugpy


class WorkerSignals(QtCore.QObject):
    finished = QtCore.Signal()
    result = QtCore.Signal(object)


class OCR_Worker(QtCore.QRunnable):
    def __init__(self, engine, box: Box, px_per_mm: float, language: Lang = Lang('English'), raw=False) -> None:
        super().__init__()

        self.engine = engine
        self.original_box = box
        self.px_per_mm = px_per_mm
        self.language = language
        self.raw = raw

        self.signals = WorkerSignals()

    def run(self) -> None:
        # blocks = self.engine.recognize(self.image, self.px_per_mm, self.language, self.raw)
        debugpy.debug_this_thread()

        blocks = []

        with tesserocr.PyTessBaseAPI(psm=tesserocr.PSM.AUTO, lang=self.language.pt2t) as api:
            api.SetImage(self.engine.pixmap_to_pil(self.original_box.get_image()))
            api.Recognize()
            hocr = api.GetHOCRText(0)

            blocks = self.engine.parse_hocr(hocr, self.original_box.get_image().size(), self.px_per_mm, self.language)

            #TODO: SetSourceResolution
            # TODO: SetRectangle (for multiple OCRs in one step)
            # TODO: GetTextlines (before recognition)
            # TODO: GetWords (before recognition)

        self.signals.result.emit([blocks, self.raw, self.original_box])
        self.signals.finished.emit()


class OCREngineTesserocr(OCREngine):
    name = 'TesserOCR'

    def __post_init__(self):
        self.languages = tesserocr.get_languages()[1]

        self.result_blocks = []

    def pixmap_strip_header_footer(self, image: QtGui.QPixmap, from_header=0, to_footer=0) -> QtGui.QPixmap:
        rect = image.rect()
        rect.setTop(from_header)
        if to_footer:
            rect.setBottom(to_footer)
        return image.copy(rect)

    def start_recognize_thread(self, callback, box: Box, px_per_mm: float, language: Lang = Lang('English'), raw=False):
        worker = OCR_Worker(self, box, px_per_mm, language, raw)
        worker.signals.result.connect(callback)
        # worker.signals.finished.connect(self.thread_complete)

        self.threadpool.start(worker)

    # def recognize_finished(self, blocks):
    #     self.result_blocks = blocks

    # def thread_complete(self):
    #     pass

    def recognize_raw(self, image: QtGui.QPixmap, language: Lang = Lang('English')) -> list[OCRResultBlock] | None:
        blocks = []

        # with tesserocr.PyTessBaseAPI(psm=tesserocr.PSM.SINGLE_BLOCK, lang=language.pt2t) as api:
        #     api.SetImage(self.pixmap_to_pil(image))
        #     api.Recognize()
        #     hocr = api.GetHOCRText(0)

        #     blocks = self.parse_hocr(hocr, image.size(), px_per_mm, language)

        return blocks

    # def recognize(self, image: QtGui.QPixmap, px_per_mm: float, language: Lang = Lang('English'), raw=False, psm_override=3) -> list[OCRResultBlock] | None:

    def analyse_layout(self, image: QtGui.QPixmap, from_header=0, to_footer=0) -> list[OCRResultBlock] | None:
        blocks = []

        margin = 5

        with tesserocr.PyTessBaseAPI(psm=tesserocr.PSM.AUTO_ONLY) as api:
            api.SetImage(self.pixmap_to_pil(self.pixmap_strip_header_footer(image, from_header, to_footer)))
            tess_blocks = api.GetComponentImages(tesserocr.RIL.BLOCK, True)

            for tess_block in tess_blocks:
                image, bbox, block_id, paragraph_id = tess_block

                block = OCRResultBlock()
                block.bbox = QtCore.QRect(bbox['x'], bbox['y'] + from_header, bbox['w'], bbox['h'])

                block = self.add_safety_margin(block, margin)

                blocks.append(block)

        return blocks
