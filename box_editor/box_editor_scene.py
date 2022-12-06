from enum import Enum, auto

import cv2
import numpy
from iso639 import Lang
from ocr_engine import OCREngineManager
from odf import style
from odf import text as odftext
from odf.opendocument import OpenDocumentText
from odf.text import P
from project import Page, Project
from PySide6 import QtCore, QtGui, QtWidgets

from box_editor.box import Box
from box_editor.box_data import BoxData


class BoxEditorView(QtWidgets.QGraphicsView):
    def __init__(self, parent, engine_manager: OCREngineManager, property_editor, project: Project) -> None:
        super().__init__(parent)

        self.project = project
        self.property_editor = property_editor
        self.current_page = None
        self.custom_scene = BoxEditorScene(self, engine_manager, self.property_editor, self.project, None)
        self.setScene(self.custom_scene)
        self.origin = QtCore.QPoint()
        self.current_scale = 1.0

        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform | QtGui.QPainter.TextAntialiasing)
        self.setDisabled(True)

        # Enable so we get mouse move events
        self.setMouseTracking(True)

    # def cleanup(self):
    #     self.project = None
    #     self.current_page = None
    #     self.current_scale = 1.0
    #     self.scene().cleanup()
    #     self.setDisabled(True)

    def load_page(self, page: Page):
        self.scene().clear()
        self.scene().box_counter = 0
        self.scene().header_item = None
        self.scene().footer_item = None
        # self.scene().current_box = None
        self.scene().set_page_as_background(page)

        self.setEnabled(True)
        self.current_page = page
        self.scene().current_page = self.current_page

        for box_data in page.box_datas:
            # Restore existing boxes for this page
            self.scene().restore_box(box_data)

        # Restore header and footer box
        if self.project:
            if self.project.header_y:
                self.scene().add_header_footer(HEADER_FOOTER_ITEM_TYPE.HEADER, self.project.header_y)
            if self.project.footer_y:
                self.scene().add_header_footer(HEADER_FOOTER_ITEM_TYPE.FOOTER, self.project.footer_y)

        # TODO: Check if there’s a way to avoid checking current_box to find out if box is currently being resized
        self.scene().current_box = None

        self.property_editor.box_widget.reset()
        # self.property_editor.box_widget

        # self.scene().focus

    def scene(self):
        return self.custom_scene

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        '''Handle zooming and scrolling by mouse'''

        if event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier:
            scaleFactor = 1.02
            degrees = event.angleDelta().y()
            if degrees > 0:
                self.current_scale *= scaleFactor
            else:
                self.current_scale /= scaleFactor

            self.resetTransform()
            self.scale(self.current_scale, self.current_scale)
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        '''Setup movement by mouse'''
        if event.buttons() == QtCore.Qt.MiddleButton:
            self.origin = event.pos()
        elif event.buttons() == QtCore.Qt.RightButton:
            self.setDragMode(QtWidgets.QGraphicsView.DragMode.RubberBandDrag)

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.buttons() == QtCore.Qt.RightButton:
            self.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)
            self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.DefaultContextMenu)
        return super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        '''Handle movement by mouse'''
        oldPoint = self.mapToScene(self.origin)
        newPoint = self.mapToScene(event.pos())
        translation = newPoint - oldPoint

        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)
        if event.buttons() == QtCore.Qt.RightButton:
            pass
        if event.buttons() == QtCore.Qt.MiddleButton:
            self.translate(translation.x(), translation.y())

        self.origin = event.pos()

        super().mouseMoveEvent(event)

    # def get_boxes(self, only_selected: bool = False) -> list:
    #     boxes = []

    #     for item in self.scene().items():
    #         if isinstance(item, Box):
    #             if only_selected:
    #                 if item in self.scene().selectedItems():
    #                     boxes.append(item)
    #             else:
    #                 boxes.append(item)

    #     boxes.sort(key=lambda x: x.properties.order)
    #     return boxes

    def pixmap_to_cv2(self, pixmap: QtGui.QPixmap):
        image = pixmap.toImage().copy()

        # TODO: Works for now but a bit dirty, investigate further
        return numpy.array(image.bits()).reshape((image.height(), image.width(), 4))

    def analyze_layout(self) -> list:
        # TODO: Check for actual page
        new_boxes = []
        if self.scene().image:
            image = self.pixmap_to_cv2(self.scene().image)

            # ret1, th1 = cv2.threshold(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
            ret1, th1 = cv2.threshold(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 100, 255, cv2.THRESH_BINARY_INV)

            kernel = numpy.ones((5, 5), 'uint8')
            margin_img = cv2.dilate(th1, kernel, iterations=5)

            # cv2.imshow("test", margin_img)

            (contours, _) = cv2.findContours(margin_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in reversed(contours):
                x, y, w, h = cv2.boundingRect(cnt)

                box = QtCore.QRectF(x, y, w, h)

                new_boxes.append(self.scene().add_box(box))
                self.scene().current_box = None
        return new_boxes


class HEADER_FOOTER_ITEM_TYPE(Enum):
    HEADER = auto()
    FOOTER = auto()


class HeaderFooterItem(QtWidgets.QGraphicsRectItem):
    def __init__(self, type: HEADER_FOOTER_ITEM_TYPE, page_size: QtCore.QSizeF, y: float):
        super().__init__()

        rect = QtCore.QRectF()

        rect.setX(0)
        rect.setWidth(page_size.width())

        if type == HEADER_FOOTER_ITEM_TYPE.HEADER:
            title = 'Header'
            rect.setBottom(y)
        else:
            title = 'Footer'
            rect.setTop(y)
            rect.setBottom(page_size.height())

        self.setRect(rect)

        brush = QtGui.QBrush(QtGui.QColor(128, 0, 200, 150))
        brush.setStyle(QtCore.Qt.BDiagPattern)

        self.setPen(QtCore.Qt.NoPen)
        self.setBrush(brush)

        pen = QtGui.QPen(QtGui.QColor(128, 0, 200, 150))
        pen.setWidth(1)
        pen.setStyle(QtCore.Qt.SolidLine)
        pen.setCosmetic(True)

        self.title = QtWidgets.QGraphicsSimpleTextItem(self)
        self.title.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)
        self.title.setPen(pen)
        self.title.setText(title)

        self.line = QtWidgets.QGraphicsLineItem(self)
        self.line.setPen(QtGui.QPen(QtGui.QColor(128, 0, 200, 200), 3, QtCore.Qt.SolidLine))
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
    IDLE = auto()
    DRAW_BOX = auto()
    PLACE_HEADER = auto()
    PLACE_FOOTER = auto()


