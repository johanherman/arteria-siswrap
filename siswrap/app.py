from tornado.web import URLSpec as url

from arteria.web.app import AppService
from siswrap.handlers import RunHandler, StatusHandler
from siswrap.wrapper_services import ProcessService


def routes(**kwargs):
    return [
        url(r"/api/1.0/(?:qc|report|aeacusstats|aeacusreports)/run/([\w_-]+)",
            RunHandler, name="run", kwargs=kwargs),
        url(r"/api/1.0/(?:qc|report|aeacusstats|aeacusreports)/status/(\d*)",
            StatusHandler, name="status", kwargs=kwargs)]

def start():
    app_svc = AppService.create(__package__)
    process_svc = ProcessService(app_svc.config_svc)

    # Setup the routing. Help will be automatically available at /api, and will
    # be based on the doc strings of the get/post/put/delete methods
    app_svc.start(routes(process_svc=process_svc, config_svc=app_svc.config_svc))
