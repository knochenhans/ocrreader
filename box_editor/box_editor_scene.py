from enum import Enum, auto
from typing import Union

from iso639 import Lang
from ocr_engine.ocr_engine import OCREngineManager  # type: ignore
from ocr_engine.ocr_results import (OCR_RESULT_BLOCK_TYPE, OCRResultBlock,
                                    OCRResultLine, OCRResultParagraph,
                                    OCRResultWord)
from project import Page, Project
from PySide6 import QtCore, QtGui, QtWidgets

from box_editor.box import BOX_DATA_TYPE, Box
from box_editor.box_data import BoxData


class HEADER_FOOTER_ITEM_TYPE(Enum):
    HEADER = auto()
    FOOTER = auto()


class SplitLine(QtWidgets.QGraphicsLineItem):
    def __init__(self, x: float, height: float):
        super().__init__()

        self.height = height

        self.setLine(x, 0, x, self.height)

    def update_x_position(self, x: float):
        self.setLine(x, 0, x, self.height)


class HeaderFooterItem(QtWidgets.QGraphicsRectItem):
    def __init__(self, type: HEADER_FOOTER_ITEM_TYPE, page_size: QtCore.QSizeF, y: float):
        super().__init__()

        rect = QtCore.QRectF()

        rect.setX(0)
        rect.setWidth(page_size.width())

        if type is HEADER_FOOTER_ITEM_TYPE.HEADER:
            title = 'Header'
            rect.setBottom(y)
        else:
            title = 'Footer'
            rect.setTop(y)
            rect.setBottom(page_size.height())

        self.setRect(rect)

        brush = QtGui.QBrush(QtGui.QColor(128, 0, 200, 150))
        brush.setStyle(QtCore.Qt.BrushStyle.BDiagPattern)

        self.setPen(QtCore.Qt.PenStyle.NoPen)
        self.setBrush(brush)

        pen = QtGui.QPen(QtGui.QColor(128, 0, 200, 150))
        pen.setWidth(1)
        pen.setStyle(QtCore.Qt.PenStyle.SolidLine)
        pen.setCosmetic(True)

        self.title = QtWidgets.QGraphicsSimpleTextItem(self)
        self.title.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.title.setPen(pen)
        self.title.setText(title)

        self.line = QtWidgets.QGraphicsLineItem(self)
        self.line.setPen(QtGui.QPen(QtGui.QColor(128, 0, 200, 200), 3, QtCore.Qt.PenStyle.SolidLine))
        self.line.setPos(0, y)
        self.line.setLine(0, 0, self.rect().width(), 0)

        self.setZValue(10)

    def update_title(self):
        self.title.setPos(5, self.rect().y() + 5)

    def update_bottom_position(self, y: float):
        rect = self.rect()
        rect.setBottom(y)
        self.setRect(rect)
        self.line.setPos(0, y)

    def update_top_position(self, y: float):
        rect = self.rect()
        rect.setTop(y)
        self.setRect(rect)
        self.line.setPos(0, y)
        self.title.setPos(5, self.rect().y() + 5)


class BOX_EDITOR_SCENE_STATE(Enum):
    SELECT = auto()
    DRAW_BOX = auto()
    HAND = auto()
    PLACE_HEADER = auto()
    PLACE_FOOTER = auto()
    PLACE_X_SPLITLINE = auto()
    RENUMBER = auto()


