"""
Inspector Rabbit - Metadata Extractor Module
Extract EXIF from images, metadata from PDFs and documents
"""

import io
import os
import re
import json
import struct
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from urllib.parse import urlparse
from PyQt6.QtCore import QObject, pyqtSignal, QThread


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0.0.0 Safari/537.36'
}


@dataclass
class MetadataResult:
    filename: str = ""
    file_type: str = ""
    file_size: int = 0
    source: str = ""   # 'file' or 'url'
    exif_data: Dict = field(default_factory=dict)
    gps_data: Dict = field(default_factory=dict)
    document_meta: Dict = field(default_factory=dict)
    raw_tags: Dict = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    error: str = ""


GPS_TAGS = {
    1: 'GPSLatitudeRef', 2: 'GPSLatitude', 3: 'GPSLongitudeRef',
    4: 'GPSLongitude', 5: 'GPSAltitudeRef', 6: 'GPSAltitude',
    7: 'GPSTimeStamp', 12: 'GPSSpeedRef', 13: 'GPSSpeed',
    16: 'GPSImgDirectionRef', 17: 'GPSImgDirection',
    23: 'GPSDestBearingRef', 24: 'GPSDestBearing',
    27: 'GPSProcessingMethod', 29: 'GPSDateStamp',
}

IMPORTANT_EXIF_TAGS = {
    'Make', 'Model', 'Software', 'DateTime', 'DateTimeOriginal',
    'DateTimeDigitized', 'ExifImageWidth', 'ExifImageHeight',
    'GPSInfo', 'Author', 'Artist', 'Copyright',
    'XPAuthor', 'XPComment', 'XPTitle', 'XPKeywords',
    'UserComment', 'ImageDescription', 'Orientation',
    'Flash', 'FocalLength', 'ISOSpeedRatings', 'ExposureTime',
    'FNumber', 'WhiteBalance', 'LensModel', 'LensMake',
    'HostComputer', 'ProcessingSoftware',
}


def _rat_to_float(rat):
    """Convert EXIF rational to float"""
    try:
        if isinstance(rat, tuple):
            return rat[0] / rat[1] if rat[1] != 0 else 0
        return float(rat)
    except Exception:
        return 0.0


def _parse_gps_coord(coord_tuple, ref: str) -> float:
    """Parse GPS coordinate from EXIF rational tuple"""
    try:
        d = _rat_to_float(coord_tuple[0])
        m = _rat_to_float(coord_tuple[1])
        s = _rat_to_float(coord_tuple[2])
        decimal = d + m / 60 + s / 3600
        if ref in ('S', 'W'):
            decimal = -decimal
        return round(decimal, 7)
    except Exception:
        return 0.0


def extract_image_metadata(data: bytes, filename: str = "") -> MetadataResult:
    result = MetadataResult(filename=filename, file_size=len(data))

    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS

        img = Image.open(io.BytesIO(data))
        result.file_type = f"Image/{img.format}"
        result.raw_tags['image_size'] = f"{img.width}x{img.height}"
        result.raw_tags['image_mode'] = img.mode
        result.raw_tags['image_format'] = img.format

        # Get EXIF data
        try:
            exif_raw = img._getexif()
            if exif_raw:
                for tag_id, value in exif_raw.items():
                    tag_name = TAGS.get(tag_id, str(tag_id))
                    if tag_name == 'GPSInfo' and isinstance(value, dict):
                        gps = {}
                        for gps_id, gps_val in value.items():
                            gps_tag = GPSTAGS.get(gps_id, str(gps_id))
                            gps[gps_tag] = str(gps_val)
                        result.exif_data['GPSInfo'] = gps

                        # Calculate decimal coordinates
                        if 'GPSLatitude' in gps and 'GPSLatitudeRef' in gps and \
                           'GPSLongitude' in gps and 'GPSLongitudeRef' in gps:
                            lat = _parse_gps_coord(value[2], value[1])
                            lon = _parse_gps_coord(value[4], value[3])
                            result.gps_data = {
                                'latitude': lat,
                                'longitude': lon,
                                'maps_url': f"https://maps.google.com/?q={lat},{lon}",
                                'lat_ref': str(value.get(1, '')),
                                'lon_ref': str(value.get(3, '')),
                            }
                            if lat and lon:
                                result.warnings.append(
                                    f"⚠️  GPS LOCATION EMBEDDED: {lat}, {lon}"
                                )
                    elif tag_name in IMPORTANT_EXIF_TAGS:
                        result.exif_data[tag_name] = str(value)[:200]
                    else:
                        result.raw_tags[tag_name] = str(value)[:100]
        except Exception:
            pass

        # Check for XMP metadata
        try:
            xmp = img.info.get('xmp', b'')
            if xmp:
                xmp_str = xmp.decode('utf-8', errors='ignore')
                # Extract creator
                creator_match = re.search(r'dc:creator[^>]*>([^<]+)', xmp_str)
                if creator_match:
                    result.document_meta['XMP Creator'] = creator_match.group(1).strip()
                # Extract description
                desc_match = re.search(r'dc:description[^>]*>([^<]+)', xmp_str)
                if desc_match:
                    result.document_meta['XMP Description'] = desc_match.group(1).strip()
        except Exception:
            pass

        # Check other PIL info
        for key, value in img.info.items():
            if key not in ('exif', 'xmp') and isinstance(value, (str, int, float)):
                result.raw_tags[f'info_{key}'] = str(value)[:100]

    except ImportError:
        result.error = "Pillow library not installed"
    except Exception as e:
        result.error = f"Image metadata error: {e}"

    return result


