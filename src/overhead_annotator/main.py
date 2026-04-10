import argparse
from model import MapAnnotation, GeoReference
import serde
from editor import Editor


def main():
    parser = argparse.ArgumentParser(description="Map Region Annotator")

    # --- Option A: local image ---
    parser.add_argument("--image", "-i", default=None,
                        help="Path to a local overhead image")

    # --- Option B: fetch by bounding box ---
    parser.add_argument("--bbox", nargs=4, type=float, default=None,
                        metavar=("LAT_S", "LON_W", "LAT_N", "LON_E"),
                        help="Bounding box: lower-left lat, lon → upper-right lat, lon")
    parser.add_argument("--zoom", default="auto",
                        help="Tile zoom level (int or 'auto')")

    # --- YAML persistence ---
    parser.add_argument("--yaml", "-y", default=None,
                        help="YAML file to load/save annotations")

    args = parser.parse_args()

    # ---- Resolve image source ----
    if args.yaml and not args.image and not args.bbox:
        # Pure reload from YAML
        annotation = serde.load(args.yaml)
        yaml_path = args.yaml
        print(f"Loaded {len(annotation.regions)} regions from {yaml_path}")

    elif args.bbox:
        # Fetch satellite imagery
        from fetch import fetch_image, save_image
        lat_s, lon_w, lat_n, lon_e = args.bbox
        zoom = int(args.zoom) if args.zoom != "auto" else "auto"

        print(f"Fetching tiles for ({lat_s}, {lon_w}) → ({lat_n}, {lon_e}) ...")
        img, geo = fetch_image(lat_s, lon_w, lat_n, lon_e, zoom=zoom)

        # Save image locally so it can be reloaded later
        image_path = args.image or "overhead.png"
        save_image(img, image_path)
        print(f"Saved {img.shape[1]}×{img.shape[0]} image to {image_path}")

        georef = GeoReference(
            utm_epsg=geo["utm_epsg"],
            utm_left=geo["utm_left"],
            utm_right=geo["utm_right"],
            utm_bottom=geo["utm_bottom"],
            utm_top=geo["utm_top"],
            image_width=geo["image_width"],
            image_height=geo["image_height"],
        )
        yaml_path = args.yaml or image_path.rsplit(".", 1)[0] + "_annotations.yaml"

        # If YAML already exists, load regions but refresh georef
        try:
            annotation = serde.load(yaml_path)
            annotation.image_path = image_path
            annotation.georef = georef
            print(f"  Loaded {len(annotation.regions)} existing regions from {yaml_path}")
        except FileNotFoundError:
            annotation = MapAnnotation(image_path=image_path, georef=georef)

    elif args.image:
        # Local image, no geo-reference
        yaml_path = args.yaml or args.image.rsplit(".", 1)[0] + "_annotations.yaml"
        try:
            annotation = serde.load(yaml_path)
            annotation.image_path = args.image
            print(f"Loaded {len(annotation.regions)} regions from {yaml_path}")
        except FileNotFoundError:
            annotation = MapAnnotation(image_path=args.image)
            print("Starting fresh annotation.")
    else:
        parser.error("Provide --image, --bbox, or --yaml to reload a session.")
        return

    # ---- Launch editor ----
    editor = Editor(annotation)
    editor.on_save(lambda a: serde.save(a, yaml_path) or print(f"Saved → {yaml_path}"))
    editor.run()

    serde.save(annotation, yaml_path)
    print(f"Auto-saved → {yaml_path}")


if __name__ == "__main__":
    main()
