import enum

from PIL import Image, ImageDraw, ExifTags, ImageFont
from pathlib import Path
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
import zipfile
from config.paths import input_file_dest, output_file_dest
from werkzeug.datastructures.file_storage import FileStorage
import uuid
from werkzeug.utils import secure_filename
from dataclasses import dataclass
from io import BytesIO
from os import fspath
from shutil import copyfileobj
from config.paths import FontPaths

ALLOWED_EXTENSIONS = {"jpg", "jpeg"}


EXIF_MODIFY_DATE = 0x0132
DATE_TIME_ORIGINAL = 0x9003
CREATE_DATE = 0x9004


def get_create_date(im: Image) -> str | None:
    """Attempts to extract the creation date from the image's EXIF metadata
    The date is returned on first-found basis in order CREATE_DATE -> DATE_TIME_ORIGINAL _>  GPS_DATE_STAMP -> EXIF_MODIFY_DATE

    :param im: Image to extract date from
    :return: Create date of the image
    """
    exif: Image.Exif = im.getexif()

    if CREATE_DATE in exif:
        return exif[CREATE_DATE]

    if DATE_TIME_ORIGINAL in exif:
        return exif[DATE_TIME_ORIGINAL]

    ifd_date_time_original = exif.get_ifd(ExifTags.IFD.Exif).get(DATE_TIME_ORIGINAL)
    if ifd_date_time_original is not None:
        return ifd_date_time_original

    gps_info: dict = exif.get_ifd(ExifTags.IFD.GPSInfo)
    if ExifTags.GPS.GPSDateStamp in gps_info:
        return gps_info[ExifTags.GPS.GPSDateStamp]

    if EXIF_MODIFY_DATE in exif:
        return exif[EXIF_MODIFY_DATE]

    return None


def format_datestamp(date: str) -> str:
    return date.replace(":", "/").split(" ")[0]


def test_get_create_date():
    all_paths = list((Path(__file__).parent / "test_images").iterdir())
    image_paths = list(filter(lambda x: x.suffix == ".jpg", all_paths))

    for image_path in image_paths:
        with Image.open(image_path) as im:
            print(image_path, get_create_date(im))


class DateStampPosition(enum.Enum):
    NORTH_EAST = (1, 0)
    NORTH_WEST = (0, 0)
    SOUTH_EAST = (1, 1)
    SOUTH_WEST = (0, 1)


def draw_datestamp(
    im: Image.Image,
    datestamp: str = "",
    position: DateStampPosition = DateStampPosition.NORTH_WEST,
    color: tuple[int, int, int, int] = (255, 239, 120, 255),
    font_path: Path | None = None,
    font_scaling_factor: float = 0.05,
    margin_scaling_factor: float = 0.05,
) -> Image:
    if font_path is None:
        print(FontPaths.DEFAULT)
        font_path = FontPaths.DEFAULT
    drawing_context = ImageDraw.Draw(im)
    font_size = int(im.width * font_scaling_factor)
    font = ImageFont.truetype(font_path, font_size)
    text_length = font.getlength(datestamp)
    text_ascent, _ = font.getmetrics()
    margin_width = im.width * margin_scaling_factor
    margin_height = im.height * margin_scaling_factor

    stamp_width = position.value[0] * im.width
    stamp_height = position.value[1] * im.height

    match position:
        case DateStampPosition.SOUTH_WEST:
            stamp_height -= font_size
            stamp_height -= margin_height
            stamp_width += margin_width
        case DateStampPosition.SOUTH_EAST:
            stamp_height -= font_size
            stamp_width -= text_length
            stamp_height -= margin_height
            stamp_width -= margin_width
        case DateStampPosition.NORTH_EAST:
            stamp_width -= text_length
            stamp_height += margin_height
            stamp_width -= margin_width
        case DateStampPosition.NORTH_WEST:
            stamp_height -= font_size - text_ascent
            stamp_height += margin_height
            stamp_width += margin_width

    drawing_context.text((stamp_width, stamp_height), datestamp, font=font, fill=color)
    return im


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@dataclass
class FileProcessMetadata:
    user_id: str
    upload_id: str
    datestamp_opts: dict