def extract_pdf_metadata(data: bytes, filename: str = "") -> MetadataResult:
    result = MetadataResult(filename=filename, file_type="PDF", file_size=len(data))
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(data))
        meta = reader.metadata

        if meta:
            fields = [
                'title', 'author', 'subject', 'creator', 'producer',
                'creation_date', 'modification_date', 'keywords',
            ]
            for field in fields:
                val = getattr(meta, field, None)
                if val:
                    result.document_meta[field.replace('_', ' ').title()] = str(val)[:200]

        result.document_meta['Pages'] = str(len(reader.pages))

        # Check for encryption
        if reader.is_encrypted:
            result.warnings.append("⚠️  PDF is encrypted")

        # Try to read page text for metadata clues
        try:
            first_page_text = reader.pages[0].extract_text()[:500]
            if first_page_text:
                result.raw_tags['first_page_preview'] = first_page_text
        except Exception:
            pass

    except ImportError:
        result.error = "pypdf library not installed. Run: pip3 install pypdf"
    except Exception as e:
        result.error = f"PDF metadata error: {e}"

    return result


def extract_metadata_from_bytes(data: bytes, filename: str = "",
                                 url: str = "") -> MetadataResult:
    """Auto-detect file type and extract metadata"""
    filename_lower = filename.lower()
    source = url or filename

    # Check magic bytes
    if data[:3] == b'\xff\xd8\xff' or data[:8] == b'\x89PNG\r\n\x1a\n':
        return extract_image_metadata(data, filename)
    elif data[:4] == b'%PDF':
        return extract_pdf_metadata(data, filename)
    elif data[:2] in (b'BM',):  # BMP
        return extract_image_metadata(data, filename)
    elif data[:6] in (b'GIF87a', b'GIF89a'):
        return extract_image_metadata(data, filename)
    elif filename_lower.endswith('.pdf'):
        return extract_pdf_metadata(data, filename)
    elif any(filename_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.tiff', '.gif', '.bmp', '.webp']):
        return extract_image_metadata(data, filename)
    else:
        result = MetadataResult(filename=filename, file_type="Unknown", file_size=len(data))
        result.error = "Unsupported file type. Supports: JPEG, PNG, GIF, BMP, PDF"
        return result


def fetch_and_extract(url: str) -> MetadataResult:
    """Download a URL and extract metadata"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, stream=True)
        resp.raise_for_status()

        # Get filename from URL or Content-Disposition
        filename = urlparse(url).path.split('/')[-1] or "downloaded_file"
        content_disp = resp.headers.get('Content-Disposition', '')
        cd_match = re.search(r'filename="?([^";\n]+)"?', content_disp)
        if cd_match:
            filename = cd_match.group(1).strip()

        # Limit download size to 50MB
        content = b''
        for chunk in resp.iter_content(chunk_size=65536):
            content += chunk
            if len(content) > 50 * 1024 * 1024:
                break

        result = extract_metadata_from_bytes(content, filename, url)
        result.source = 'url'
        return result

    except Exception as e:
        result = MetadataResult(source='url')
        result.error = str(e)
        return result


class MetadataThread(QThread):
    progress = pyqtSignal(str)
    result_ready = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, source: str, is_url: bool = True):
        super().__init__()
        self.source = source.strip()
        self.is_url = is_url

    def run(self):
        try:
            if self.is_url:
                self.progress.emit(f"Downloading: {self.source[:60]}...")
                result = fetch_and_extract(self.source)
            else:
                self.progress.emit(f"Reading file: {self.source}...")
                with open(self.source, 'rb') as f:
                    data = f.read()
                result = extract_metadata_from_bytes(
                    data, os.path.basename(self.source)
                )
                result.source = 'file'

            self.progress.emit("Metadata extraction complete.")
            self.result_ready.emit(result)
        except Exception as e:
            self.error.emit(str(e))