class BoxEditorScene(QtWidgets.QGraphicsScene):
    def __init__(self, parent, undo_stack: QtGui.QUndoStack, engine_manager: OCREngineManager, property_editor, project: Project, page: Page | None) -> None:
        super().__init__(parent)
        self.current_box: Box | None = None
        self.current_rect = QtCore.QRectF()
        self.header_item: HeaderFooterItem | None = None
        self.footer_item: HeaderFooterItem | None = None

        self.undo_stack = undo_stack

        self.project = project
        self.current_page = page
        self.image: QtGui.QPixmap | None = QtGui.QPixmap()
        # self.set_page_as_background(0)
        self.engine_manager = engine_manager
        self.box_counter = 0

        self.property_editor = property_editor

        # Setup connection to and from property editor
        self.selectionChanged.connect(self.update_property_editor)
        self.property_editor.box_widget.text_edit.editingFinished.connect(self.update_text)
        self.property_editor.box_widget.tag_edit.editingFinished.connect(self.update_tag)
        self.property_editor.box_widget.class_edit.editingFinished.connect(self.update_class_)
        self.property_editor.box_widget.language_combo.currentTextChanged.connect(self.update_language)

        # Current editor state
        self.editor_state = BOX_EDITOR_SCENE_STATE.SELECT
        self.set_editor_state(self.editor_state)

        # Current box type for drawing boxes
        self.current_box_type = BOX_DATA_TYPE.TEXT

        # Variables for box renumbering
        self.renumber_line = None
        self.set_renumber_first_box(None)

        self.x_splitline = None

        self.swap_left_right = False
        self.swap_top_bottom = False

        self.setBackgroundBrush(QtGui.QColorConstants.Svg.gray)

    def selectedItems(self) -> list[Box]:
        items = super().selectedItems()

        boxes: list[Box] = []

        for item in items:
            if isinstance(item, Box):
                boxes.append(item)
        return boxes

    def items(self, order=False) -> list[Box]:
        items = super().items()

        items_boxes: list[Box] = []

        for item in items:
            if isinstance(item, Box):
                items_boxes.append(item)

        return sorted(items_boxes, key=lambda x: x.properties.order)

    def focusNextPrevChild(self, next: bool) -> bool:
        current_item = self.selectedItems()[0]
        next_item_order = current_item
        step = 0

        if isinstance(current_item, Box):
            if next:
                step = 1
            else:
                step = -1

            next_item_order = (current_item.properties.order + step) % len(self.items())

        for item in self.items():
            if next_item_order == item.properties.order:
                self.clearSelection()
                item.setSelected(True)
                item.setFocus()

        return True

    def clear_boxes(self):
        if self.current_page:
            self.current_page.clear()
        for item in self.items():
            if isinstance(item, Box):
                self.removeItem(item)

    def clear(self):
        super().clear()

        self.image = None
        self.setSceneRect(QtCore.QRect())

    def set_editor_state(self, new_state: BOX_EDITOR_SCENE_STATE) -> None:
        cursor = QtCore.Qt.CursorShape.ArrowCursor

        old_state = self.editor_state

        match old_state:
            case BOX_EDITOR_SCENE_STATE.DRAW_BOX:
                self.views()[0].setStyleSheet('')
                for item in self.items():
                    item.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

        match new_state:
            case BOX_EDITOR_SCENE_STATE.SELECT:
                cursor = QtCore.Qt.CursorShape.ArrowCursor
            case BOX_EDITOR_SCENE_STATE.DRAW_BOX:
                cursor = QtCore.Qt.CursorShape.CrossCursor

                # Set color for rubberbox to resemble actual box (very limited though)
                self.views()[0].setStyleSheet('selection-background-color: rgb(0, 0, 255)')

                # Disable item selection while drawing
                for item in self.items():
                    item.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
            case BOX_EDITOR_SCENE_STATE.HAND:
                cursor = QtCore.Qt.CursorShape.OpenHandCursor
            case BOX_EDITOR_SCENE_STATE.PLACE_HEADER | BOX_EDITOR_SCENE_STATE.PLACE_FOOTER:
                cursor = QtCore.Qt.CursorShape.SplitVCursor
            case BOX_EDITOR_SCENE_STATE.RENUMBER:
                cursor = QtCore.Qt.CursorShape.PointingHandCursor

                items = self.selectedItems()

                if len(items):
                    self.set_renumber_first_box(items[0])

                for item in self.items():
                    item.setAcceptHoverEvents(False)
            case BOX_EDITOR_SCENE_STATE.PLACE_X_SPLITLINE:
                cursor = QtCore.Qt.CursorShape.SplitHCursor

        if cursor:
            QtWidgets.QApplication.setOverrideCursor(cursor)
        else:
            QtWidgets.QApplication.restoreOverrideCursor()

        self.editor_state = new_state

    def update_text(self) -> None:
        if len(self.selectedItems()) > 1:
            parent = self.parent()
            if isinstance(parent, QtWidgets.QWidget):
                button = QtWidgets.QMessageBox.question(parent, self.tr('Edit text of multiple boxes?', 'dialog_multiple_boxes_edit_title'), self.tr(
                    'Multiple boxes are currently selected, do you want to set the current text for all selected box?', 'dialog_multiple_boxes_edit'))

                if button == QtWidgets.QMessageBox.StandardButton.No:
                    return
        for item in self.selectedItems():
            item.properties.text = self.property_editor.box_widget.text_edit.document()
            self.update_property_editor()

    def update_tag(self) -> None:
        for item in self.selectedItems():
            item.properties.tag = self.property_editor.box_widget.tag_edit.text()

    def update_class_(self) -> None:
        for item in self.selectedItems():
            item.properties.class_ = self.property_editor.box_widget.class_edit.text()

    def update_language(self, text) -> None:
        for item in self.selectedItems():
            item.properties.language = Lang(text)

    def update_property_editor(self) -> None:
        '''Update property editor with the currently selected box'''
        for item in self.selectedItems():
            self.property_editor.box_widget.box_selected(item.properties)

    def disable_boxes_in_header_footer(self) -> None:
        for item in self.items():
            if self.header_item:
                if self.header_item.rect().contains(item.rect()):
                    item.properties.export_enabled = False
            if self.footer_item:
                if self.footer_item.rect().contains(item.rect()):
                    item.properties.export_enabled = False

    def shift_ordering(self, box: Box, shift_by: int):
        ordered_items = sorted(self.items(), key=lambda x: x.properties.order)

        move_rest = False

        for item in ordered_items:
            if isinstance(item, Box):
                if item != box:
                    if item.properties.order == box.properties.order:
                        move_rest = True
                    if move_rest:
                        item.properties.order += shift_by
                        item.update()

    def add_box(self, rect: QtCore.QRectF, order=-1) -> Box:
        '''Add new box and give it an order number'''

        add_box_command = AddBoxCommand(self, rect, order)
        self.undo_stack.push(add_box_command)

        return add_box_command.current_box

    def add_box_(self, rect: QtCore.QRectF, order=-1) -> Box:
        current_box = Box(rect, self.engine_manager, self)
        if self.current_page:
            self.current_page.box_datas.append(current_box.properties)
        current_box.properties.order = order
        current_box.properties.type = self.current_box_type

        self.addItem(current_box)

        if order >= 0:
            self.shift_ordering(current_box, 1)
        else:
            current_box.properties.order = self.box_counter
        self.box_counter += 1

        self.current_box = current_box

        return current_box

    def restore_box(self, box_datas: BoxData) -> Box:
        '''Restore a box in the editor using box properties stored in the project'''
        self.current_box = Box(QtCore.QRectF(box_datas.rect), self.engine_manager, self)
        self.current_box.properties = box_datas
        self.box_counter += 1
        self.addItem(self.current_box)
        return self.current_box

    def remove_box(self, box: Box) -> None:
        remove_box_command = RemoveBoxCommand(self, box)
        self.undo_stack.push(remove_box_command)

    def remove_box_(self, box: Box) -> None:
        '''Remove a box from the editor window and project'''
        self.removeItem(box)

        if self.current_page:
            self.current_page.box_datas.remove(box.properties)

        # Renumber items
        self.box_counter = 0
        self.current_box = None

        ordered_items = sorted(self.items(), key=lambda x: x.properties.order)

        for item in ordered_items:
            if isinstance(item, Box):
                item.properties.order = self.box_counter
                self.box_counter += 1
                item.update()

    def toggle_export_enabled(self, box: Box) -> None:
        box.properties.export_enabled = not box.properties.export_enabled
        box.update()

    def recognize_box(self, box: Box, raw=False):
        '''Run OCR for box and update properties with recognized text in selection, create new boxes if suggested by tesseract'''
        engine = self.engine_manager.get_current_engine()

        if self.image and self.current_page:
            engine.start_recognize_thread(self.new_ocr_results, box, self.image, self.current_page.ppi, box.properties.language, raw)

    def new_ocr_results(self, result: tuple[list[OCRResultBlock], bool, Box]):
        blocks, raw, original_box = result

        is_image = False
        remove_hyphens = self.project.remove_hyphens

        #TODO: Set in options
        confidence_treshold = 30

        if isinstance(blocks, list):
            if blocks:
                if raw:
                    original_box.properties.ocr_result_block = blocks[0]
                    original_box.properties.text = blocks[0].get_document(False)
                    original_box.properties.recognized = True
                else:
                    if len(blocks) == 1:
                        block = blocks[0]

                        if block.confidence > confidence_treshold:
                            original_box.properties.ocr_result_block = block
                            # original_box.properties.words = block.get_words()
                            original_box.properties.text = block.get_document(True, remove_hyphens)
                            original_box.properties.recognized = True
                        else:
                            is_image = True
                    elif len(blocks) > 1:
                        new_boxes: list[Box] = []

                        # Multiple text blocks have been recognized within the selection, replace original box with new boxes

                        # Remove original box
                        self.remove_box_(original_box)

                        added_boxes = 0

                        for block in blocks:
                            # Skip blocks with bad confidence (might be an image)
                            # TODO: Find a good threshold
                            if block.confidence > confidence_treshold:

                                # Add safety margin for correct recognition
                                block.add_margin(5)

                                # Add new blocks at the recognized positions and adjust child elements
                                # new_box = self.add_box(QtCore.QRectF(block.bbox_rect.translated(original_box.rect().topLeft().toPoint())), original_box.properties.order + added_boxes)
                                new_box = self.add_box(QtCore.QRectF(block.bbox_rect), original_box.properties.order + added_boxes)
                                # dist = original_box.rect().topLeft() - new_box.rect().topLeft()
                                new_box.properties.ocr_result_block = block

                                # Move paragraph lines and word boxes accordingly
                                # new_box.properties.ocr_result_block.translate(dist.toPoint())

                                new_box.properties.words = new_box.properties.ocr_result_block.get_words()
                                new_box.properties.text = new_box.properties.ocr_result_block.get_document(True, remove_hyphens)

                                new_box.properties.recognized = True
                                new_box.update()

                                self.current_box = None

                                new_boxes.append(new_box)
                                added_boxes += 1

                        if added_boxes > 0:
                            new_boxes[0].setSelected(True)
                        else:
                            is_image = True
                    else:
                        is_image = True

        if is_image:
            # The original box is probably an image
            original_box.set_type_to_image()

        original_box.update()
        self.update_property_editor()

    def get_mouse_position(self) -> QtCore.QPointF:
        mouse_origin = self.views()[0].mapFromGlobal(QtGui.QCursor.pos())
        return self.views()[0].mapToScene(mouse_origin)

    def add_header_footer(self, type: HEADER_FOOTER_ITEM_TYPE, y: float):
        if type is HEADER_FOOTER_ITEM_TYPE.HEADER:
            if self.header_item:
                self.removeItem(self.header_item)
        else:
            if self.footer_item:
                self.removeItem(self.footer_item)

        page_size = QtCore.QSizeF(self.width(), self.height())
        item = HeaderFooterItem(type, page_size, y)
        self.addItem(item)
        item.setFocus()
        item.update_title()

        if type is HEADER_FOOTER_ITEM_TYPE.HEADER:
            self.header_item = item
            if self.project:
                self.project.header_y = y
        else:
            self.footer_item = item
            if self.project:
                self.project.footer_y = y

    def set_renumber_first_box(self, item: Box | None):
        self.renumber_first_box = item

        if item:
            if not self.renumber_line:
                self.renumber_line = QtWidgets.QGraphicsLineItem()

                pen = QtGui.QPen(QtGui.QColor(227, 35, 35, 255))
                pen.setWidth(3)
                pen.setStyle(QtCore.Qt.PenStyle.DotLine)
                self.renumber_line.setPen(pen)

                self.addItem(self.renumber_line)
        else:
            if self.renumber_line:
                self.removeItem(self.renumber_line)
                self.renumber_line = None

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        from box_editor.box_editor_view import BoxEditorView
        '''Handle adding new box by mouse'''

        box_clicked = None

        # itemAt would return the QGraphicsLineItem object
        for item in self.items():
            if isinstance(item, Box):
                if item.contains(event.scenePos()):
                    box_clicked = item

        match self.editor_state:
            case BOX_EDITOR_SCENE_STATE.SELECT:
                match event.buttons():
                    case QtCore.Qt.MouseButton.LeftButton:
                        # Draw rubber band when no box is selected or Ctrl is being pressed
                        if not box_clicked or (box_clicked and event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier):
                            self.views()[0].setDragMode(QtWidgets.QGraphicsView.DragMode.RubberBandDrag)
                    case QtCore.Qt.MouseButton.MiddleButton:
                        view = self.views()[0]
                        if isinstance(view, BoxEditorView):
                            view.origin = event.pos().toPoint()
            case BOX_EDITOR_SCENE_STATE.DRAW_BOX:
                if not box_clicked:
                    self.views()[0].setDragMode(QtWidgets.QGraphicsView.DragMode.RubberBandDrag)
            case BOX_EDITOR_SCENE_STATE.PLACE_HEADER:
                if self.header_item:
                    if self.project:
                        self.project.header_y = self.header_item.rect().bottom()
                self.set_editor_state(BOX_EDITOR_SCENE_STATE.SELECT)
            case BOX_EDITOR_SCENE_STATE.PLACE_FOOTER:
                if self.footer_item:
                    if self.project:
                        self.project.footer_y = self.footer_item.rect().top()
                self.set_editor_state(BOX_EDITOR_SCENE_STATE.SELECT)
            case BOX_EDITOR_SCENE_STATE.RENUMBER:
                if self.renumber_first_box:
                    if isinstance(self.renumber_first_box, Box) and isinstance(box_clicked, Box):
                        # The second selected box will get the next higher order number
                        next_number = self.renumber_first_box.properties.order + 1

                        # Find existing box with new number and swap order numbers
                        for item in self.items():
                            if item.properties.order == next_number:
                                if not (item == self.renumber_first_box or item == box_clicked):
                                    swap = item.properties.order
                                    item.properties.order = box_clicked.properties.order
                                    box_clicked.properties.order = swap
                                    break

                        self.renumber_first_box.update()
                        self.clearSelection()
                        box_clicked.setSelected(True)
                        box_clicked.update()

                        self.set_renumber_first_box(None)

                        self.set_editor_state(BOX_EDITOR_SCENE_STATE.SELECT)
                        self.update()
                else:
                    if isinstance(box_clicked, Box):
                        self.set_renumber_first_box(box_clicked)
                return
            case BOX_EDITOR_SCENE_STATE.PLACE_X_SPLITLINE:

                if self.x_splitline and box_clicked:
                    box_line = QtWidgets.QGraphicsLineItem(box_clicked)
                    box_line.setLine(self.x_splitline.line().x1(), box_clicked.rect().top(), self.x_splitline.line().x2(), box_clicked.rect().bottom())

                    self.removeItem(self.x_splitline)
                    self.x_splitline = None

                self.set_editor_state(BOX_EDITOR_SCENE_STATE.SELECT)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        match self.editor_state:
            case BOX_EDITOR_SCENE_STATE.PLACE_HEADER:
                if self.header_item:
                    self.header_item.update_bottom_position(event.scenePos().y())
            case BOX_EDITOR_SCENE_STATE.PLACE_FOOTER:
                if self.footer_item:
                    self.footer_item.update_top_position(event.scenePos().y())
            case BOX_EDITOR_SCENE_STATE.RENUMBER:
                if self.renumber_line and self.renumber_first_box:
                    x = self.renumber_first_box.rect().x() + self.renumber_first_box.rect().width() / 2
                    y = self.renumber_first_box.rect().y() + self.renumber_first_box.rect().height() / 2
                    self.renumber_line.setLine(x, y, event.scenePos().x(), event.scenePos().y())
            case BOX_EDITOR_SCENE_STATE.PLACE_X_SPLITLINE:
                if self.x_splitline:
                    self.x_splitline.update_x_position(event.scenePos().x())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        match self.editor_state:
            case BOX_EDITOR_SCENE_STATE.SELECT:
                self.views()[0].setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)
            case BOX_EDITOR_SCENE_STATE.DRAW_BOX:
                # Commit current rubberband drag as new box and select
                if not self.current_rect.isEmpty():
                    top_left = self.views()[0].mapToScene(self.current_rect.topLeft().toPoint())
                    bottom_right = self.views()[0].mapToScene(self.current_rect.bottomRight().toPoint())

                    self.add_box(QtCore.QRectF(top_left, bottom_right).normalized()).setSelected(True)

                self.set_editor_state(BOX_EDITOR_SCENE_STATE.SELECT)
        super().mouseReleaseEvent(event)

    def rubber_band_changed(self, rubberBandRect: QtCore.QRect, fromScenePoint, toScenePoint):
        if not rubberBandRect.isEmpty():
            self.current_rect = rubberBandRect.toRectF()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        # Get selected boxes:
        boxes = self.selectedItems()

        # Sort by order number
        boxes.sort(key=lambda x: x.properties.order)

        match self.editor_state:
            case BOX_EDITOR_SCENE_STATE.SELECT:
                match event.modifiers():
                    case QtCore.Qt.KeyboardModifier.NoModifier:
                        match event.key():
                            case QtCore.Qt.Key.Key_F1:
                                self.set_editor_state(BOX_EDITOR_SCENE_STATE.SELECT)
                            case QtCore.Qt.Key.Key_F2:
                                self.set_editor_state(BOX_EDITOR_SCENE_STATE.DRAW_BOX)
                            case QtCore.Qt.Key.Key_F3:
                                self.set_editor_state(BOX_EDITOR_SCENE_STATE.HAND)
                            case QtCore.Qt.Key.Key_F4:
                                self.set_editor_state(BOX_EDITOR_SCENE_STATE.PLACE_HEADER)
                            case QtCore.Qt.Key.Key_F5:
                                self.set_editor_state(BOX_EDITOR_SCENE_STATE.PLACE_FOOTER)
                            case QtCore.Qt.Key.Key_Shift:
                                self.set_editor_state(BOX_EDITOR_SCENE_STATE.DRAW_BOX)
                            case QtCore.Qt.Key.Key_F6:
                                self.set_editor_state(BOX_EDITOR_SCENE_STATE.RENUMBER)
                            case QtCore.Qt.Key.Key_Delete:
                                for box in boxes:
                                    self.remove_box(box)
                            case QtCore.Qt.Key.Key_I:
                                self.current_box_type = BOX_DATA_TYPE.IMAGE
                                self.set_editor_state(BOX_EDITOR_SCENE_STATE.DRAW_BOX)
                            case QtCore.Qt.Key.Key_T:
                                self.current_box_type = BOX_DATA_TYPE.TEXT
                                self.set_editor_state(BOX_EDITOR_SCENE_STATE.DRAW_BOX)
                            case QtCore.Qt.Key.Key_H:
                                self.add_header_footer(HEADER_FOOTER_ITEM_TYPE.HEADER, self.get_mouse_position().y())
                                self.set_editor_state(BOX_EDITOR_SCENE_STATE.PLACE_HEADER)
                            case QtCore.Qt.Key.Key_F:
                                self.add_header_footer(HEADER_FOOTER_ITEM_TYPE.FOOTER, self.get_mouse_position().y())
                                self.set_editor_state(BOX_EDITOR_SCENE_STATE.PLACE_FOOTER)
                    case QtCore.Qt.KeyboardModifier.ControlModifier:
                        match event.key():
                            case QtCore.Qt.Key.Key_A:
                                for box in self.items():
                                    box.setSelected(True)
                            # case _:
                            #     super().keyPressEvent(event)
                    case QtCore.Qt.KeyboardModifier.AltModifier:
                        match event.key():
                            case QtCore.Qt.Key.Key_A:
                                for box in boxes:
                                    box.auto_align()
                            case QtCore.Qt.Key.Key_I:
                                for box in boxes:
                                    box.set_type_to_image()
                            case QtCore.Qt.Key.Key_T:
                                for box in boxes:
                                    box.set_type_to_text()
                            case QtCore.Qt.Key.Key_R:
                                for box in boxes:
                                    if box.properties.type != BOX_DATA_TYPE.IMAGE:
                                        box.recognize_text()
                                    # TODO: Move to thread
                                    if instance := QtCore.QCoreApplication.instance():
                                        instance.processEvents()
                            case QtCore.Qt.Key.Key_D:
                                for box in boxes:
                                    self.toggle_export_enabled(box)
                            case QtCore.Qt.Key.Key_X:
                                self.x_splitline = SplitLine(self.get_mouse_position().x(), self.height())
                                self.addItem(self.x_splitline)

                                self.set_editor_state(BOX_EDITOR_SCENE_STATE.PLACE_X_SPLITLINE)
                            # case _:
                            #     super().keyPressEvent(event)
            case BOX_EDITOR_SCENE_STATE.RENUMBER:
                self.set_editor_state(BOX_EDITOR_SCENE_STATE.RENUMBER)
            case _:
                # TODO: enable canceling actions
                if event.modifiers() == QtCore.Qt.KeyboardModifier.NoModifier:
                    match event.key():
                        case QtCore.Qt.Key.Key_Escape:
                            self.set_editor_state(BOX_EDITOR_SCENE_STATE.SELECT)

    def keyReleaseEvent(self, event: QtGui.QKeyEvent) -> None:
        match event.key():
            case QtCore.Qt.Key.Key_Shift:
                self.set_editor_state(BOX_EDITOR_SCENE_STATE.SELECT)
        super().keyReleaseEvent(event)

    def set_page_as_background(self, page: Page):
        self.image = QtGui.QPixmap(page.image_path)
        self.setSceneRect(self.image.rect())
        # self.project.current_page_idx = page_number

    def drawBackground(self, painter, rect: Union[QtCore.QRectF, QtCore.QRect]) -> None:
        '''Draw background image for page'''

        if self.image:
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(self.backgroundBrush())
            painter.drawRect(rect)
            painter.drawPixmap(self.sceneRect(), self.image, QtCore.QRectF(self.image.rect()))

    def analyse_layout(self) -> None:
        analyse_layout_command = AnalyseLayoutCommand(self)
        self.undo_stack.push(analyse_layout_command)

    def modify_box(self, box: Box, properties: BoxData, last_pos: QtCore.QPointF):
        modify_box_command = ModifyBoxCommand(box, properties, last_pos)
        self.undo_stack.push(modify_box_command)


