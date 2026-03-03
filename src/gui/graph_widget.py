"""
Inspector Rabbit - Network Graph Widget
Interactive force-directed graph visualization (Maltego-style)
"""

import math
import random
from typing import Dict, List, Optional, Tuple

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem,
    QGraphicsRectItem, QToolButton, QLineEdit, QApplication,
    QFileDialog, QMenu
)
from PyQt6.QtCore import (
    Qt, QTimer, QRectF, QPointF, QLineF, pyqtSignal, QPropertyAnimation
)
from PyQt6.QtGui import (
    QFont, QColor, QPen, QBrush, QPainter, QTransform,
    QLinearGradient, QRadialGradient, QPixmap, QKeySequence
)
from .components import apply_page_header_style


NODE_COLORS = {
    'username':  ('#a78bfa', '#2d1b69'),
    'domain':    ('#60a5fa', '#1e3a5f'),
    'email':     ('#34d399', '#0d3d29'),
    'ip':        ('#f87171', '#4a1515'),
    'social':    ('#fb923c', '#4a2a10'),
    'url':       ('#fbbf24', '#4a3a10'),
    'identity':  ('#f472b6', '#4a1a3a'),
    'phone':     ('#22d3ee', '#0a3540'),
    'default':   ('#8b949e', '#21262d'),
}

NODE_EMOJIS = {
    'username':  '👤',
    'domain':    '🌐',
    'email':     '✉️',
    'ip':        '🖥️',
    'social':    '📱',
    'url':       '🔗',
    'identity':  '🪪',
    'phone':     '📞',
    'default':   '●',
}


class GraphNode:
    def __init__(self, node_id: str, label: str, node_type: str = 'default',
                 x: float = 0.0, y: float = 0.0):
        self.id = node_id
        self.label = label
        self.node_type = node_type
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.fx: Optional[float] = None  # fixed position
        self.fy: Optional[float] = None
        self.data: Dict = {}
        self.selected = False

        # Graphics item (set after creation)
        self.graphics_item = None


class GraphEdge:
    def __init__(self, source_id: str, target_id: str, label: str = ""):
        self.source_id = source_id
        self.target_id = target_id
        self.label = label
        self.graphics_item = None


