import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.widgets import Button
from matplotlib.path import Path
import matplotlib
matplotlib.use('Qt5Agg')
import tkinter as tk
from tkinter import simpledialog
from model import Region, MapAnnotation
import uuid

# How close (in pixels) the cursor must be to "grab" a vertex
GRAB_RADIUS = 8


class Editor:
    def __init__(self, annotation: MapAnnotation):
        self.annotation = annotation

        # --- Drawing state ---
        self.current_vertices = []  # vertices of polygon being drawn
        self._draw_markers = []  # temporary matplotlib artists (dots + lines)

        # --- Selection state ---
        self.selected_region = None

        # --- Drag state ---
        self._dragging = False
        self._drag_region = None  # which Region
        self._drag_vert_idx = None  # which vertex index
        self._drag_marker = None  # highlight artist for dragged point

        # --- Patch bookkeeping ---
        self.patch_map = {}  # region.id → (polygon_patch, text_artist)

        # --- Build figure ---
        self.fig, self.ax = plt.subplots(1, 1, figsize=(12, 9))
        img = mpimg.imread(annotation.image_path)
        self.ax.imshow(img)
        self._update_title()

        # Draw pre-existing regions
        for region in self.annotation.regions:
            self._draw_region(region)

        # Buttons
        ax_del = self.fig.add_axes([0.80, 0.01, 0.09, 0.04])
        ax_save = self.fig.add_axes([0.90, 0.01, 0.09, 0.04])
        self.btn_del = Button(ax_del, "Delete")
        self.btn_save = Button(ax_save, "Save")
        self.btn_del.on_clicked(self._on_delete)
        self._save_callback = None

        # Connect events
        self.fig.canvas.mpl_connect("button_press_event", self._on_press)
        self.fig.canvas.mpl_connect("button_release_event", self._on_release)
        self.fig.canvas.mpl_connect("motion_notify_event", self._on_motion)
        self.fig.canvas.mpl_connect("key_press_event", self._on_key)

        # Disconnect default pan/zoom key bindings that conflict
        # and optionally start with toolbar in neutral mode
        self.fig.canvas.manager.toolbar.mode = ''
        # Remove default key bindings that conflict with ours
        for key in ['z', 'backspace', 'escape', 'delete']:
            # Some backends bind z to "undo zoom", etc.
            try:
                plt.rcParams[f'keymap.back'] = [
                    k for k in plt.rcParams.get('keymap.back', []) if k != key
                ]
            except Exception:
                pass

        # Nuclear option: unbind all default keymap conflicts
        import matplotlib as mpl
        for action in ['back', 'forward', 'home', 'pan', 'zoom',
                       'save', 'quit', 'fullscreen', 'yscale', 'xscale']:
            keymap_key = f'keymap.{action}'
            if keymap_key in mpl.rcParams:
                mpl.rcParams[keymap_key] = []

    # ------------------------------------------------------------------ #
    #  Title helper                                                       #
    # ------------------------------------------------------------------ #
    def _update_title(self):
        lines = []
        if self.current_vertices:
            lines.append(
                f"Drawing: {len(self.current_vertices)} pts  |  "
                f"L-click: add  |  R-click: close  |  z: undo"
            )
        else:
            lines.append(
                "L-click: add vertex / drag existing  |  Shift+L-click: select region"
            )
        if self.selected_region:
            lines.append(
                f"Selected: {self.selected_region.label} "
                f"({self.selected_region.id})  |  Del: remove"
            )
        self.ax.set_title("\n".join(lines), fontsize=9)

    # ------------------------------------------------------------------ #
    #  Drawing helpers                                                    #
    # ------------------------------------------------------------------ #
    def _draw_region(self, region: Region):
        is_sel = region is self.selected_region
        edge = "cyan" if is_sel else "yellow"
        face = "cyan" if is_sel else "yellow"
        lw = 3 if is_sel else 2

        patch = MplPolygon(
            region.vertices,
            closed=True,
            fill=True,
            alpha=0.25,
            edgecolor=edge,
            facecolor=face,
            linewidth=lw,
        )
        self.ax.add_patch(patch)

        cx = sum(v[0] for v in region.vertices) / len(region.vertices)
        cy = sum(v[1] for v in region.vertices) / len(region.vertices)
        txt = self.ax.text(
            cx,
            cy,
            f"{region.label}\n{region.id[:8]}",
            ha="center",
            va="center",
            fontsize=7,
            color="black",
            weight="bold",
        )

        # Draw individual vertex handles for selected region
        if is_sel:
            for vx, vy in region.vertices:
                self.ax.plot(
                    vx,
                    vy,
                    "co",
                    markersize=7,
                    markeredgecolor="black",
                    markeredgewidth=0.5,
                    zorder=5,
                )

        self.patch_map[region.id] = (patch, txt)

    def _clear_patches(self):
        for patch, txt in self.patch_map.values():
            patch.remove()
            txt.remove()
        self.patch_map.clear()
        # Remove vertex handles (circles plotted for selected region)
        for line in self.ax.lines[:]:
            if line.get_marker() == "o" and line is not self._drag_marker:
                line.remove()

    def _redraw_regions(self):
        self._clear_patches()
        for region in self.annotation.regions:
            self._draw_region(region)
        self._update_title()
        self.fig.canvas.draw_idle()

    def _clear_draw_markers(self):
        for artist in self._draw_markers:
            artist.remove()
        self._draw_markers.clear()

    def _redraw_draw_markers(self):
        self._clear_draw_markers()
        for i, (vx, vy) in enumerate(self.current_vertices):
            (m,) = self.ax.plot(vx, vy, "r+", markersize=10, zorder=6)
            self._draw_markers.append(m)
            if i > 0:
                prev = self.current_vertices[i - 1]
                (ln,) = self.ax.plot(
                    [prev[0], vx], [prev[1], vy], "r--", linewidth=1, zorder=6
                )
                self._draw_markers.append(ln)

    # ------------------------------------------------------------------ #
    #  Nearest-vertex search                                              #
    # ------------------------------------------------------------------ #
    def _find_nearest_vertex(self, mx, my):
        """
        Returns (region, vertex_index, distance) for the closest vertex
        across all regions, or (None, None, inf).
        """
        best_region = None
        best_idx = None
        best_dist = float("inf")
        for region in self.annotation.regions:
            for i, (vx, vy) in enumerate(region.vertices):
                d = ((vx - mx) ** 2 + (vy - my) ** 2) ** 0.5
                if d < best_dist:
                    best_dist = d
                    best_region = region
                    best_idx = i
        return best_region, best_idx, best_dist

    # ------------------------------------------------------------------ #
    #  Mouse press                                                        #
    # ------------------------------------------------------------------ #
    def _on_press(self, event):
        print(f"PRESS: button={event.button}, key={event.key}, "
          f"inaxes={event.inaxes is not None}, "
          f"toolbar_mode='{self.fig.canvas.manager.toolbar.mode}'")
        if event.inaxes != self.ax:
            return

        mx, my = float(event.xdata), float(event.ydata)

        # --- Shift + left click → select region ---
        if event.button == 1 and event.key == "shift":
            self._select_at(mx, my)
            return

        # --- Right click → close polygon ---
        if event.button == 3:
            self._close_polygon()
            return

        # --- Left click ---
        if event.button == 1:
            # If actively drawing, always add a vertex
            if self.current_vertices:
                self._add_draw_vertex(mx, my)
                return

            # Not drawing — check if near an existing vertex → drag
            region, idx, dist = self._find_nearest_vertex(mx, my)
            if region is not None and dist < GRAB_RADIUS:
                self._start_drag(region, idx)
                return

            # Nothing nearby — start a new polygon
            self._add_draw_vertex(mx, my)

    # ------------------------------------------------------------------ #
    #  Mouse motion (drag)                                                #
    # ------------------------------------------------------------------ #
    def _on_motion(self, event):
        if not self._dragging or event.inaxes != self.ax:
            return

        mx, my = float(event.xdata), float(event.ydata)

        # Update the vertex in-place
        verts = self._drag_region.vertices
        verts[self._drag_vert_idx] = (mx, my)

        # Update visual
        self._redraw_regions()
        # Show a highlight on the dragged point
        if self._drag_marker:
            self._drag_marker.remove()
        (self._drag_marker,) = self.ax.plot(
            mx,
            my,
            "ro",
            markersize=9,
            markeredgecolor="white",
            markeredgewidth=1.5,
            zorder=7,
        )
        self.fig.canvas.draw_idle()

    # ------------------------------------------------------------------ #
    #  Mouse release                                                      #
    # ------------------------------------------------------------------ #
    def _on_release(self, event):
        print("release")
        if not self._dragging:
            return
        if event.inaxes == self.ax:
            mx, my = float(event.xdata), float(event.ydata)
            self._drag_region.vertices[self._drag_vert_idx] = (mx, my)

        # Clean up drag state
        if self._drag_marker:
            print("clean up drag state")
            self._drag_marker.remove()
            self._drag_marker = None
        print("draggin = False")
        self._dragging = False
        self._drag_region = None
        self._drag_vert_idx = None
        self._redraw_regions()

    # ------------------------------------------------------------------ #
    #  Keyboard                                                           #
    # ------------------------------------------------------------------ #
    def _on_key(self, event):
        if event.key in ("z", "Z", "backspace"):
            self._undo_last_vertex()
        elif event.key == "delete":
            self._on_delete(None)
        elif event.key == "escape":
            if self.current_vertices:
                # Cancel current drawing
                self.current_vertices.clear()
                self._clear_draw_markers()
                self._update_title()
                self.fig.canvas.draw_idle()
            else:
                # Deselect
                self.selected_region = None
                self._redraw_regions()

    # ------------------------------------------------------------------ #
    #  Actions                                                            #
    # ------------------------------------------------------------------ #
    def _add_draw_vertex(self, mx, my):
        self.current_vertices.append((mx, my))
        self._redraw_draw_markers()
        self._update_title()
        self.fig.canvas.draw_idle()

    def _undo_last_vertex(self):
        if not self.current_vertices:
            return
        self.current_vertices.pop()
        self._redraw_draw_markers()
        self._update_title()
        self.fig.canvas.draw_idle()

    def _close_polygon(self):
        if len(self.current_vertices) < 3:
            return
        label, tags = self._prompt_label_tags()
        if label is None:
            # User cancelled — keep vertices so they can continue or undo
            return
        region = Region(
            id=str(uuid.uuid4())[:8],
            label=label,
            vertices=list(self.current_vertices),
            tags=tags,
        )
        self.annotation.regions.append(region)
        self.current_vertices.clear()
        self._clear_draw_markers()
        self._redraw_regions()

    def _select_at(self, mx, my):
        self.selected_region = None
        for region in self.annotation.regions:
            path = Path(region.vertices)
            if path.contains_point((mx, my)):
                self.selected_region = region
                break
        self._redraw_regions()

    def _start_drag(self, region, vert_idx):
        self._dragging = True
        self._drag_region = region
        self._drag_vert_idx = vert_idx
        # Auto-select the region being dragged
        self.selected_region = region
        self._redraw_regions()

    def _on_delete(self, _event):
        if self.selected_region:
            self.annotation.regions.remove(self.selected_region)
            self.selected_region = None
            self._redraw_regions()

    def _prompt_label_tags(self):
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

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #
    def on_save(self, callback):
        self._save_callback = callback
        self.btn_save.on_clicked(lambda _: callback(self.annotation))

    def run(self):
        plt.show()
