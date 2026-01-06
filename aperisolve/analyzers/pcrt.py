# flake8: noqa: E203,E501,W503
# pylint: disable=C0413,W0718,R0903,R0801
# mypy: disable-error-code=unused-awaitable
"""PCRT (PNG Check & Repair Tool) Analyzer for Image Submissions."""

__author__ = [
    "Zeecka",
    "indonumberone (https://github.com/indonumberone/PCRT3)",
    "Etr1x (https://github.com/Etr1x/PCRT3)",
    "sherlly (https://github.com/sherlly/PCRT)",
]

import binascii
import itertools
import re
import struct
import zlib
from pathlib import Path
from typing import Any, Optional

from .base_analyzer import SubprocessAnalyzer


def str2hex(s: bytes) -> str:
    """Convert bytes to hex string."""
    return binascii.hexlify(s).decode().upper()


def int2hex(i: int) -> str:
    """Convert int to hex string with 0x prefix."""
    return "0x" + hex(i)[2:].upper()


def str2num(s: bytes, n: int = 0) -> int:
    """Convert bytes to number."""
    return struct.unpack("!I", s)[0] if n == 4 else int(str2hex(s), 16)


class PNG:
    """PNG file analyzer and repair tool."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.width = self.height = self.bits = self.mode = 0
        self.compression = self.filter = self.interlace = self.channel = 0
        self.txt_content: dict = {}
        self.image_content: dict = {}
        self.crcs: dict = {}
        self.repaired_data = bytearray()
        self.logs: list[str] = []
        self.errors: list[str] = []

    def _log(self, msg: str) -> None:
        """Add message to logs."""
        self.logs.append(msg)

    def _error(self, msg: str) -> None:
        """Add error message."""
        self.errors.append(msg)

    def _check_format(self, data: bytes) -> bool:
        """Check if data contains PNG signature chunks."""
        return all(p in data for p in [b"PNG", b"IHDR", b"IDAT", b"IEND"])

    def _check_crc(self, chunk_type: bytes, chunk_data: bytes, checksum: bytes) -> Optional[bytes]:
        """Check CRC of chunk."""
        calc_crc = struct.pack("!I", zlib.crc32(chunk_type + chunk_data))
        return calc_crc if calc_crc != checksum else None

    def _find_ihdr(self, data: bytes) -> tuple[int, bytes]:
        """Find IHDR chunk in PNG data."""
        pos = data.find(b"IHDR")
        if pos == -1:
            return -1, b""
        idat_begin = data.find(b"IDAT")
        return pos, data[pos - 4 : idat_begin - 4 if idat_begin != -1 else pos + 21]

    def check_header(self) -> bool:
        """Check and fix PNG header."""
        header = self.data[:8]
        correct = b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a"
        if header != correct:
            self._log(f"Wrong PNG header: {str2hex(header)}")
            self._log("Fixed header to: 89504E470D0A1A0A")
            self.repaired_data.extend(correct)
            return True
        self._log("Correct PNG header")
        self.repaired_data.extend(header)
        return False

    def get_pic_info(self, ihdr: bytes = b"") -> bool:
        """Extract picture information from IHDR chunk."""
        if not ihdr:
            pos, ihdr_chunk = self._find_ihdr(self.data)
            if pos == -1:
                self._error("Lost IHDR chunk")
                return False
            length = struct.unpack("!I", ihdr_chunk[:4])[0]
            ihdr = ihdr_chunk[8 : 8 + length]

        (
            self.width,
            self.height,
            self.bits,
            self.mode,
            self.compression,
            self.filter,
            self.interlace,
        ) = struct.unpack("!iiBBBBB", ihdr)

        self.interlace = int(ihdr[12])
        self.channel = {0: 1, 3: 1, 2: 3, 4: 2, 6: 4}.get(self.mode, 0)

        self.txt_content, self.image_content, self.crcs = self._find_ancillary(self.data)
        return True

    def _find_ancillary(self, data: bytes) -> tuple[dict, dict, dict]:
        """Find ancillary chunks in PNG data."""
        ancillary = [
            b"cHRM",
            b"pHYs",
            b"gAMA",
            b"sBIT",
            b"PLTE",
            b"bKGD",
            b"sTER",
            b"hIST",
            b"iCCP",
            b"sPLT",
            b"sRGB",
            b"dSIG",
            b"tIME",
            b"tRNS",
            b"oFFs",
            b"sCAL",
            b"fRAc",
            b"gIFg",
            b"gIFt",
            b"gIFx",
        ]
        attach_txt = [b"eXIf", b"iTXt", b"tEXt", b"zTXt"]
        image_content: dict = {}
        crcs: dict = {}

        for data_i in ancillary:
            image_content[data_i] = []
            crcs[data_i] = []
            pos = 0
            while (pos := data.find(data_i, pos)) != -1:
                length = str2num(data[pos - 4 : pos])
                image_content[data_i].append(data[pos + 4 : pos + 4 + length])
                crc_data = data[pos + 4 + length : pos + 4 + length + 4]
                calc_crc = self._check_crc(data_i, image_content[data_i][0], crc_data)
                crcs[data_i] = (calc_crc, crc_data) if calc_crc else []
                pos += 4 + length + 1

        txt_content: dict = {}
        for text in attach_txt:
            txt_content[text] = []
            pos = 0
            while (pos := data.find(text, pos)) != -1:
                length = str2num(data[pos - 4 : pos])
                txt_content[text].append(data[pos + 4 : pos + 4 + length])
                pos += 1
        return txt_content, image_content, crcs

    def check_ihdr(self) -> bool:
        """Check and repair IHDR chunk."""
        pos, ihdr = self._find_ihdr(self.data)
        if pos == -1:
            self._error("Lost IHDR chunk")
            return False

        length = struct.unpack("!I", ihdr[:4])[0]
        chunk_type, chunk_ihdr = ihdr[4:8], ihdr[8 : 8 + length]
        crc = ihdr[8 + length : 12 + length]
        width, height = struct.unpack("!II", chunk_ihdr[:8])

        fixed = False
        if calc_crc := self._check_crc(chunk_type, chunk_ihdr, crc):
            self._log(f"Error IHDR CRC found at offset {int2hex(pos + 4 + length)}")
            self._log(f"Chunk crc: {str2hex(crc)}, Correct crc: {str2hex(calc_crc)}")
            self._log("Bruteforcing dimensions...")

            for w in range(width + height + 1000):
                for h in range(width + height + 1000):
                    test_ihdr = struct.pack(">I", w) + struct.pack(">I", h) + ihdr[16:21]
                    if not self._check_crc(chunk_type, test_ihdr, crc):
                        ihdr = ihdr[:8] + test_ihdr + crc
                        self._log(f"Found correct dimensions: {w}x{h}")
                        fixed = True
                        break
                if fixed:
                    break

            if not fixed:
                self._error(f"Exhausted dimensions up to ({width + height + 1000})")
        else:
            self._log(f"Correct IHDR CRC at offset {int2hex(pos + 4 + length)}")

        self.repaired_data.extend(ihdr)
        self._log(f"IHDR chunk check complete at offset {int2hex(pos - 4)}")
        self.get_pic_info(ihdr=chunk_ihdr)
        return fixed

    def _fix_dos2unix(
        self, chunk_type: bytes, chunk_data: bytes, crc: bytes, count: int
    ) -> Optional[bytes]:
        """Fix DOS to Unix line ending conversion."""
        pos_list = []
        pos = -1
        while (pos := chunk_data.find(b"\x0a", pos + 1)) != -1:
            pos_list.append(pos)
        for pos_combo in itertools.combinations(pos_list, count):
            test_data = chunk_data
            for i, pos in enumerate(pos_combo):
                test_data = test_data[: pos + i] + b"\x0d" + test_data[pos + i :]
            if not self._check_crc(chunk_type, test_data, crc):
                return test_data
        return None

    def check_idat(self) -> bool:
        """Check and repair IDAT chunks."""
        idat_begin = self.data.find(b"IDAT") - 4
        if idat_begin == -5:
            self._error("Lost all IDAT chunks")
            return False

        pos_iend = self.data.find(b"IEND")
        pos_list = [
            g.start()
            for g in re.finditer(b"IDAT", self.data)
            if pos_iend == -1 or g.start() < pos_iend
        ]

        idat_table = []
        for i, pos1 in enumerate(pos_list):
            if i + 1 == len(pos_list):
                idat_table.append(
                    self.data[pos1 - 4 : pos_iend - 4 if pos_iend != -1 else len(self.data)]
                )
            else:
                idat_table.append(self.data[pos1 - 4 : pos_list[i + 1] - 4])

        offset = idat_begin
        fixed = False
        for idat_chunk in idat_table:
            length = struct.unpack("!I", idat_chunk[:4])[0]
            chunk_type, chunk_data, crc = idat_chunk[4:8], idat_chunk[8:-4], idat_chunk[-4:]

            if length != len(chunk_data):
                self._log(f"Error IDAT chunk data length at offset {int2hex(offset)}")
                self._log(f"Length: {int2hex(length)}, Actual: {int2hex(len(chunk_data))}")
                if fixed_data := self._fix_dos2unix(
                    chunk_type, chunk_data, crc, abs(length - len(chunk_data))
                ):
                    idat_chunk = idat_chunk[:8] + fixed_data + idat_chunk[-4:]
                    self._log("Successfully recovered IDAT chunk data (DOS->Unix fix)")
                    fixed = True
                else:
                    self._log("Failed to fix IDAT chunk, using original")
            else:
                if calc_crc := self._check_crc(chunk_type, chunk_data, crc):
                    self._log(f"Error IDAT CRC at offset {int2hex(offset + 8 + length)}")
                    self._log(f"Chunk crc: {str2hex(crc)}, Correct: {str2hex(calc_crc)}")
                    idat_chunk = idat_chunk[:-4] + calc_crc
                    self._log("Successfully fixed CRC")
                    fixed = True

            self.repaired_data.extend(idat_chunk)
            offset += len(chunk_data) + 12

        self._log(f"IDAT chunk check complete at offset {int2hex(idat_begin)}")
        return fixed

    def check_iend(self) -> tuple[bool, Optional[bytes]]:
        """Check and repair IEND chunk."""
        standard_iend = b"\x00\x00\x00\x00IEND\xae\x42\x60\x82"
        pos = self.data.find(b"IEND")
        fixed = False
        extra_data = None

        if pos == -1:
            self._log("Lost IEND chunk, adding standard IEND")
            iend = standard_iend
            fixed = True
        else:
            iend = self.data[pos - 4 : pos + 8]
            if iend != standard_iend:
                self._log("Error IEND chunk, fixing...")
                iend = standard_iend
                fixed = True
            else:
                self._log("Correct IEND chunk")

            if extra_data := self.data[pos + 8 :]:
                self._log(f"Found {len(extra_data)} bytes after IEND: {extra_data[:20]}")

        self.repaired_data.extend(iend)
        self._log("IEND chunk check complete")
        return fixed, extra_data

    def repair(self) -> tuple[bool, Optional[bytes]]:
        """Run full PNG repair process."""
        if not self._check_format(self.data):
            self._error("File may not be a PNG image")
            return False, None

        fixed = False
        fixed |= self.check_header()
        fixed |= self.check_ihdr()
        fixed |= self.check_idat()
        iend_fixed, extra_data = self.check_iend()
        fixed |= iend_fixed

        return fixed, extra_data


class PCRTAnalyzer(SubprocessAnalyzer):
    """Analyzer for PCRT (PNG Check & Repair Tool)."""

    def __init__(self, input_img: Path, output_dir: Path) -> None:
        super().__init__("pcrt", input_img, output_dir, has_archive=True)

    def _write_repaired_data(self, data: bytes) -> str:
        """Write recovered image."""
        img_name = f"pcrt_recoverd_{self.input_img.name}.png"
        output_path = self.output_dir / img_name
        saved_img_url = "/image/" + str(Path(self.output_dir.name) / img_name)
        with output_path.open("wb") as f:
            f.write(data)
        return saved_img_url

    def _write_extra_data(self, data: bytes) -> None:
        """Write recovered extra data."""
        extracted_dir = self.get_extracted_dir()
        extracted_dir.mkdir(parents=True, exist_ok=True)
        extra_path = extracted_dir / "extra_data.bin"
        with extra_path.open("wb") as f:
            f.write(data)

    def get_results(self, password: Optional[str] = None) -> dict[str, Any]:
        """Analyze PNG and attempt repairs."""
        try:
            with self.input_img.open("rb") as f:
                data = f.read()

            png = PNG(data)
            fixed, extra_data = png.repair()

            result: dict[str, Any] = {}

            if png.errors:
                result["status"] = "error"
                result["error"] = "\n".join(png.errors)
                if png.logs:
                    result["output"] = png.logs
                return result

            result["status"] = "ok"
            result["output"] = png.logs if png.logs else ["PNG appears valid, no repairs needed"]

            # Save repaired PNG if any fixes were made
            if fixed and png.repaired_data:
                url = self._write_repaired_data(png.repaired_data)
                result["note"] = "PNG was repaired and saved"
                result["png_images"] = [url]

            # Save extra data if found after IEND
            if extra_data:
                self._write_extra_data(extra_data)
                self.generate_archive(self.output_dir)
                result["note"] = result.get("note", "") + " | Extra data found after IEND"
                result["download"] = f"/download/{self.output_dir.name}/{self.name}"

            return result

        except Exception as e:
            return {"status": "error", "error": f"Analysis failed: {str(e)}"}


def analyze_pcrt(input_img: Path, output_dir: Path) -> None:
    """Analyze an image submission using PCRT."""
    analyzer = PCRTAnalyzer(input_img, output_dir)
    analyzer.analyze()