@dataclass
class FileProcessResult:
    filename: str
    success: bool
    reason: str
    output_dest: Path | None
    input_dest: Path | None


@dataclass
class BatchProcessResult:
    successful: list[FileProcessResult]
    unsuccessful: list[FileProcessResult]
    critical_failure: bool
    output_filename: str
    reason: str
    user_id: str
    upload_id: str


def save_file_stream(stream: BytesIO, dst, buffer_size=16384):
    close_dst = False

    if hasattr(dst, "__fspath__"):
        dst = fspath(dst)

    if isinstance(dst, str):
        dst = open(dst, "wb")
        close_dst = True

    try:
        copyfileobj(stream, dst, buffer_size)
    finally:
        if close_dst:
            dst.close()


def batch_process_files(
    files: list[FileStorage], shared_metadata: FileProcessMetadata
) -> BatchProcessResult:
    result = BatchProcessResult(
        successful=[],
        unsuccessful=[],
        critical_failure=False,
        output_filename="",
        reason="",
        user_id="",
        upload_id="",
    )
    result.user_id = shared_metadata.user_id
    result.upload_id = shared_metadata.upload_id

    with ThreadPool(cpu_count()) as pool:
        results = pool.starmap(
            process_file,
            zip(
                map(lambda x: x.stream, files),
                map(lambda x: x.filename, files),
                [shared_metadata] * len(files),
            ),
        )

    if len(results) == 0:
        result.critical_failure = True
        result.reason = "No files were processed."
        return result

    for res in results:
        if res.success:
            result.successful.append(res)
        else:
            result.unsuccessful.append(res)

    if len(result.successful) == 0:
        result.critical_failure = True
        result.reason = "No files were processed successfully."
        return result

    if len(result.successful) == 1:
        result.output_filename = result.successful[0].filename
        result.success = True
    else:
        # compress files from the input directory and save the zip in the output directory
        filename = uuid.uuid4().hex + ".zip"
        output_dest = output_file_dest(
            user_id=shared_metadata.user_id,
            upload_id=shared_metadata.upload_id,
            filename=filename,
        )

        with zipfile.ZipFile(output_dest, "w", zipfile.ZIP_DEFLATED) as my_zip:
            for res in result.successful:
                my_zip.write(res.output_dest, arcname=res.filename)

        result.output_filename = filename
        result.success = True

    return result


def process_file(
    stream: BytesIO, filename: str, metadata: FileProcessMetadata
) -> FileProcessResult:
    result = FileProcessResult(
        filename="", success=False, reason="", output_dest=None, input_dest=None
    )

    if filename == "":
        result.filename = "empty"
        result.success = False
        result.reason = "No file was provided."
        return result

    if not allowed_file(filename):
        result.filename = filename
        result.success = False
        result.reason = "File extension is not allowed."
        return result

    result.filename = secure_filename(filename)

    input_dest = input_file_dest(
        user_id=metadata.user_id, upload_id=metadata.upload_id, filename=result.filename
    )

    output_dest = output_file_dest(
        user_id=metadata.user_id, upload_id=metadata.upload_id, filename=result.filename
    )

    save_file_stream(stream, input_dest)

    with Image.open(input_dest) as im:
        datestamp = get_create_date(im)

        if datestamp is None:
            result.success = False
            result.reason = "Couldn't extract datestamp metadata"
            return result

        datestamp = format_datestamp(datestamp)
        im = draw_datestamp(im, datestamp=datestamp, **metadata.datestamp_opts)
        im.save(output_dest)

        result.success = True
        result.output_dest = output_dest
        result.input_dest = input_dest

    return result
