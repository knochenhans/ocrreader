from PySide6 import QtCore, QtGui, QtWidgets

from box_editor.box import Box
from box_editor.box_data import BOX_DATA_TYPE, BoxData
from box_editor.box_editor_scene import BoxEditorScene
from ocr_engine.ocr_results import OCR_RESULT_BLOCK_TYPE, OCRResultBlock

# Assuming BoxEditorScene, Box, BoxData, OCRResultBlock, OCR_RESULT_BLOCK_TYPE, and BOX_DATA_TYPE are defined elsewhere
# from your_module import BoxEditorScene, Box, BoxData, OCRResultBlock, OCR_RESULT_BLOCK_TYPE, BOX_DATA_TYPE

class AddBoxCommand(QtGui.QUndoCommand):
    def __init__(
        self, box_editor_scene: BoxEditorScene, rect: QtCore.QRectF, order: int
    ):
        super().__init__()
        self.box_editor_scene: BoxEditorScene = box_editor_scene
        self.rect: QtCore.QRectF = rect
        self.order: int = order
        self.current_box: Box

    def redo(self) -> None:
        self.current_box = self.box_editor_scene.add_box_(self.rect, self.order)

    def undo(self) -> None:
        self.box_editor_scene.remove_box_(self.current_box)


class RemoveBoxCommand(QtGui.QUndoCommand):
    def __init__(self, box_editor_scene: BoxEditorScene, box: Box):
        super().__init__()
        self.box_editor_scene = box_editor_scene
        self.box = box

    def redo(self) -> None:
        self.box_editor_scene.remove_box_(self.box)

    def undo(self) -> None:
        self.box_editor_scene.add_box_(self.box.rect())


class ModifyBoxCommand(QtGui.QUndoCommand):
    def __init__(self, box: Box, properties: BoxData, last_pos: QtCore.QPointF):
        super().__init__()
        self.box = box
        self.properties = properties
        self.properties_old: BoxData
        self.last_pos = last_pos
        self.pos = self.box.pos()

    def redo(self) -> None:
        self.properties_old = self.box.properties
        self.box.properties = self.properties
        self.box.setPos(self.pos)

    def undo(self) -> None:
        self.box.setPos(self.last_pos)


class AnalyseLayoutCommand(QtGui.QUndoCommand):
    def __init__(self, box_editor_scene: BoxEditorScene):
        super().__init__()
        self.box_editor_scene = box_editor_scene
        self.boxes: list[Box] = []

    def redo(self) -> None:
        """Analyse layout, excluding footer and header. Gets recognition boxes from OCR engine and creates boxes in editor accordingly."""
        from_header = 0.0
        to_footer = 0.0

        if self.box_editor_scene.header_item:
            from_header = self.box_editor_scene.header_item.rect().bottom()
        if self.box_editor_scene.footer_item:
            to_footer = self.box_editor_scene.footer_item.rect().top()

        if self.box_editor_scene.image:
            block = self.box_editor_scene.engine_manager.get_current_engine().analyse_layout(
                self.box_editor_scene.image, int(from_header), int(to_footer)
            )

            if block:
                ocr_result_blocks: list[OCRResultBlock] = block

                if ocr_result_blocks:
                    added_boxes = 0

                    for ocr_result_block in ocr_result_blocks:
                        if (
                            ocr_result_block.type is OCR_RESULT_BLOCK_TYPE.H_LINE
                            or ocr_result_block.type is OCR_RESULT_BLOCK_TYPE.V_LINE
                        ):
                            # TODO: Not captured by undo/redo so far
                            self.box_editor_scene.addItem(
                                QtWidgets.QGraphicsLineItem(
                                    QtCore.QLine(
                                        ocr_result_block.bbox_rect.topLeft(),
                                        ocr_result_block.bbox_rect.bottomRight(),
                                    )
                                )
                            )
                        elif ocr_result_block.type != OCR_RESULT_BLOCK_TYPE.UNKNOWN:
                            new_box = self.box_editor_scene.add_box_(
                                QtCore.QRectF(
                                    ocr_result_block.bbox_rect.topLeft(),
                                    ocr_result_block.bbox_rect.bottomRight(),
                                ),
                                added_boxes,
                            )
                            new_box.properties.ocr_result_block = ocr_result_block

                            match ocr_result_block.type:
                                case OCR_RESULT_BLOCK_TYPE.TEXT:
                                    new_box.properties.type = BOX_DATA_TYPE.TEXT
                                case OCR_RESULT_BLOCK_TYPE.IMAGE:
                                    new_box.properties.type = BOX_DATA_TYPE.IMAGE

                            new_box.properties.tag = ocr_result_block.tag
                            new_box.properties.class_ = ocr_result_block.class_

                            new_box.update()
                            self.boxes.append(new_box)

                        self.box_editor_scene.current_box = None

                        added_boxes += 1
                        # TODO: Move to thread
                        if instance := QtCore.QCoreApplication.instance():
                            instance.processEvents()

                # Remove items fully contained by larger items
                delete_items: list[Box] = []

                for item in self.box_editor_scene.items():
                    if isinstance(item, Box):
                        if item.collidingItems(
                            QtCore.Qt.ItemSelectionMode.ContainsItemShape
                        ):
                            delete_items.append(item)

                for item in list(set(delete_items)):
                    if isinstance(item, Box):
                        self.box_editor_scene.removeItem(item)

                self.box_editor_scene.update_property_editor()

    def undo(self) -> None:
        for box in self.boxes:
            self.box_editor_scene.remove_box_(box)