class NodeItem(QGraphicsItem):
    """Custom graphics item for a node"""
    RADIUS = 32

    def __init__(self, node: GraphNode):
        super().__init__()
        self.node = node
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self._hovered = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setZValue(2)

    def boundingRect(self) -> QRectF:
        r = self.RADIUS
        return QRectF(-r - 6, -r - 6, (r + 6) * 2, (r + 6) * 2 + 28)

    def paint(self, painter: QPainter, option, widget=None):
        node_type = self.node.node_type
        fg_color, bg_color = NODE_COLORS.get(node_type, NODE_COLORS['default'])
        r = self.RADIUS

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Glow effect when selected or hovered
        if self.isSelected() or self._hovered:
            glow = QRadialGradient(0, 0, r + 10)
            glow.setColorAt(0, QColor(fg_color + "44"))
            glow.setColorAt(1, QColor(fg_color + "00"))
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(-r - 10, -r - 10, (r + 10) * 2, (r + 10) * 2))

        # Background circle gradient
        grad = QRadialGradient(0, -r * 0.3, r * 1.2)
        grad.setColorAt(0, QColor(bg_color))
        grad.setColorAt(1, QColor("#0d1117"))
        painter.setBrush(QBrush(grad))

        # Border
        pen_color = fg_color if (self.isSelected() or self._hovered) else bg_color
        pen_width = 2.5 if self.isSelected() else 1.5
        painter.setPen(QPen(QColor(pen_color), pen_width))
        painter.drawEllipse(QRectF(-r, -r, r * 2, r * 2))

        # Emoji icon
        emoji = NODE_EMOJIS.get(node_type, '●')
        painter.setPen(QPen(QColor("#ffffff")))
        painter.setFont(QFont("Ubuntu", 16))
        painter.drawText(QRectF(-r, -r - 2, r * 2, r * 2),
                         Qt.AlignmentFlag.AlignCenter, emoji)

        # Label
        label = self.node.label
        lines = label.split('\n')
        painter.setFont(QFont("Ubuntu", 8, QFont.Weight.Bold))
        painter.setPen(QPen(QColor(fg_color)))
        y_offset = r + 8
        for line in lines[:2]:
            painter.drawText(
                QRectF(-r - 10, y_offset, (r + 10) * 2, 14),
                Qt.AlignmentFlag.AlignCenter, line[:25]
            )
            y_offset += 12

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.node.x = self.pos().x()
            self.node.y = self.pos().y()
        return super().itemChange(change, value)

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background: #1f2937; border: 1px solid #30363d; border-radius: 8px; padding: 4px; }
            QMenu::item { padding: 8px 20px; color: #c9d1d9; border-radius: 4px; }
            QMenu::item:selected { background: #1f6feb22; color: #00f5ff; }
        """)
        copy_lbl = menu.addAction(f"📋 Copy: {self.node.label[:30]}")
        open_url = menu.addAction("🌐 Open URL")
        pin_action = menu.addAction("📌 Pin Node")
        delete_action = menu.addAction("🗑️ Remove Node")

        action = menu.exec(event.screenPos())
        if action == copy_lbl:
            QApplication.clipboard().setText(self.node.label)
        elif action == delete_action:
            if self.scene():
                self.scene().removeItem(self)
        elif action == pin_action:
            self.node.fx = self.node.x
            self.node.fy = self.node.y


class EdgeItem(QGraphicsItem):
    """Custom graphics item for an edge"""

    def __init__(self, source_item: NodeItem, target_item: NodeItem, label: str = ""):
        super().__init__()
        self.source_item = source_item
        self.target_item = target_item
        self.label = label
        self.setZValue(1)

    def boundingRect(self) -> QRectF:
        p1 = self.source_item.pos()
        p2 = self.target_item.pos()
        x = min(p1.x(), p2.x()) - 10
        y = min(p1.y(), p2.y()) - 10
        w = abs(p2.x() - p1.x()) + 20
        h = abs(p2.y() - p1.y()) + 20
        return QRectF(x, y, max(w, 1), max(h, 1))

    def paint(self, painter: QPainter, option, widget=None):
        p1 = self.source_item.pos()
        p2 = self.target_item.pos()

        if p1 == p2:
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Edge line
        pen = QPen(QColor("#30363d"), 1.5, Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(p1, p2)

        # Arrow head
        angle = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
        arrow_size = 10
        mid = QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)
        p_arrow1 = QPointF(
            mid.x() - arrow_size * math.cos(angle - math.pi / 6),
            mid.y() - arrow_size * math.sin(angle - math.pi / 6)
        )
        p_arrow2 = QPointF(
            mid.x() - arrow_size * math.cos(angle + math.pi / 6),
            mid.y() - arrow_size * math.sin(angle + math.pi / 6)
        )
        painter.setPen(QPen(QColor("#444c56"), 1.5))
        painter.drawLine(mid, p_arrow1)
        painter.drawLine(mid, p_arrow2)

        # Edge label
        if self.label:
            painter.setFont(QFont("Ubuntu", 8))
            painter.setPen(QPen(QColor("#484f58")))
            lbl_pos = QPointF((p1.x() + p2.x()) / 2 + 6, (p1.y() + p2.y()) / 2 - 8)
            painter.drawText(lbl_pos, self.label[:20])

    def update_position(self):
        self.prepareGeometryChange()


class GraphScene(QGraphicsScene):
    node_selected = pyqtSignal(object)  # GraphNode

    def __init__(self, parent=None):
        super().__init__(parent)
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self._node_items: Dict[str, NodeItem] = {}
        self._edge_items: List[EdgeItem] = []

        # Force simulation
        self._sim_timer = QTimer()
        self._sim_timer.timeout.connect(self._simulate_step)
        self._sim_timer.setInterval(16)  # 60fps
        self._simulation_alpha = 1.0
        self._repulsion = 3000
        self._attraction = 0.08
        self._damping = 0.85

    def add_node(self, node_id: str, label: str, node_type: str = 'default',
                 data: dict = None) -> GraphNode:
        if node_id in self.nodes:
            return self.nodes[node_id]

        # Place near center with some randomness
        cx = random.uniform(-200, 200)
        cy = random.uniform(-200, 200)
        node = GraphNode(node_id, label, node_type, cx, cy)
        if data:
            node.data = data

        self.nodes[node_id] = node

        item = NodeItem(node)
        item.setPos(cx, cy)
        self.addItem(item)
        self._node_items[node_id] = item
        node.graphics_item = item

        self._restart_simulation()
        return node

    def add_edge(self, source_id: str, target_id: str, label: str = "") -> Optional[GraphEdge]:
        if source_id not in self.nodes or target_id not in self.nodes:
            return None

        # Avoid duplicates
        for e in self.edges:
            if e.source_id == source_id and e.target_id == target_id:
                return e

        edge = GraphEdge(source_id, target_id, label)
        self.edges.append(edge)

        src_item = self._node_items[source_id]
        tgt_item = self._node_items[target_id]
        edge_item = EdgeItem(src_item, tgt_item, label)
        self.addItem(edge_item)
        self._edge_items.append(edge_item)
        edge.graphics_item = edge_item

        return edge

    def remove_node(self, node_id: str):
        if node_id not in self.nodes:
            return
        item = self._node_items.pop(node_id)
        self.removeItem(item)
        del self.nodes[node_id]

        # Remove connected edges
        to_remove = [e for e in self.edges
                     if e.source_id == node_id or e.target_id == node_id]
        for edge in to_remove:
            if edge.graphics_item:
                self.removeItem(edge.graphics_item)
            self.edges.remove(edge)

    def clear_graph(self):
        super().clear()
        self.nodes.clear()
        self.edges.clear()
        self._node_items.clear()
        self._edge_items.clear()
        self._sim_timer.stop()

    def _restart_simulation(self, alpha: float = 0.8):
        self._simulation_alpha = alpha
        if not self._sim_timer.isActive():
            self._sim_timer.start()

    def _simulate_step(self):
        if self._simulation_alpha < 0.001:
            self._sim_timer.stop()
            return

        nodes = list(self.nodes.values())
        n = len(nodes)
        if n < 2:
            self._sim_timer.stop()
            return

        # Apply repulsion
        for i in range(n):
            ni = nodes[i]
            if ni.fx is not None:
                continue
            fx_total, fy_total = 0.0, 0.0

            for j in range(n):
                if i == j:
                    continue
                nj = nodes[j]
                dx = ni.x - nj.x
                dy = ni.y - nj.y
                dist = math.sqrt(dx * dx + dy * dy) + 0.1
                force = self._repulsion / (dist * dist)
                fx_total += (dx / dist) * force
                fy_total += (dy / dist) * force

            ni.vx = (ni.vx + fx_total) * self._damping
            ni.vy = (ni.vy + fy_total) * self._damping

        # Apply attraction along edges
        for edge in self.edges:
            src = self.nodes.get(edge.source_id)
            tgt = self.nodes.get(edge.target_id)
            if not src or not tgt:
                continue
            dx = tgt.x - src.x
            dy = tgt.y - src.y
            dist = math.sqrt(dx * dx + dy * dy) + 0.1
            force = dist * self._attraction

            if src.fx is None:
                src.vx += (dx / dist) * force
                src.vy += (dy / dist) * force
            if tgt.fx is None:
                tgt.vx -= (dx / dist) * force
                tgt.vy -= (dy / dist) * force

        # Update positions
        max_vel = 15.0 * self._simulation_alpha
        for node in nodes:
            if node.fx is not None:
                node.x = node.fx
                node.y = node.fy
            else:
                vel = math.sqrt(node.vx ** 2 + node.vy ** 2)
                if vel > max_vel:
                    node.vx = (node.vx / vel) * max_vel
                    node.vy = (node.vy / vel) * max_vel
                node.x += node.vx
                node.y += node.vy

            if node.graphics_item:
                node.graphics_item.setPos(node.x, node.y)

        # Update edges
        for edge_item in self._edge_items:
            edge_item.update_position()
            edge_item.update()

        self._simulation_alpha *= 0.97


class GraphView(QGraphicsView):
    def __init__(self, scene: GraphScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setBackgroundBrush(QBrush(QColor("#060c14")))
        self.setStyleSheet("border: none; border-radius: 8px;")
        self._zoom = 1.0

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom *= factor
        self._zoom = max(0.1, min(5.0, self._zoom))
        self.scale(factor, factor)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F:
            self.fitInView(self.scene().itemsBoundingRect(),
                           Qt.AspectRatioMode.KeepAspectRatio)
        elif event.key() == Qt.Key.Key_Plus:
            self.scale(1.2, 1.2)
        elif event.key() == Qt.Key.Key_Minus:
            self.scale(0.8, 0.8)
        else:
            super().keyPressEvent(event)


class GraphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Topbar
        bar = QFrame()
        apply_page_header_style(bar, "#f472b6")
        bar.setFixedHeight(64)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 12, 24, 12)
        bl.setSpacing(12)

        icon = QLabel("🕸️")
        icon.setFont(QFont("Ubuntu", 22))
        icon.setStyleSheet("border: none; background: transparent;")
        bl.addWidget(icon)

        vl = QVBoxLayout()
        t1 = QLabel("Network Graph")
        t1.setFont(QFont("Ubuntu", 15, QFont.Weight.Bold))
        t1.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        t2 = QLabel("Interactive force-directed relationship visualization")
        t2.setStyleSheet("color: #8b949e; font-size: 11px; border: none; background: transparent;")
        vl.addWidget(t1)
        vl.addWidget(t2)
        bl.addLayout(vl)
        bl.addStretch()

        # Controls
        for icon_text, tooltip, handler in [
            ("🎯", "Fit to screen [F]", self._fit_view),
            ("➕", "Zoom in [+]", self._zoom_in),
            ("➖", "Zoom out [-]", self._zoom_out),
            ("🔀", "Re-layout", self._relayout),
            ("🗑️", "Clear graph", self.clear_graph),
        ]:
            btn = QPushButton(icon_text)
            btn.setFixedSize(36, 36)
            btn.setToolTip(tooltip)
            btn.setStyleSheet("""
                QPushButton {
                    background: #161b22; border: 1px solid #21262d;
                    border-radius: 8px; font-size: 14px; color: #c9d1d9;
                }
                QPushButton:hover { background: #21262d; border-color: #00f5ff44; }
            """)
            btn.clicked.connect(handler)
            bl.addWidget(btn)

        export_btn = QPushButton("📷 Export PNG")
        export_btn.setFixedHeight(36)
        export_btn.setStyleSheet("""
            QPushButton {
                background: #161b22; border: 1px solid #21262d;
                border-radius: 8px; padding: 0 12px; color: #c9d1d9; font-size: 12px;
            }
            QPushButton:hover { background: #21262d; border-color: #00f5ff44; }
        """)
        export_btn.clicked.connect(self._export_image)
        bl.addWidget(export_btn)

        layout.addWidget(bar)

        # Stats bar
        stats_bar = QFrame()
        stats_bar.setStyleSheet("QFrame { background: #0a0f14; border-bottom: 1px solid #21262d; }")
        stats_bar.setFixedHeight(36)
        sl = QHBoxLayout(stats_bar)
        sl.setContentsMargins(24, 6, 24, 6)
        sl.setSpacing(24)

        self.node_count_lbl = QLabel("Nodes: 0")
        self.node_count_lbl.setStyleSheet("color: #8b949e; font-size: 11px; border: none; background: transparent;")
        sl.addWidget(self.node_count_lbl)

        self.edge_count_lbl = QLabel("Edges: 0")
        self.edge_count_lbl.setStyleSheet("color: #8b949e; font-size: 11px; border: none; background: transparent;")
        sl.addWidget(self.edge_count_lbl)

        sl.addStretch()

        # Legend
        for node_type, (color, _) in NODE_COLORS.items():
            if node_type == 'default':
                continue
            lbl = QLabel(f"{NODE_EMOJIS.get(node_type, '●')} {node_type.capitalize()}")
            lbl.setStyleSheet(f"color: {color}; font-size: 10px; border: none; background: transparent;")
            sl.addWidget(lbl)

        layout.addWidget(stats_bar)

        # Graph view
        self.scene = GraphScene()
        self.view = GraphView(self.scene)
        layout.addWidget(self.view, 1)

        # Empty state label
        _lbl = QLabel(
            "🕸️\n\nNo data in graph yet.\n\n"
            "Run OSINT modules and click\n'Send to Graph' to visualize\nrelationships here."
        )
        _lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _lbl.setStyleSheet("""
            QLabel {
                color: #21262d;
                font-size: 14px;
                border: none;
                background: transparent;
            }
        """)
        _lbl.setFont(QFont("Ubuntu", 13))
        self._empty_label = self.scene.addWidget(_lbl)
        self._empty_label.setPos(-150, -80)

    def add_data(self, data: dict):
        """Receive node data and add to graph"""
        node_id = data.get('id', data.get('label', 'unknown'))
        label = data.get('label', node_id)
        node_type = data.get('type', 'default')
        parent_id = data.get('parent')
        edge_label = data.get('edge_label', '')

        # Hide empty label (it's a QGraphicsProxyWidget)
        if self._empty_label is not None:
            self._empty_label.hide()

        node = self.scene.add_node(node_id, label, node_type, data)

        if parent_id and parent_id in self.scene.nodes:
            self.scene.add_edge(parent_id, node_id, edge_label)

        self._update_stats()

    def clear_graph(self):
        self.scene.clear_graph()
        _lbl = QLabel(
            "🕸️\n\nNo data in graph yet.\n\n"
            "Run OSINT modules and click\n'Send to Graph' to visualize\nrelationships here."
        )
        _lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _lbl.setStyleSheet("color: #21262d; font-size: 14px; border: none; background: transparent;")
        _lbl.setFont(QFont("Ubuntu", 13))
        self._empty_label = self.scene.addWidget(_lbl)
        self._empty_label.setPos(-150, -80)
        self._update_stats()

    def _update_stats(self):
        self.node_count_lbl.setText(f"Nodes: {len(self.scene.nodes)}")
        self.edge_count_lbl.setText(f"Edges: {len(self.scene.edges)}")

    def _fit_view(self):
        if self.scene.nodes:
            self.view.fitInView(
                self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50),
                Qt.AspectRatioMode.KeepAspectRatio
            )

    def _zoom_in(self):
        self.view.scale(1.2, 1.2)

    def _zoom_out(self):
        self.view.scale(0.8, 0.8)

    def _relayout(self):
        # Scatter nodes to restart simulation
        for node in self.scene.nodes.values():
            node.x = random.uniform(-300, 300)
            node.y = random.uniform(-300, 300)
            node.vx = 0
            node.vy = 0
            if node.graphics_item:
                node.graphics_item.setPos(node.x, node.y)
        self.scene._restart_simulation(alpha=1.0)

    def export_image(self, path: str = None):
        if not path:
            path, _ = QFileDialog.getSaveFileName(
                self, "Export Graph", "graph.png", "PNG (*.png)"
            )
        if path:
            rect = self.scene.itemsBoundingRect().adjusted(-40, -40, 40, 40)
            pixmap = QPixmap(int(rect.width()), int(rect.height()))
            pixmap.fill(QColor("#060c14"))
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.scene.render(painter, source=rect)
            painter.end()
            pixmap.save(path)

    def _export_image(self):
        self.export_image()
