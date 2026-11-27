"""
Inspector Rabbit - Metadata Extractor Module
EXIF/GPS/XMP from images (JPEG, PNG, TIFF, WebP, HEIC via Pillow where
supported), PDF document info + XMP, and Office Open XML (DOCX/XLSX/PPTX)
core/app properties. Every file is fingerprinted with SHA-256/MD5.
"""

import io
import os
import re
import hashlib
import zipfile
from typing import Dict, List
from dataclasses import dataclass, field
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import requests
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from . import net

HEADERS = {'User-Agent': net.BROWSER_UA}
MAX_DOWNLOAD = 50 * 1024 * 1024


@dataclass
class MetadataResult:
    filename: str = ""
    file_type: str = ""          # human-readable, e.g. "Image/JPEG"
    kind: str = ""               # image | pdf | office | unknown
    file_size: int = 0
    sha256: str = ""
    md5: str = ""
    source: str = ""             # 'file' or 'url'
    exif_data: Dict = field(default_factory=dict)
    gps_data: Dict = field(default_factory=dict)
    document_meta: Dict = field(default_factory=dict)
    raw_tags: Dict = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> Dict:
        """Flat dict used by the GUI widgets."""
        d = {
            'filename': self.filename,
            'file_type': self.kind or 'unknown',
            'file_format': self.file_type,
            'file_size': self.file_size,
            'sha256': self.sha256,
            'md5': self.md5,
            'source': self.source,
            'warnings': list(self.warnings),
            'error': self.error,
            'gps': dict(self.gps_data),
            'exif': dict(self.exif_data),
            'document': dict(self.document_meta),
            'raw_tags': dict(self.raw_tags),
        }
        ex = self.exif_data
        d.update({
            'make': ex.get('Make', ''), 'model': ex.get('Model', ''),
            'software': ex.get('Software', ''),
            'datetime': ex.get('DateTimeOriginal') or ex.get('DateTime', ''),
            'width': self.raw_tags.get('width', ''), 'height': self.raw_tags.get('height', ''),
            'color_space': self.raw_tags.get('image_mode', ''),
        })
        dm = {k.lower().replace(' ', '_'): v for k, v in self.document_meta.items()}
        for k in ('title', 'author', 'creator', 'producer', 'subject', 'keywords',
                  'creation_date', 'modification_date', 'pages', 'encrypted',
                  'last_modified_by', 'company', 'application', 'revision'):
            if dm.get(k):
                d[k] = dm[k]
        return d


def _rat(x) -> float:
    try:
        if isinstance(x, tuple) and len(x) == 2:
            return x[0] / x[1] if x[1] else 0.0
        return float(x)
    except Exception:
        return 0.0


def _dms_to_deg(dms, ref) -> float:
    try:
        deg = _rat(dms[0]) + _rat(dms[1]) / 60 + _rat(dms[2]) / 3600
        if str(ref).upper().startswith(('S', 'W')):
            deg = -deg
        return round(deg, 7)
    except Exception:
        return 0.0


def _clean_val(v, n=200) -> str:
    if isinstance(v, bytes):
        try:
            v = v.decode('utf-16-le' if v[1:2] == b'\x00' else 'utf-8', errors='ignore').rstrip('\x00')
        except Exception:
            v = repr(v[:40])
    return str(v).strip()[:n]


def _parse_xmp(xmp: str, out: Dict) -> None:
    for tag, label in [('dc:creator', 'XMP Creator'), ('dc:description', 'XMP Description'),
                       ('dc:title', 'XMP Title'), ('xmp:CreatorTool', 'XMP Creator Tool'),
                       ('photoshop:City', 'XMP City'), ('photoshop:Country', 'XMP Country'),
                       ('xmpMM:DocumentID', 'XMP Document ID'), ('xmp:CreateDate', 'XMP Create Date'),
                       ('pdf:Producer', 'XMP Producer')]:
        m = re.search(rf'<{tag}[^>]*>(?:\s*<rdf:\w+>\s*<rdf:li[^>]*>)?([^<]+)', xmp)
        if not m:
            m = re.search(rf'{tag}="([^"]+)"', xmp)
        if m and m.group(1).strip():
            out[label] = m.group(1).strip()[:200]


