import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.widgets import Button
import tkinter as tk
from tkinter import simpledialog
from model import Region, MapAnnotation
import uuid


class Editor:
    def __init__(self, annotation: MapAnnotation):
        self.annotation = annotation
        self.current_vertices = []  # vertices being drawn right now
        self.patch_map = {}  # region.id -> matplotlib patch
        self.selected_region = None

        self.fig, self.ax = plt.subplots(1, 1, figsize=(12, 9))
        img = mpimg.imread(annotation.image_path)
        self.ax.imshow(img)
        self.ax.set_title(
            "Left-click: add vertex | Right-click: close polygon | Middle-click: select region"
        )

        # Draw any pre-existing regions
        for region in self.annotation.regions:
            self._draw_region(region)

        # Buttons
        ax_del = self.fig.add_axes([0.8, 0.01, 0.09, 0.04])
        ax_save = self.fig.add_axes([0.9, 0.01, 0.09, 0.04])
        self.btn_del = Button(ax_del, "Delete")
        self.btn_save = Button(ax_save, "Save")
        self.btn_del.on_clicked(self._on_delete)
        self.btn_save.on_clicked(lambda _: None)  # wired externally
        self._save_callback = None

        self.fig.canvas.mpl_connect("button_press_event", self._on_click)

    # ---- drawing helpers ----
    def _draw_region(self, region: Region):
        color = "cyan" if region == self.selected_region else "yellow"
        patch = MplPolygon(
            region.vertices,
            closed=True,
            fill=True,
            alpha=0.3,
            edgecolor=color,
            linewidth=2,
            facecolor=color,
        )
        self.ax.add_patch(patch)
        cx = sum(v[0] for v in region.vertices) / len(region.vertices)
        cy = sum(v[1] for v in region.vertices) / len(region.vertices)
        self.ax.text(
            cx,
            cy,
            f"{region.label}\n{region.id[:8]}",
            ha="center",
            va="center",
            fontsize=7,
            color="black",
            weight="bold",
        )
        self.patch_map[region.id] = patch

    def _redraw(self):
        # Clear and redraw all
        for p in list(self.patch_map.values()):
            p.remove()
        self.patch_map.clear()
        # Remove old text annotations
        for txt in self.ax.texts[:]:
            txt.remove()
        for region in self.annotation.regions:
            self._draw_region(region)
        self.fig.canvas.draw_idle()

    # ---- interaction ----
    def _on_click(self, event):
        if event.inaxes != self.ax:
            return

        if event.button == 1:  # left click → add vertex
            vx, vy = float(event.xdata), float(event.ydata)
            self.current_vertices.append((vx, vy))
            self.ax.plot(event.xdata, event.ydata, "r+", markersize=10)
            if len(self.current_vertices) > 1:
                xs = [self.current_vertices[-2][0], self.current_vertices[-1][0]]
                ys = [self.current_vertices[-2][1], self.current_vertices[-1][1]]
                self.ax.plot(xs, ys, "r--", linewidth=1)
            self.fig.canvas.draw_idle()

        elif event.button == 3:  # right click → close polygon
            if len(self.current_vertices) < 3:
                return
            label, tags = self._prompt_label_tags()
            if label is None:
                self.current_vertices.clear()
                return
            region = Region(
                id=str(uuid.uuid4())[:8],
                label=label,
                vertices=list(self.current_vertices),
                tags=tags,
            )
            self.annotation.regions.append(region)
            self.current_vertices.clear()
            self._redraw()

        elif event.button == 2:  # middle click → select existing region
            from matplotlib.path import Path

            self.selected_region = None
            for region in self.annotation.regions:
                path = Path(region.vertices)
                if path.contains_point((event.xdata, event.ydata)):
                    self.selected_region = region
                    break
            self._redraw()

    def _on_delete(self, _event):
        if self.selected_region:
            self.annotation.regions.remove(self.selected_region)
            self.selected_region = None
            self._redraw()

    def _prompt_label_tags(self):
        """Tiny Tk dialog for label + tags."""
        root = tk.Tk()
        root.withdraw()
        label = simpledialog.askstring("Region Label", "Semantic label:", parent=root)
        if label is None:
            root.destroy()
            return None, []
        tags_str = (
            simpledialog.askstring(
                "Tags", "Comma-separated tags (optional):", parent=root
            )
            or ""
        )
        root.destroy()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        return label, tags

    def on_save(self, callback):
        self._save_callback = callback
        self.btn_save.on_clicked(lambda _: callback(self.annotation))

    def run(self):
        plt.show()
