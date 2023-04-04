import copy
import math
from dataclasses import dataclass

import cv2
import numpy
from PySide6 import QtCore, QtGui, QtWidgets

from box_editor.box_data import BOX_DATA_TYPE, BoxData


@dataclass
class BoxColor():
    '''Color properties to represent different box types'''
    brush: QtGui.QBrush = QtGui.QBrush()
    pen: QtGui.QPen = QtGui.QPen()
    brush_selected: QtGui.QBrush = QtGui.QBrush()
    pen_selected: QtGui.QPen = QtGui.QPen()


class Box(QtWidgets.QGraphicsRectItem):
    text_recognized = QtCore.Signal(str)

    def __init__(self, rect: QtCore.QRectF, engine_manager, scene) -> None:
        super().__init__(rect, parent=None)

        self.engine_manager = engine_manager
        self.custom_scene = scene

        self.move_edges = False

        # Setup order number for painting
        self.number_widget = QtWidgets.QGraphicsSimpleTextItem(self)
        self.number_widget.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)

        # Setup recognition checkmark symbol for painting
        checkmark = QtGui.QPixmap('resources/icons/check-line.png').scaledToWidth(16, QtCore.Qt.TransformationMode.SmoothTransformation)
        self.recognized_widget = QtWidgets.QGraphicsPixmapItem(checkmark, self)
        self.recognized_widget.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.recognized_widget.hide()

        self.setAcceptHoverEvents(True)

        self.setFlags(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsFocusable)

        self.properties = BoxData()
        self.properties.language = self.scene().project.default_language

        self.setRect(rect)
        self.updateProperties()

        # Define colors for different box types

        # Text box

        brush_text = QtGui.QBrush(QtGui.QColor(94, 156, 235, 150))
        brush_text.setStyle(QtCore.Qt.BrushStyle.SolidPattern)

        brush_text_selected = brush_text

        pen_text = QtGui.QPen(QtGui.QColor(94, 156, 235, 150))
        pen_text.setWidth(2)
        pen_text.setStyle(QtCore.Qt.PenStyle.SolidLine)
        pen_text.setCosmetic(False)

        pen_text_selected = pen_text
        pen_text_selected = QtGui.QPen(QtGui.QColor(94, 156, 235, 255))
        pen_text_selected.setWidth(3)

        self.color_text = BoxColor(brush_text, pen_text, brush_text_selected, pen_text_selected)

        # Image box

        brush_image = brush_text
        brush_image = QtGui.QBrush(QtGui.QColor(227, 35, 35, 150))

        brush_image_selected = brush_image

        pen_image = pen_text
        pen_image = QtGui.QPen(QtGui.QColor(227, 35, 35, 150))

        pen_image_selected = pen_image
        pen_image_selected = QtGui.QPen(QtGui.QColor(227, 35, 35, 255))

        self.color_image = BoxColor(brush_image, pen_image, brush_image_selected, pen_image_selected)

        # Disabled box

        brush_disabled = brush_text
        brush_disabled = QtGui.QBrush(QtGui.QColor(35, 35, 35, 150))

        brush_disabled_selected = brush_disabled

        pen_disabled = pen_text
        pen_disabled = QtGui.QPen(QtGui.QColor(35, 35, 35, 150))

        pen_disabled_selected = pen_disabled
        pen_disabled_selected = QtGui.QPen(QtGui.QColor(35, 35, 35, 255))

        self.color_disabled = BoxColor(brush_disabled, pen_disabled, brush_disabled_selected, pen_disabled_selected)

        self.top_touched = False
        self.right_touched = False
        self.bottom_touched = False
        self.left_touched = False

        # Last position before drag
        self.last_pos: QtCore.QPointF = QtCore.QPointF()

    def scene(self):
        return self.custom_scene

    def updateProperties(self, undo: bool = False) -> None:
        '''Update properties with current box position'''
        new_rect = QtCore.QRectF(self.mapToScene(self.rect().topLeft()), self.mapToScene(self.rect().bottomRight())).toAlignedRect()
        # Check for actual position changes
        if self.rect() != new_rect:
            if undo:
                properties = copy.copy(self.properties)
                properties.rect = new_rect
                self.scene().modify_box(self, properties, self.last_pos)
            else:
                self.properties.rect = new_rect

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget: QtWidgets.QWidget) -> None:
        '''Paint background and border using colors defined by type and update order number item'''
        color = BoxColor()

        if self.properties.export_enabled:
            if self.properties.type is BOX_DATA_TYPE.TEXT:
                color = self.color_text
            else:
                color = self.color_image
        else:
            color = self.color_disabled

        if self.isSelected():
            painter.setPen(color.pen_selected)
            painter.setBrush(color.brush_selected)
        else:
            painter.setPen(color.pen)
            painter.setBrush(color.brush)

        painter.drawRect(self.rect())

        # TODO: Position not working correctly with ItemIgnoresTransformations
        # Update ordner number
        self.number_widget.setText(str(self.properties.order + 1))

        pos = self.rect().bottomLeft()
        pos.setX(pos.x() + 5)
        pos.setY(pos.y() - self.number_widget.boundingRect().height() - 10)
        br = self.mapToScene(pos)
        self.number_widget.setPos(self.mapFromScene(br))

        # Update recognition checkmark
        if self.properties.recognized:
            pos = self.rect().bottomLeft()
            pos.setX(pos.x() + self.number_widget.boundingRect().width() + 5)
            pos.setY(pos.y() - self.recognized_widget.boundingRect().height() - 10)
            br = self.mapToScene(pos)
            self.recognized_widget.setPos(self.mapFromScene(br))
            self.recognized_widget.show()
        else:
            self.recognized_widget.hide()

        #TODO: Set in options
        confidence_threshold = 90

        # Word confidence visualisation
        if self.properties.words:
            for word in self.properties.words:
                if word.confidence < confidence_threshold:
                    painter.setPen(QtGui.QPen(QtGui.QColor(255, 0, 0, int(1 - (word.confidence / 100)) * 200), 2, QtCore.Qt.PenStyle.DotLine))
                    #painter.setBrush(QtGui.QColor(255, 0, 0, int(1 - (word.confidence / 100)) * 200))
                    painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
                    adjust_by = 2
                    painter.drawRect(word.bbox_rect.adjusted(-adjust_by, -adjust_by, adjust_by, adjust_by))

        # Paragraphs
        if self.properties.ocr_result_block:
            paragraphs = self.properties.ocr_result_block.paragraphs
            if paragraphs:
                if len(paragraphs) > 1:
                    for p, paragraph in enumerate(self.properties.ocr_result_block.paragraphs):
                        if p > 0:
                            painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 150), 0, QtCore.Qt.PenStyle.SolidLine))
                            painter.drawLine(paragraph.bbox_rect.topLeft(), paragraph.bbox_rect.topRight())

    def hoverMoveEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        '''Show size grips at the box' margin'''
        self.top_touched = False
        self.right_touched = False
        self.bottom_touched = False
        self.left_touched = False

        # cursor = QtGui.QCursor(QtGui.Qt.CursorShape.ArrowCursor)
        cursor = None

        if math.isclose(event.pos().x(), self.rect().x(), rel_tol=0.01):
            self.left_touched = True
        if math.isclose(event.pos().x(), self.rect().x() + self.rect().width(), rel_tol=0.01):
            self.right_touched = True
        if math.isclose(event.pos().y(), self.rect().y(), rel_tol=0.01):
            self.top_touched = True
        if math.isclose(event.pos().y(), self.rect().y() + self.rect().height(), rel_tol=0.01):
            self.bottom_touched = True

        if self.top_touched or self.bottom_touched:
            cursor = QtGui.QCursor(QtGui.Qt.CursorShape.SizeVerCursor)
        if self.left_touched or self.right_touched:
            cursor = QtGui.QCursor(QtGui.Qt.CursorShape.SizeHorCursor)

        if self.top_touched and self.right_touched or self.bottom_touched and self.left_touched:
            cursor = QtGui.QCursor(QtGui.Qt.CursorShape.SizeBDiagCursor)
        if self.top_touched and self.left_touched or self.bottom_touched and self.right_touched:
            cursor = QtGui.QCursor(QtGui.Qt.CursorShape.SizeFDiagCursor)

        if cursor:
            QtWidgets.QApplication.setOverrideCursor(cursor)
        else:
            QtWidgets.QApplication.restoreOverrideCursor()

        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        QtWidgets.QApplication.changeOverrideCursor(QtGui.Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        '''Handle scaling via mouse'''
        if self.move_edges:
            self.scene().clearSelection()
            self.setSelected(True)
            self.prepareGeometryChange()
            pos = event.pos().toPoint()

            rect = self.rect()

            # TODO: right < left / bottom < top not possible
            if self.left_touched:
                rect.setLeft(pos.x())
            if self.right_touched:
                rect.setRight(pos.x())
            if self.top_touched:
                rect.setTop(pos.y())
            if self.bottom_touched:
                rect.setBottom(pos.y())

            self.setRect(rect.normalized())
            self.update()
            self.updateProperties()
        else:
            super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        match event.modifiers():
            case QtCore.Qt.KeyboardModifier.NoModifier:
                if event.buttons() == QtCore.Qt.MouseButton.LeftButton:
                    if self.left_touched or self.right_touched or self.top_touched or self.bottom_touched:
                        self.move_edges = True
                    else:
                        self.last_pos = self.pos()
                        super().mousePressEvent(event)
            case QtCore.Qt.KeyboardModifier.ControlModifier:
                if event.buttons() == QtCore.Qt.MouseButton.LeftButton:
                    event.ignore()

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        self.move_edges = False
        self.updateProperties(True)
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event: QtWidgets.QGraphicsSceneContextMenuEvent) -> None:
        self.menu = QtWidgets.QMenu()

        text_action = QtGui.QAction('Text')
        text_action.triggered.connect(self.set_type_to_text)

        self.menu.addAction(text_action)

        image_action = QtGui.QAction('Image')
        image_action.triggered.connect(self.set_type_to_image)

        self.menu.addAction(image_action)

        if self.properties.type is BOX_DATA_TYPE.TEXT:
            read_action = QtGui.QAction('Read')
            read_action.triggered.connect(self.recognize_text)
            self.menu.addAction(read_action)

            read_action_raw = QtGui.QAction('Read raw')
            read_action_raw.triggered.connect(self.recognize_text_raw)
            self.menu.addAction(read_action_raw)

            auto_align_action = QtGui.QAction('Auto align')
            auto_align_action.triggered.connect(self.auto_align)
            self.menu.addAction(auto_align_action)

        self.menu.exec(event.screenPos())

    def auto_align(self) -> None:
        '''Automatically align box to content'''

        new_rect = self.rect()

        if self.type is BOX_DATA_TYPE.TEXT:
            pass
        else:
            image = self.get_image().toImage().copy()

            # TODO: Works for now but a bit dirty, investigate further
            img = numpy.array(image.bits()).reshape((image.height(), image.width(), 4))

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            thresh_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)[1]

            # Blur the image
            blur = cv2.GaussianBlur(thresh_inv, (1, 1), 0)

            thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]

            # find contours
            contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]

            # mask = numpy.ones(img.shape[:2], dtype="uint8") * 255

            for c in contours:
                # get the bounding rect
                x, y, w, h = cv2.boundingRect(c)
                # rect = QtCore.QRectF(x, y, w, h)

                new_rect = self.rect().translated(QtCore.QPointF(x, y))
                new_rect.setWidth(w)
                new_rect.setHeight(h)

        self.setRect(new_rect)
        self.update()

        #     if w*h>1000:
        #         cv2.rectangle(mask, (x, y), (x+w, y+h), (0, 0, 255), -1)

        # res_final = cv2.bitwise_and(img, img, mask=cv2.bitwise_not(mask))

        # cv2.imshow("boxes", mask)
        # # cv2.imshow('test', gray)
        # cv2.imshow("final image", res_final)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        # engine = self.engine_manager.get_current_engine()

        # block = engine.read(self.get_image(), self.properties.language)

        # if block:
        #     final_rect = QtCore.QRect(self.properties.rect.x() + block.bbox.x(), self.properties.rect.y() + block.bbox.y(), block.bbox.width(), block.bbox.height())
        #     self.properties.rect = final_rect
        #     self.setRect(final_rect)
        #     self.properties.recognized = True

        # self.scene_.update_property_editor()
        # self.update()
        pass

    def recognize_text(self) -> None:
        '''Delegate recognition to scene in case new boxes are detected'''
        if self.properties.recognized:
            button = QtWidgets.QMessageBox.question(self.scene().parent(), self.scene().tr('Recognize again?', 'dialog_recognize_again_title'),
                                                    self.scene().tr('Text recognition has already been run for box {}. Run again?'.format(self.properties.order + 1), 'dialog_recognize_again'))

            if button == QtWidgets.QMessageBox.StandardButton.Yes:
                self.scene().recognize_box(self)
        else:
            self.scene().recognize_box(self)

    def recognize_text_raw(self) -> None:
        '''Delegate recognition to scene in case new boxes are detected'''
        if self.properties.recognized:
            button = QtWidgets.QMessageBox.question(self.scene().parent(), self.scene().tr('Recognize again?', 'dialog_recognize_again_title'),
                                                    self.scene().tr('Text recognition has already been run for box {}. Run again?'.format(self.properties.order + 1), 'dialog_recognize_again'))

            if button == QtWidgets.QMessageBox.StandardButton.Yes:
                self.scene().recognize_box(self, True)
        else:
            self.scene().recognize_box(self, True)

    def get_image(self) -> QtGui.QPixmap:
        '''Return part of the image within selection'''
        image: QtGui.QPixmap = self.scene().image
        return image.copy(self.properties.rect)

    def set_type_to_text(self) -> None:
        self.properties.type = BOX_DATA_TYPE.TEXT
        self.update()

    def set_type_to_image(self) -> None:
        self.properties.type = BOX_DATA_TYPE.IMAGE
        self.update()
