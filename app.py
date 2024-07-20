from flask import (
    Flask,
    flash,
    request,
    redirect,
    url_for,
    send_from_directory,
    session,
    render_template,
)

import uuid

from .paths import USER_CONTENT_DIR
from .timestamp import FileProcessMetadata, batch_process_files, BatchProcessResult
from .forms import parse_form
from werkzeug.datastructures.file_storage import FileStorage
from loguru import logger

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = USER_CONTENT_DIR
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024
app.config["SECRET_KEY"] = uuid.uuid4().hex
logger.add("logs/log_{time}.log", rotation="1 MB")

@app.route("/", methods=["GET", "POST"])
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
            return redirect(
                url_for(
                    "download_file",
                    user_id=user_id,
                    upload_id=upload_id,
                    filename=batch_process_result.output_filename,
                )
            )
        else:
            logger.info(f"User {user_id}; {upload_id} critical failure.")
            return redirect(request.url)

    return render_template("index.html")


@app.route("/uploads/<user_id>/<upload_id>/<filename>")
def download_file(user_id: str, upload_id: str, filename: str):
    output_path = app.config["UPLOAD_FOLDER"] / "out" / user_id / upload_id
    return send_from_directory(output_path, filename)


app.add_url_rule("/uploads/<name>", endpoint="download_file", build_only=True)

if __name__ == "__main__":
    app.run(debug=True)
