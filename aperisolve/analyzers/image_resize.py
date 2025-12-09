"""Image size bruteforcer for common PNG sizes."""

import zlib
import shutil
from pathlib import Path
from .utils import update_data

# Full list of expected sizes
EXPECTED_SIZES = [
    # -------------------------
    # ICONS (Square)
    # -------------------------
    (16, 16), (20, 20), (24, 24), (28, 28),
    (32, 32), (48, 48), (64, 64), (72, 72),
    (96, 96), (128, 128), (192, 192), (256, 256),
    (384, 384), (512, 512), (768, 768), (1024, 1024),
    (1536, 1536), (2048, 2048), (4096, 4096),

    # -------------------------
    # 1:1 Square (General)
    # -------------------------
    (300, 300), (500, 500), (800, 800), (1000, 1000),
    (1500, 1500), (2000, 2000), (2500, 2500), (3000, 3000),

    # -------------------------
    # 4:3 Aspect (Classic Screens)
    # -------------------------
    (320, 240), (640, 480), (800, 600), (960, 720),
    (1024, 768), (1280, 960), (1600, 1200), (2048, 1536),
    (2560, 1920), (3200, 2400), (4096, 3072),

    # -------------------------
    # 3:2 Aspect (Photography)
    # -------------------------
    (600, 400), (900, 600), (1200, 800), (1500, 1000),
    (1800, 1200), (2400, 1600), (3000, 2000), (3600, 2400),
    (4500, 3000), (6000, 4000),

    # -------------------------
    # 16:9 Aspect (Video / Web)
    # -------------------------
    (426, 240), (640, 360), (854, 480), (960, 540),
    (1280, 720), (1366, 768), (1600, 900), (1920, 1080),
    (2560, 1440), (3200, 1800), (3440, 1935), (3840, 2160),
    (5120, 2880), (7680, 4320), (10240, 5760),

    # -------------------------
    # 16:10 Aspect (Laptops)
    # -------------------------
    (1280, 800), (1440, 900), (1680, 1050),
    (1920, 1200), (2560, 1600), (2880, 1800),
    (3840, 2400), (5120, 3200),

    # -------------------------
    # Mobile Portrait (9:16)
    # -------------------------
    (720, 1280), (1080, 1920), (1440, 2560),
    (2160, 3840), (1440, 2960), (1080, 2400),
    (1170, 2532), (1284, 2778), (1290, 2796),

    # -------------------------
    # Social Media Sizes
    # -------------------------
    # Instagram
    (1080, 1080), (1080, 1350), (1080, 1920),

    # Facebook
    (1200, 628), (1200, 1200),

    # Twitter/X
    (1200, 675), (1500, 500),

    # YouTube Thumbnails
    (1280, 720), (1920, 1080),

    # -------------------------
    # Banners / Headers
    # -------------------------
    (1600, 500), (1920, 500), (2560, 700),
    (3000, 1000), (3840, 1200),

    # -------------------------
    # Print-like Digital Sizes
    # -------------------------
    (2550, 3300),  # Letter @ 300 DPI
    (2480, 3508),  # A4 @ 300 DPI
    (3508, 4961),  # A3 @ 300 DPI
    (4961, 7016),  # A2 @ 300 DPI
    (7016, 9933),  # A1 @ 300 DPI

]

def calc_checksum(header_chunk, width_bytes, height_bytes):
    """
    Calculates the CRC32 of the IHDR chunk with new dimensions.
    header_chunk: The full IHDR chunk (Type + Data).
    """
    # Reconstruct IHDR: [Type(4)] + [New Width(4)] + [New Height(4)] + [Rest of Data(5)]
    new_header = header_chunk[:4] + width_bytes + height_bytes + header_chunk[12:]

    # Calculate CRC and return as 4 bytes (Big Endian)
    return bytearray((zlib.crc32(new_header) & 0xffffffff).to_bytes(4, byteorder='big'))

def analyze_image_resize(input_img: Path, output_dir: Path) -> None:
    """
    Analyze an image submission using python-based resize bruteforce.
    Attempts to recover PNGs with modified resolutions but valid CRCs.
    """

    # 1. Setup Paths
    input_img = Path(input_img)
    output_dir = Path(output_dir)
    extracted_dir = output_dir / "image_resize_output_dir"

    # 2. CREATE THE DIRECTORY (Crucial Step!)
    extracted_dir.mkdir(parents=True, exist_ok=True)

    # 3. Initialize Logs
    logs = []
    recovered_image = None

    try:
        with open(input_img, "rb") as image:
            f = image.read()

        b = bytearray(f)

        # Find IHDR start
        IHDR = b.find(b'\x49\x48\x44\x52')
        if IHDR == -1:
            logs.append("Failure: PNG header (IHDR) not found.")
            update_data(output_dir, {"image_resize": {"status": "error", "error": "PNG header not found."}})
            if extracted_dir.exists():
                shutil.rmtree(extracted_dir, ignore_errors=True)
            return

        # Calculate Chunk Length (The 4 bytes BEFORE IHDR tag)
        chunk_length = int.from_bytes((b[IHDR- 4: IHDR]), byteorder="big") + 4

        # Extract Target CRC (The 4 bytes AFTER the chunk data)
        target_crc = b[IHDR + chunk_length:IHDR + chunk_length + 4]

        # Isolate the header chunk (Type + Data)
        header_chunk = b[IHDR:IHDR + chunk_length]

        logs.append(f"Target CRC found: 0x{target_crc.hex()}")

        match_found = False

        # Brute-force Loop
        for size in EXPECTED_SIZES:
            width, height = size

            # Convert dimensions to 4-byte Big Endian arrays
            width_bytes = bytearray(width.to_bytes(4, byteorder='big'))
            height_bytes = bytearray(height.to_bytes(4, byteorder='big'))

            # Check if this size matches the file's CRC
            if target_crc == calc_checksum(header_chunk, width_bytes, height_bytes):
                match_found = True
                logs.append(f"Success: Match found! Dimensions: {width}x{height}")

                # Create Output Filename
                output_filename = f"recovered_{width}x{height}.png"
                output_path = extracted_dir / output_filename

                # Splicing: [Start...IHDR+4] + [W] + [H] + [IHDR+12...End]
                full_png_data = b[:IHDR+4] + width_bytes + height_bytes + b[IHDR+12:]

                # Write the recovered file to disk
                with output_path.open("wb") as out_f:
                    out_f.write(full_png_data)

                recovered_image = output_filename
                break # Stop looking after finding the match

        if not match_found:
            logs.append("Failure: No matching dimensions found.")

        # 4. Final Data Update
        output_data = {
            "image_resize": {  # Key name must match your module name in AperiSolve
                "status": "ok",
                "output": logs,
                "images": recovered_image, # Tells frontend to display the image
            }
        }
        update_data(output_dir, output_data)

    except Exception as e:
        update_data(output_dir, {"image_resize": {"status": "error", "error": str(e)}})
        if extracted_dir.exists():
            shutil.rmtree(extracted_dir, ignore_errors=True)

    return None