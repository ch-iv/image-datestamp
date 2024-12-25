from flask import (
    Blueprint,
    flash,
    request,
    redirect,
    url_for,
    session,
    render_template,
)
from timestamp import FileProcessMetadata, batch_process_files, BatchProcessResult
from forms import parse_form
from werkzeug.datastructures.file_storage import FileStorage
from loguru import logger
import uuid
from paths import APP_STATIC_FOLDER

image_upload_blueprint = Blueprint(
    'image_upload',
    __name__,
    template_folder='templates',
    static_folder=APP_STATIC_FOLDER,
)

@image_upload_blueprint.route("/", methods=["GET", "POST"])
def upload_file():
    if "user_id" not in session:
        session["user_id"] = uuid.uuid4().hex
    user_id = session["user_id"]

    logger.info(f"User {user_id} accessed {request.url}")
    if request.method == "POST":
        upload_id = uuid.uuid4().hex
        logger.info(f"User {user_id} posted {upload_id} to {request.url}")

        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)

        files: list[FileStorage] = request.files.getlist("file")
        logger.info(f"User {user_id} uploaded {len(files)} files to {upload_id}")
        datestamp_options = parse_form(request.form)
        batch_process_result: BatchProcessResult = batch_process_files(
            files,
            FileProcessMetadata(
                user_id=user_id, upload_id=upload_id, datestamp_opts=datestamp_options
            ),
        )

        if not batch_process_result.critical_failure:
            logger.info(f"User {user_id}; {upload_id} successfully processed files.")
        else:
            logger.info(f"User {user_id}; {upload_id} critical failure.")

        return render_template(
            "index.html",
            batch_process_result=batch_process_result,
            download_url=url_for(
                "user_content.download",
                user_id=user_id,
                upload_id=upload_id,
                filename=batch_process_result.output_filename,
            )
        )

    return render_template("index.html")