from flask import Flask
import uuid
from paths import USER_CONTENT_DIR
from loguru import logger

from blueprints.user_content_blueprint import user_content_blueprint
from blueprints.image_upload_blueprint import image_upload_blueprint

logger.add("logs/log_{time}.log", rotation="1 MB")

app = Flask(__name__)

app.config["UPLOAD_FOLDER"] = USER_CONTENT_DIR
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024
app.config["SECRET_KEY"] = uuid.uuid4().hex

app.register_blueprint(image_upload_blueprint)
app.register_blueprint(user_content_blueprint)

if __name__ == "__main__":
    app.run(debug=True)
