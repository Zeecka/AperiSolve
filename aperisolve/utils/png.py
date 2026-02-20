"""PNG Class for analyzer modules."""

import itertools
import re
import struct
import zlib
from typing import Any

from aperisolve.app import create_app
from aperisolve.models import IHDR

from .utils import int2hex, str2hex

__author__ = [
    "Zeecka",
    "indonumberone (https://github.com/indonumberone/PCRT3)",
    "Etr1x (https://github.com/Etr1x/PCRT3)",
    "sherlly (https://github.com/sherlly/PCRT)",
]

IDAT_NOT_FOUND_OFFSET = -5


class PNG:
    """PNG file analyzer and repair tool."""

    def __init__(self, data: bytes) -> None:
        """Initialize PNG parser state for a binary payload."""
        self.data = data
        self.width = self.height = self.bits = self.mode = 0
        self.compression = self.filter = self.interlace = self.channel = 0
        self.txt_content: dict[bytes, list[bytes]] = {}
        self.image_content: dict[bytes, list[bytes]] = {}
        self.crcs: dict[bytes, Any] = {}
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
        return all(p in data for p in [b"IHDR", b"IDAT", b"IEND"])

    def _check_crc(self, chunk_type: bytes, chunk_data: bytes, checksum: bytes) -> bytes | None:
        """Check CRC of chunk."""
        calc_crc = struct.pack("!I", zlib.crc32(chunk_type + chunk_data))
        return calc_crc if calc_crc != checksum else None

    def _find_ihdr(self, data: bytes) -> tuple[int, bytes]:
        """Find IHDR chunk in PNG data."""
        pos = data.find(b"IHDR")
        if pos == -1:
            return -1, b""
        # IHDR chunk is always 25 bytes: 4 (length) + 4 (type) + 13 (data) + 4 (CRC)
        # Only return the IHDR chunk itself, not everything up to IDAT
        return pos, data[pos - 4 : pos + 21]

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

    def _find_ancillary(
        self,
        data: bytes,
    ) -> tuple[dict[bytes, list[bytes]], dict[bytes, list[bytes]], dict[bytes, Any]]:
        """Find ancillary chunks in PNG data with an optimized single pass."""
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

        # Initialize result dictionaries
        image_content: dict[bytes, list[bytes]] = {chunk: [] for chunk in ancillary}
        txt_content: dict[bytes, list[bytes]] = {chunk: [] for chunk in attach_txt}
        crcs: dict[bytes, Any] = {chunk: [] for chunk in ancillary}

        # Single pass through data
        pos = 8  # Skip PNG signature
        while pos < len(data) - 12:  # Need at least 12 bytes for chunk header
            # Try to read chunk length
            try:
                length = struct.unpack("!I", data[pos : pos + 4])[0]
                chunk_type = data[pos + 4 : pos + 8]

                # Check if this is a chunk we care about
                if chunk_type in ancillary:
                    chunk_data = data[pos + 8 : pos + 8 + length]
                    image_content[chunk_type].append(chunk_data)

                    # Check CRC for first occurrence only
                    if len(image_content[chunk_type]) == 1:
                        crc_data = data[pos + 8 + length : pos + 12 + length]
                        calc_crc = self._check_crc(chunk_type, chunk_data, crc_data)
                        crcs[chunk_type] = (calc_crc, crc_data) if calc_crc else []

                elif chunk_type in attach_txt:
                    chunk_data = data[pos + 8 : pos + 8 + length]
                    txt_content[chunk_type].append(chunk_data)

                # Move to next chunk
                pos += 12 + length
            except (struct.error, IndexError):
                # Malformed chunk, skip ahead
                pos += 1

        return txt_content, image_content, crcs

    def check_chunks(self) -> bool:
        """Copy ancillary chunks (like PLTE) from original data to repaired_data with CRC.

        validation.
        """
        critical_ancillary = [
            b"PLTE",
            b"tRNS",
            b"cHRM",
            b"gAMA",
            b"iCCP",
            b"sBIT",
            b"sRGB",
            b"bKGD",
            b"hIST",
            b"pHYs",
            b"sPLT",
        ]

        ihdr_end = len(self.repaired_data)
        idat_pos = self.data.find(b"IDAT")
        if idat_pos == -1:
            return False

        search_start = self.data.find(b"IHDR")
        if search_start == -1:
            return False

        # Skip past the IHDR chunk
        ihdr_length = struct.unpack("!I", self.data[search_start - 4 : search_start])[0]
        search_start = search_start + 4 + ihdr_length + 4

        # Collect all ancillary chunks before IDAT
        for chunk_type in critical_ancillary:
            pos = search_start
            while pos < idat_pos:
                pos = self.data.find(chunk_type, pos, idat_pos)
                if pos == -1:
                    break

                chunk_start = pos - 4
                length = struct.unpack("!I", self.data[chunk_start:pos])[0]
                chunk_data = self.data[pos + 4 : pos + 4 + length]
                chunk_crc = self.data[pos + 4 + length : pos + 8 + length]

                # Validate CRC before copying
                if calc_crc := self._check_crc(chunk_type, chunk_data, chunk_crc):
                    self._log(f"Warning: {chunk_type.decode()} has invalid CRC, fixing...")
                    chunk_crc = calc_crc

                # Reconstruct complete chunk with validated CRC
                complete_chunk = struct.pack("!I", length) + chunk_type + chunk_data + chunk_crc
                self.repaired_data[ihdr_end:ihdr_end] = complete_chunk
                ihdr_end += len(complete_chunk)

                self._log(f"Copied {chunk_type.decode()} chunk ({length} bytes)")
                pos = pos + 4 + length + 4

        return True

    def _lookup_ihdr_from_db(self, chunk_type: bytes, crc: bytes) -> bytes | None:
        """Try to recover IHDR bytes from known CRC values in the database."""
        crc_int = struct.unpack("!I", crc)[0]
        app = create_app()
        with app.app_context():
            matches = IHDR.query.filter_by(crc=crc_int).all()

        if not matches:
            return None

        self._log(f"Found {len(matches)} matching IHDR configuration(s) in database")
        match = matches[0]
        test_ihdr = match.to_ihdr_bytes()
        if self._check_crc(chunk_type, test_ihdr, crc):
            self._log("Database match found but CRC verification failed")
            return None

        self._log(
            f"Recovered IHDR: {match.width}x{match.height}, "
            f"bit_depth={match.bit_depth}, "
            f"color_type={match.color_type}, "
            f"interlace={match.interlace}",
        )
        return test_ihdr

    def _bruteforce_ihdr_dimensions(
        self,
        chunk_type: bytes,
        ihdr: bytes,
        crc: bytes,
    ) -> bytes | None:
        """Fallback recovery for width and height by brute-force CRC matching."""
        self._log("No database match found, falling back to exhaustive search...")
        for width in range(1, 5000):
            for height in range(1, 5000):
                test_ihdr = struct.pack(">I", width) + struct.pack(">I", height) + ihdr[16:21]
                if not self._check_crc(chunk_type, test_ihdr, crc):
                    self._log(
                        f"Found correct dimensions via exhaustive search: {width}x{height}",
                    )
                    return test_ihdr
        return None

    def check_ihdr(self) -> bool:
        """Check and repair IHDR chunk using database lookup and exhaustive fallback."""
        pos, ihdr = self._find_ihdr(self.data)
        if pos == -1:
            self._error("Lost IHDR chunk")
            return False

        length = struct.unpack("!I", ihdr[:4])[0]
        chunk_type, chunk_ihdr = ihdr[4:8], ihdr[8 : 8 + length]
        crc = ihdr[8 + length : 12 + length]

        fixed = False
        if calc_crc := self._check_crc(chunk_type, chunk_ihdr, crc):
            self._log(f"Error IHDR CRC found at offset {int2hex(pos + 4 + length)}")
            self._log(f"Chunk crc: {str2hex(crc)}, Correct crc: {str2hex(calc_crc)}")
            self._log("Looking up CRC in database...")

            if (recovered_ihdr := self._lookup_ihdr_from_db(chunk_type, crc)) or (
                recovered_ihdr := self._bruteforce_ihdr_dimensions(chunk_type, ihdr, crc)
            ):
                ihdr = ihdr[:8] + recovered_ihdr + crc
                fixed = True

            if not fixed:
                self._error("Could not recover IHDR dimensions")
        else:
            self._log(f"Correct IHDR CRC at offset {int2hex(pos + 4 + length)}")

        self.repaired_data.extend(ihdr)
        self._log(f"IHDR chunk check complete at offset {int2hex(pos - 4)}")

        self.get_pic_info(ihdr=chunk_ihdr if not fixed else ihdr[8 : 8 + length])
        return fixed

    def _fix_dos2unix(
        self,
        chunk_type: bytes,
        chunk_data: bytes,
        crc: bytes,
        count: int,
    ) -> bytes | None:
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
        if idat_begin == IDAT_NOT_FOUND_OFFSET:
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
                    self.data[pos1 - 4 : pos_iend - 4 if pos_iend != -1 else len(self.data)],
                )
            else:
                idat_table.append(self.data[pos1 - 4 : pos_list[i + 1] - 4])

        offset = idat_begin
        fixed = False
        for chunk in idat_table:
            current_chunk = chunk
            length = struct.unpack("!I", current_chunk[:4])[0]
            chunk_type, chunk_data, crc = (
                current_chunk[4:8],
                current_chunk[8:-4],
                current_chunk[-4:],
            )

            if length != len(chunk_data):
                self._log(f"Error IDAT chunk data length at offset {int2hex(offset)}")
                self._log(f"Length: {int2hex(length)}, Actual: {int2hex(len(chunk_data))}")
                if fixed_data := self._fix_dos2unix(
                    chunk_type,
                    chunk_data,
                    crc,
                    abs(length - len(chunk_data)),
                ):
                    current_chunk = current_chunk[:8] + fixed_data + current_chunk[-4:]
                    self._log("Successfully recovered IDAT chunk data (DOS->Unix fix)")
                    fixed = True
                else:
                    self._log("Failed to fix IDAT chunk, using original")
            elif calc_crc := self._check_crc(chunk_type, chunk_data, crc):
                self._log(f"Error IDAT CRC at offset {int2hex(offset + 8 + length)}")
                self._log(f"Chunk crc: {str2hex(crc)}, Correct: {str2hex(calc_crc)}")
                current_chunk = current_chunk[:-4] + calc_crc
                self._log("Successfully fixed CRC")
                fixed = True

            self.repaired_data.extend(current_chunk)
            offset += len(chunk_data) + 12

        self._log(f"IDAT chunk check complete at offset {int2hex(idat_begin)}")
        return fixed

    def check_iend(self) -> tuple[bool, bytes | None]:
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
                self._log(f"Found {len(extra_data)} bytes after IEND: {extra_data[:20]!r}")

        self.repaired_data.extend(iend)
        self._log("IEND chunk check complete")
        return fixed, extra_data

    def repair(self) -> tuple[bool, bytes | None]:
        """Run full PNG repair process."""
        if not self._check_format(self.data):
            self._error("File may not be a PNG image")
            return False, None

        fixed = False
        fixed |= self.check_header()
        fixed |= self.check_ihdr()
        fixed |= self.check_chunks()
        fixed |= self.check_idat()
        iend_fixed, extra_data = self.check_iend()
        fixed |= iend_fixed

        return fixed, extra_data