class BoxEditorScene(QtWidgets.QGraphicsScene):
    def __init__(self, parent, engine_manager: OCREngineManager, property_editor, project: Project, page: Page) -> None:
        super().__init__(parent)
        self.current_box = None
        self.header_item = None
        self.footer_item = None

        self.project = project
        self.current_page = page
        self.image = QtGui.QPixmap()
        # self.set_page_as_background(0)
        self.engine_manager = engine_manager
        self.box_counter = 0

        self.property_editor = property_editor

        # Setup connection to and from property editor
        self.selectionChanged.connect(self.update_property_editor)
        self.property_editor.box_widget.text_edit.editingFinished.connect(self.update_text)
        self.property_editor.box_widget.tag_edit.editingFinished.connect(self.update_tag)
        self.property_editor.box_widget.class_str_edit.editingFinished.connect(self.update_class_str)
        self.property_editor.box_widget.language_combo.currentTextChanged.connect(self.update_language)

        self.state = BOX_EDITOR_SCENE_STATE.IDLE

    def selectedItems(self) -> list[Box]:
        items = super().selectedItems()

        boxes = []

        for item in items:
            if isinstance(item, Box):
                boxes.append(item)
        return boxes

    def items(self, order=False) -> list[Box]:
        items = super().items()

        items_boxes = []

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

    def update_text(self) -> None:
        if len(self.selectedItems()) > 1:
            button = QtWidgets.QMessageBox.question(self.parent(), self.tr('Edit text of multiple boxes?', 'dialog_multiple_boxes_edit_title'), self.tr(
                'Multiple boxes are currently selected, do you want to set the current text for all selected box?', 'dialog_multiple_boxes_edit'))

            if button == QtWidgets.QMessageBox.No:
                return
        for item in self.selectedItems():
            item.properties.text = self.property_editor.box_widget.text_edit.document()
            self.update_property_editor()

    def update_tag(self) -> None:
        for item in self.selectedItems():
            item.properties.tag = self.property_editor.box_widget.tag_edit.text()

    def update_class_str(self) -> None:
        for item in self.selectedItems():
            item.properties.class_str = self.property_editor.box_widget.class_str_edit.text()

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

        self.current_box = Box(rect, self.engine_manager, self)
        if self.current_page:
            self.current_page.box_datas.append(self.current_box.properties)
        self.current_box.properties.order = order

        self.addItem(self.current_box)

        if order >= 0:
            self.shift_ordering(self.current_box, 1)
        else:
            self.current_box.properties.order = self.box_counter
        self.box_counter += 1
        return self.current_box

    def restore_box(self, box_datas: BoxData) -> Box:
        '''Restore a box in the editor using box properties stored in the project'''
        self.current_box = Box(QtCore.QRectF(box_datas.rect), self.engine_manager, self)
        self.current_box.properties = box_datas
        self.box_counter += 1
        self.addItem(self.current_box)
        return self.current_box

    def remove_box(self, box: Box) -> None:
        '''Remove a box from the editor window and project'''
        self.removeItem(box)
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

        remove_hyphens = False

        # TODO: Implement an option for this
        if box.properties.language == Lang('German'):
            remove_hyphens = True

        blocks = engine.recognize(box.get_image(), self.current_page.px_per_mm, box.properties.language, raw)

        is_image = False

        if isinstance(blocks, list):
            if raw:
                box.properties.ocr_result_block = blocks[0]
                box.properties.text = blocks[0].get_text(False)
                box.properties.recognized = True
            else:
                if len(blocks) == 1:
                    block = blocks[0]

                    if block.get_avg_confidence() > 30:
                        box.properties.ocr_result_block = block
                        box.properties.words = block.get_words()
                        box.properties.text = block.get_text(True, remove_hyphens)
                        box.properties.recognized = True
                    else:
                        is_image = True
                elif len(blocks) > 1:
                    new_boxes = []

                    # Multiple text blocks have been recognized within the selection, replace original box with new boxes

                    # Remove original box
                    self.remove_box(box)

                    added_boxes = 0

                    for block in blocks:
                        # Skip blocks with bad confidence (might be an image)
                        # TODO: Find a good threshold
                        if block.get_avg_confidence() > 30:

                            # Add new blocks at the recognized positions and adjust child elements
                            new_box = self.add_box(QtCore.QRectF(block.bbox.translated(box.rect().topLeft().toPoint())), box.properties.order + added_boxes)
                            dist = box.rect().topLeft() - new_box.rect().topLeft()
                            new_box.properties.ocr_result_block = block

                            # Move paragraph lines and word boxes accordingly
                            new_box.properties.ocr_result_block.translate(dist.toPoint())

                            new_box.properties.words = new_box.properties.ocr_result_block.get_words()
                            new_box.properties.text = new_box.properties.ocr_result_block.get_text(True, remove_hyphens)

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
            box.set_type_to_image()

        box.update()
        self.update_property_editor()

    def get_mouse_position(self) -> QtCore.QPointF:
        mouse_origin = self.views()[0].mapFromGlobal(QtGui.QCursor.pos())
        return self.views()[0].mapToScene(mouse_origin)

    def add_header_footer(self, type: HEADER_FOOTER_ITEM_TYPE, y: float):
        if type == HEADER_FOOTER_ITEM_TYPE.HEADER:
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

        if type == HEADER_FOOTER_ITEM_TYPE.HEADER:
            self.header_item = item
            if self.project:
                self.project.header_y = y
        else:
            self.footer_item = item
            if self.project:
                self.project.footer_y = y

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        '''Handle adding new box by mouse'''
        if self.state == BOX_EDITOR_SCENE_STATE.IDLE:
            if not self.itemAt(event.scenePos(), QtGui.QTransform()):
                if event.buttons() == QtCore.Qt.LeftButton:
                    if not self.current_box:
                        rect = QtCore.QRectF()
                        rect.setTopLeft(event.scenePos())
                        rect.setBottomRight(event.scenePos())

                        self.add_box(rect)

                        self.state = BOX_EDITOR_SCENE_STATE.DRAW_BOX
        elif self.state == BOX_EDITOR_SCENE_STATE.PLACE_HEADER:
            if self.header_item:
                if self.project:
                    self.project.header_y = self.header_item.rect().bottom()
            self.state = BOX_EDITOR_SCENE_STATE.IDLE
        elif self.state == BOX_EDITOR_SCENE_STATE.PLACE_FOOTER:
            if self.footer_item:
                if self.project:
                    self.project.footer_y = self.footer_item.rect().top()
            self.state = BOX_EDITOR_SCENE_STATE.IDLE

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        if self.state == BOX_EDITOR_SCENE_STATE.DRAW_BOX:
            if event.buttons() == QtCore.Qt.LeftButton:
                if self.current_box:
                    rect = self.current_box.rect()
                    rect.setBottomRight(event.scenePos())
                    self.current_box.setRect(rect)
        elif self.state == BOX_EDITOR_SCENE_STATE.PLACE_HEADER:
            if self.header_item:
                self.header_item.update_bottom_position(event.scenePos().y())
        elif self.state == BOX_EDITOR_SCENE_STATE.PLACE_FOOTER:
            if self.footer_item:
                self.footer_item.update_top_position(event.scenePos().y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        '''Commit changes after drawing box or remove if too small'''
        if self.state == BOX_EDITOR_SCENE_STATE.DRAW_BOX:
            if self.current_box:
                corner = self.current_box.rect().topLeft()
                if (event.scenePos().x() - corner.x()) > 10 and (event.scenePos().y() - corner.y()) > 10:
                    self.current_box.updateProperties()
                    self.current_box.setSelected(True)
                    self.current_box.setFocus()
                else:
                    self.remove_box(self.current_box)
            self.current_box = None
        self.state = BOX_EDITOR_SCENE_STATE.IDLE
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        # Get selected boxes:
        boxes = self.selectedItems()

        # Sort by order number
        boxes.sort(key=lambda x: x.properties.order)

        if self.state == BOX_EDITOR_SCENE_STATE.IDLE:
            if event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier:
                match event.key():
                    case QtCore.Qt.Key_A:
                        for box in self.items():
                            box.setSelected(True)
                    case _:
                        super().keyPressEvent(event)

            if event.modifiers() == QtCore.Qt.KeyboardModifier.NoModifier:
                match event.key():
                    case QtCore.Qt.Key_A:
                        for box in boxes:
                            box.auto_align()
                    case QtCore.Qt.Key_I:
                        for box in boxes:
                            box.set_type_to_image()
                    case QtCore.Qt.Key_T:
                        for box in boxes:
                            box.set_type_to_text()
                    case QtCore.Qt.Key_R:
                        for box in boxes:
                            box.recognize_text()
                    case QtCore.Qt.Key_Delete:
                        for box in boxes:
                            self.remove_box(box)
                    case QtCore.Qt.Key_H:
                        self.add_header_footer(HEADER_FOOTER_ITEM_TYPE.HEADER, self.get_mouse_position().y())
                        self.state = BOX_EDITOR_SCENE_STATE.PLACE_HEADER
                    case QtCore.Qt.Key_F:
                        self.add_header_footer(HEADER_FOOTER_ITEM_TYPE.FOOTER, self.get_mouse_position().y())
                        self.state = BOX_EDITOR_SCENE_STATE.PLACE_FOOTER
                    case QtCore.Qt.Key_D:
                        for box in boxes:
                            self.toggle_export_enabled(box)
                    case _:
                        super().keyPressEvent(event)
        else:
            # TODO: enable canceling actions
            if event.modifiers() == QtCore.Qt.KeyboardModifier.NoModifier:
                match event.key():
                    case QtCore.Qt.Key_Escape:
                        self.state = BOX_EDITOR_SCENE_STATE.IDLE

    def set_page_as_background(self, page: Page):
        self.image = QtGui.QPixmap(page.image_path)
        self.setSceneRect(self.image.rect())
        # self.project.current_page_idx = page_number

    def drawBackground(self, painter, rect: QtCore.QRectF) -> None:
        '''Setup background image for page'''
        if self.image:
            painter.drawPixmap(self.sceneRect(), self.image, QtCore.QRectF(self.image.rect()))