def extract_image_metadata(data: bytes, filename: str = "") -> MetadataResult:
    result = MetadataResult(filename=filename, file_size=len(data), kind='image')
    try:
        from PIL import Image, ExifTags
        img = Image.open(io.BytesIO(data))
        result.file_type = f"Image/{img.format}"
        result.raw_tags.update({'width': img.width, 'height': img.height,
                                'image_mode': img.mode, 'image_format': img.format,
                                'image_size': f"{img.width}x{img.height}"})

        exif = img.getexif()
        tags = ExifTags.TAGS
        for tag_id, value in exif.items():
            name = tags.get(tag_id, str(tag_id))
            if name in ('ExifOffset', 'GPSInfo'):
                continue
            result.exif_data[name] = _clean_val(value)
        try:
            for tag_id, value in exif.get_ifd(ExifTags.IFD.Exif).items():
                name = tags.get(tag_id, str(tag_id))
                if name in ('MakerNote',):
                    continue
                result.exif_data[name] = _clean_val(value)
        except Exception:
            pass

        try:
            gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
        except Exception:
            gps = {}
        if gps:
            named = {ExifTags.GPSTAGS.get(k, str(k)): v for k, v in gps.items()}
            result.exif_data['GPSInfo'] = {k: _clean_val(v, 80) for k, v in named.items()}
            if 'GPSLatitude' in named and 'GPSLongitude' in named:
                lat = _dms_to_deg(named['GPSLatitude'], named.get('GPSLatitudeRef', 'N'))
                lon = _dms_to_deg(named['GPSLongitude'], named.get('GPSLongitudeRef', 'E'))
                if lat or lon:
                    result.gps_data = {
                        'latitude': lat, 'longitude': lon,
                        'maps_url': f"https://maps.google.com/?q={lat},{lon}",
                        'lat_ref': str(named.get('GPSLatitudeRef', '')),
                        'lon_ref': str(named.get('GPSLongitudeRef', '')),
                    }
                    if 'GPSAltitude' in named:
                        alt = _rat(named['GPSAltitude'])
                        if named.get('GPSAltitudeRef') in (1, b'\x01'):
                            alt = -alt
                        result.gps_data['altitude'] = f"{alt:.1f} m"
                    if 'GPSDateStamp' in named:
                        result.gps_data['date'] = str(named['GPSDateStamp'])
                    result.warnings.append(f"⚠️  GPS LOCATION EMBEDDED: {lat}, {lon}")

        xmp = img.info.get('xmp') or img.info.get('XML:com.adobe.xmp')
        if xmp:
            _parse_xmp(xmp.decode('utf-8', 'ignore') if isinstance(xmp, bytes) else str(xmp),
                       result.document_meta)
        for key, value in img.info.items():
            if key in ('exif', 'xmp', 'icc_profile', 'XML:com.adobe.xmp'):
                continue
            if isinstance(value, (str, int, float)):
                result.raw_tags[f'info_{key}'] = str(value)[:200]
        if img.info.get('icc_profile'):
            result.raw_tags['icc_profile'] = f"{len(img.info['icc_profile'])} bytes"

        for k in ('Make', 'Model', 'Software', 'Artist', 'XPAuthor', 'HostComputer',
                  'BodySerialNumber', 'CameraOwnerName', 'LensSerialNumber'):
            if result.exif_data.get(k):
                result.warnings.append(f"Identifying tag {k}: {result.exif_data[k]}")
        if not result.exif_data and not result.document_meta:
            result.warnings.append("No EXIF/XMP metadata (stripped or never present)")
    except ImportError:
        result.error = "Pillow library not installed"
    except Exception as e:
        result.error = f"Image metadata error: {e}"
    return result


def extract_pdf_metadata(data: bytes, filename: str = "") -> MetadataResult:
    result = MetadataResult(filename=filename, file_type="PDF", kind='pdf', file_size=len(data))
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            result.document_meta['Encrypted'] = 'Yes'
            result.warnings.append("⚠️  PDF is encrypted")
            try:
                reader.decrypt('')
            except Exception:
                pass
        meta = reader.metadata
        if meta:
            for key, val in meta.items():
                label = key.lstrip('/')
                label = {'CreationDate': 'Creation Date', 'ModDate': 'Modification Date'}.get(label, label)
                result.document_meta[label] = _clean_val(val)
        result.document_meta['Pages'] = str(len(reader.pages))
        try:
            xmp = reader.xmp_metadata
            if xmp is not None:
                raw = xmp.stream.get_data().decode('utf-8', 'ignore')
                _parse_xmp(raw, result.document_meta)
        except Exception:
            pass
        try:
            text = (reader.pages[0].extract_text() or '')[:600]
            if text:
                result.raw_tags['first_page_preview'] = text
        except Exception:
            pass
        for k in ('Author', 'Creator', 'Producer'):
            if result.document_meta.get(k):
                result.warnings.append(f"Identifying field {k}: {result.document_meta[k]}")
    except ImportError:
        result.error = "pypdf library not installed. Run: pip3 install pypdf"
    except Exception as e:
        result.error = f"PDF metadata error: {e}"
    return result


_NS = {
    'cp': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dcterms': 'http://purl.org/dc/terms/',
    'ep': 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties',
}