class AddBoxCommand(QtGui.QUndoCommand):
    def __init__(self, box_editor_scene: BoxEditorScene, rect: QtCore.QRectF, order: int):
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
        '''Analyse layout, excluding footer and header. Gets recognition boxes from OCR engine and creates boxes in editor accordingly.'''
        from_header = 0.0
        to_footer = 0.0

        if self.box_editor_scene.header_item:
            from_header = self.box_editor_scene.header_item.rect().bottom()
        if self.box_editor_scene.footer_item:
            to_footer = self.box_editor_scene.footer_item.rect().top()

        if self.box_editor_scene.image:
            block = self.box_editor_scene.engine_manager.get_current_engine().analyse_layout(self.box_editor_scene.image, int(from_header), int(to_footer))

            if block:
                ocr_result_blocks: list[OCRResultBlock] = block

                if ocr_result_blocks:
                    added_boxes = 0

                    for ocr_result_block in ocr_result_blocks:
                        if ocr_result_block.type is OCR_RESULT_BLOCK_TYPE.H_LINE or ocr_result_block.type is OCR_RESULT_BLOCK_TYPE.V_LINE:
                            #TODO: Not captured by undo/redo so far
                            self.box_editor_scene.addItem(QtWidgets.QGraphicsLineItem(QtCore.QLine(ocr_result_block.bbox_rect.topLeft(), ocr_result_block.bbox_rect.bottomRight())))
                        elif ocr_result_block.type != OCR_RESULT_BLOCK_TYPE.UNKNOWN:
                            new_box = self.box_editor_scene.add_box_(QtCore.QRectF(ocr_result_block.bbox_rect.topLeft(), ocr_result_block.bbox_rect.bottomRight()), added_boxes)
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
                        if item.collidingItems(QtCore.Qt.ItemSelectionMode.ContainsItemShape):
                            delete_items.append(item)

                for item in list(set(delete_items)):
                    if isinstance(item, Box):
                        self.box_editor_scene.removeItem(item)

                self.box_editor_scene.update_property_editor()

    def undo(self) -> None:
        for box in self.boxes:
            self.box_editor_scene.remove_box_(box)
