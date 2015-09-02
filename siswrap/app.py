from arteria.web.app import AppService
from siswrap.handlers import RunHandler, StatusHandler
from siswrap.wrapper_services import ProcessService


def start():
    app_svc = AppService.create(__package__)
    process_svc = ProcessService(app_svc.config_svc)

    # Setup the routing. Help will be automatically available at /api, and will
    # be based on the doc strings of the get/post/put/delete methods
    args = dict(process_svc=process_svc, config_svc=app_svc.config_svc)
    routes = [
        (r"/api/1.0/(?:qc|report)/run/([\w_-]+)", RunHandler, args),
        (r"/api/1.0/(?:qc|report)/status/(\d*)", StatusHandler, args)
    ]
    app_svc.start(routes)
