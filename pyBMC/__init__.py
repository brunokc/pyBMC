
import os

from flask import Flask

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    # app.config.from_mapping(
    #     SECRET_KEY="dev",
    #     DATABASE=os.path.join(app.instance_path, "pyBMC.sqlite"),
    # )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route("/state")
    def get_state():
        return {
        
        }

    @app.route("/")
    def hello():
        return f"Hello from {__name__}"

    return app
