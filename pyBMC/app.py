
import os

from quart import Quart, render_template
from . import version

def create_app(test_config=None):
    app = Quart(__name__.split('.')[0], instance_relative_config=True)
    app.config.from_mapping(
        JSON_SORT_KEYS=False,
        # SECRET_KEY="dev",
        # DATABASE=os.path.join(app.instance_path, "pyBMC.sqlite"),
    )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import api
    app.register_blueprint(api.bp)

    @app.route("/")
    async def index():
        project_name = __name__.split('.')[0]
        project_version = version.__version__
        sensors = api.sensors
        return await render_template("main.html", **locals())

    return app