def extract_office_metadata(data: bytes, filename: str = "") -> MetadataResult:
    result = MetadataResult(filename=filename, kind='office', file_size=len(data))
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        names = set(z.namelist())
        if 'word/document.xml' in names:
            result.file_type = 'Office/DOCX'
        elif 'xl/workbook.xml' in names:
            result.file_type = 'Office/XLSX'
        elif 'ppt/presentation.xml' in names:
            result.file_type = 'Office/PPTX'
        else:
            result.file_type = 'ZIP archive'
            result.kind = 'unknown'
            result.raw_tags['entries'] = len(names)
            return result
        if 'docProps/core.xml' in names:
            root = ET.fromstring(z.read('docProps/core.xml'))
            for tag, label in [('dc:title', 'Title'), ('dc:subject', 'Subject'),
                               ('dc:creator', 'Author'), ('cp:keywords', 'Keywords'),
                               ('dc:description', 'Description'), ('cp:lastModifiedBy', 'Last Modified By'),
                               ('cp:revision', 'Revision'), ('dcterms:created', 'Creation Date'),
                               ('dcterms:modified', 'Modification Date'), ('cp:category', 'Category')]:
                el = root.find(tag, _NS)
                if el is not None and (el.text or '').strip():
                    result.document_meta[label] = el.text.strip()[:200]
        if 'docProps/app.xml' in names:
            root = ET.fromstring(z.read('docProps/app.xml'))
            for tag, label in [('Application', 'Application'), ('AppVersion', 'App Version'),
                               ('Company', 'Company'), ('Manager', 'Manager'),
                               ('TotalTime', 'Total Editing Minutes'), ('Pages', 'Pages'),
                               ('Words', 'Words'), ('Template', 'Template')]:
                el = root.find(f'ep:{tag}', _NS)
                if el is not None and (el.text or '').strip():
                    result.document_meta[label] = el.text.strip()[:200]
        if 'docProps/custom.xml' in names:
            result.raw_tags['custom_properties'] = 'present'
        if 'word/comments.xml' in names:
            result.warnings.append("Document contains reviewer comments")
        media = [n for n in names if '/media/' in n]
        if media:
            result.raw_tags['embedded_media'] = len(media)
        for k in ('Author', 'Last Modified By', 'Company', 'Manager'):
            if result.document_meta.get(k):
                result.warnings.append(f"Identifying field {k}: {result.document_meta[k]}")
    except zipfile.BadZipFile:
        result.error = "Corrupt or non-OOXML zip file"
    except Exception as e:
        result.error = f"Office metadata error: {e}"
    return result


def extract_metadata_from_bytes(data: bytes, filename: str = "", url: str = "") -> MetadataResult:
    name = filename.lower()
    if data[:3] == b'\xff\xd8\xff' or data[:8] == b'\x89PNG\r\n\x1a\n' or data[:6] in (b'GIF87a', b'GIF89a') \
            or data[:2] == b'BM' or data[:4] in (b'II*\x00', b'MM\x00*') \
            or (data[:4] == b'RIFF' and data[8:12] == b'WEBP') or data[4:12] in (b'ftypheic', b'ftypheix', b'ftypmif1'):
        r = extract_image_metadata(data, filename)
    elif data[:5] == b'%PDF-':
        r = extract_pdf_metadata(data, filename)
    elif data[:4] == b'PK\x03\x04':
        r = extract_office_metadata(data, filename)
    elif name.endswith('.pdf'):
        r = extract_pdf_metadata(data, filename)
    elif name.endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.gif', '.bmp', '.webp', '.heic')):
        r = extract_image_metadata(data, filename)
    else:
        r = MetadataResult(filename=filename, file_type="Unknown", kind='unknown', file_size=len(data))
        head = data[:200].lstrip().lower()
        if head.startswith((b'<!doctype html', b'<html')):
            r.error = "URL returned an HTML page, not a file (login wall, redirect or viewer page?)"
        else:
            r.error = "Unsupported file type. Supports: JPEG, PNG, TIFF, WebP, GIF, BMP, HEIC, PDF, DOCX, XLSX, PPTX"
    r.sha256 = hashlib.sha256(data).hexdigest()
    r.md5 = hashlib.md5(data).hexdigest()
    return r


def download(url: str):
    """Download up to 50 MB. Returns (bytes, filename)."""
    resp = requests.get(url, headers=HEADERS, timeout=20, stream=True, allow_redirects=True)
    resp.raise_for_status()
    filename = os.path.basename(urlparse(resp.url).path) or "downloaded_file"
    cd = resp.headers.get('Content-Disposition', '')
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";\n]+)"?', cd)
    if m:
        filename = os.path.basename(m.group(1).strip())
    buf = bytearray()
    for chunk in resp.iter_content(chunk_size=65536):
        buf.extend(chunk)
        if len(buf) > MAX_DOWNLOAD:
            raise ValueError("File larger than 50 MB — download aborted")
    return bytes(buf), filename


def fetch_and_extract(url: str) -> MetadataResult:
    try:
        data, filename = download(url)
        result = extract_metadata_from_bytes(data, filename, url)
        result.source = 'url'
        return result
    except Exception as e:
        result = MetadataResult(source='url', filename=url)
        result.error = f"Download failed: {e}"
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
                result = extract_metadata_from_bytes(data, os.path.basename(self.source))
                result.source = 'file'
            self.progress.emit("Metadata extraction complete.")
            self.result_ready.emit(result)
        except Exception as e:
            self.error.emit(str(e))
