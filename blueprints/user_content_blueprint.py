from flask import Blueprint, current_app, send_from_directory

user_content_blueprint = Blueprint(
    "user_content",
    __name__,
    url_prefix="/user_content",
)


@user_content_blueprint.route("download/<user_id>/<upload_id>/<filename>")
def download(user_id: str, upload_id: str, filename: str):
    output_path = current_app.config["UPLOAD_FOLDER"] / "out" / user_id / upload_id
    return send_from_directory(output_path, filename)
