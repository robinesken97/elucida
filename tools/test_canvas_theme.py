"""Display inversion must not change export bytes or the source pixmap."""
import os,sys,io
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
os.environ['ELUCIDA_OCTET']='1'
from PySide6.QtWidgets import QApplication,QWidget,QLabel,QVBoxLayout
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt,QPoint
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from elucida.app.canvas_theme import register,configure
app=QApplication([]);root=QWidget();layout=QVBoxLayout(root)
figure=Figure(figsize=(3,2));ax=figure.subplots();ax.plot([0,1],[0,1],color='blue')
canvas=register(FigureCanvasQTAgg(figure));layout.addWidget(canvas)
label=register(QLabel());label.setAlignment(Qt.AlignCenter);pixmap=QPixmap(100,100);pixmap.fill('white');label.setPixmap(pixmap);layout.addWidget(label)
def export():
 b=io.BytesIO();figure.savefig(b,format='png');return b.getvalue()
root.show();app.processEvents();normal=export();configure(True);app.processEvents()
point=label.mapTo(root,label.rect().center());screen=root.grab().toImage()
assert screen.pixelColor(point.x(),point.y()).name()=='#000000'
plot_point=canvas.mapTo(root,QPoint(5,5))
assert screen.pixelColor(plot_point.x(),plot_point.y()).name()=='#000000', 'plot background must be pure black'
assert label.pixmap().toImage().pixelColor(50,50).name()=='#ffffff'
assert normal==export(),'display inversion changed matplotlib export'
configure(False);app.processEvents();assert root.grab().toImage().pixelColor(point.x(),point.y()).name()=='#ffffff'
print('OK: pure black canvas, source image unchanged, PNG export byte-identical')
root.close()
