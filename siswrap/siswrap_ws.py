import tornado.ioloop
import tornado.web
import jsonpickle
from .siswrap import ProcessService, Logger, ProcessInfo, Wrapper
from .configuration import ConfigurationService
import os
import click


class BaseHandler(tornado.web.RequestHandler):
    """ Our base Tornado process handler.
    """

    HTTP_OK = 200
    HTTP_ACCEPTED = 202
    HTTP_ERROR = 500

    def write_object(self, obj, http_code=200, reason="OK"):
        self.set_status(http_code, reason)
        self.set_header("Content-Type", "application/json")
        resp = jsonpickle.encode(obj, unpicklable=False)
        self.write(resp)

    # Respond with different HTTP messages depending on the return code
    # from the process. Used when polling the status.
    def write_status(self, proc_info):

        # Write output for specific process
        if type(proc_info) is dict:
            state = proc_info.get("state")

            if state == ProcessInfo.STATE_STARTED:
                self.write_object(proc_info, self.HTTP_OK,
                                  "OK - still processing")
            elif state == ProcessInfo.STATE_DONE:
                self.write_object(proc_info, self.HTTP_OK,
                                  "OK - finished processing")
            elif state == ProcessInfo.STATE_ERROR:
                self.write_object(proc_info, self.HTTP_OK,
                                  "OK - but error occured while processing")
            else:
                self.write_object(proc_info, self.HTTP_ERROR,
                                  "An error occurred")
        # Write output for all processes
        else:
            self.write_object(proc_info, self.HTTP_OK, "OK")

    # When responding to the initial POST request we should answer with 202
    # if successful
    def write_accepted(self, proc_info):
        state = proc_info.get("state")

        if state == ProcessInfo.STATE_STARTED:
            self.write_object(proc_info, self.HTTP_ACCEPTED,
                              "Request accepted")
        else:
            self.write_object(proc_info, self.HTTP_ERROR, "An error occurred")

    def append_status_link(self, wrapper):
        wrapper.info.link = self.create_status_link(wrapper.type_txt,
                                                    wrapper.info.pid)

    def create_status_link(self, wrapper, pid):
        return "%s/%s/status/%s" % (self.api_link(), wrapper, pid)

    def api_link(self, version="1.0"):
        return "%s://%s/api/%s" % (self.request.protocol, self.request.host,
                                   version)


class RunHandler(BaseHandler):
    """ Our handler for requesting the launch of a new quick report and
        quality control.

        Args:
            runfolder: Which runfolder to generate a report or quality control
                       for.

        Returns:
            A status code HTTP 202 if the report generation or quality control
            is initialised successfully, and a JSON response including a link
            to the status page to poll. An error code HTTP 500 otherwise.

        Raises:
            RuntimeError if an empty POST body was sent in, or an unknown
            wrapper runner was requested.
    """
    def post(self, runfolder="/some/runfolder"):
        try:
            url = self.request.uri.strip()
            payload = {}

            if self.request.body:
                payload = jsonpickle.decode(self.request.body)
                runfolder = payload.get("runfolder").strip()
            else:
                raise RuntimeError("Cannot handle empty request body")

            # Return a new wrapper object depending on what was requested in
            # the URL, and then ask the process service to start execution.
            wrapper_type = Wrapper.url_to_type(url)
            wrapper = Wrapper.new_wrapper(wrapper_type, str(runfolder),
                                          SisApp.config_svc, SisApp.logger)
            result = SisApp.process_svc.run(wrapper)

            self.append_status_link(result)
            resp = {"pid": result.info.pid,
                    "state": result.info.state,
                    "host": result.info.host,
                    "runfolder": result.info.runfolder,
                    "link": result.info.link,
                    "msg": result.info.msg}
            self.write_accepted(resp)
        except RuntimeError, err:
            self.write_object("An error ocurred: " + str(err),
                              http_code=500, reason="An error occurred")


class StatusHandler(BaseHandler):
    """ Our handler for checking on the status of the report generation or
        quality control.

        Args:
            id: The ID of the process to check status of.
            Or empty if all processes should be returned.

        Returns:
            JSON with fields that describe current status for requested
            process. List of dicts with Current status of all the processes
            if input parameter was non-existant.
    """
    def get(self, pid):
        try:
            url = self.request.uri
            wrapper_type = Wrapper.url_to_type(url)

            # Get status for a specific PID and wrapper type
            if pid:
                response = SisApp.process_svc.get_status(int(pid),
                                                         wrapper_type)

                payload = {"pid": response.pid,
                           "state": response.state,
                           "host": response.host,
                           "msg": response.msg}

                # If the process was found then we also want to return
                # the runfolder
                if response.state is not ProcessInfo.STATE_NONE:
                    temp = payload.copy()
                    temp.update({"runfolder": response.runfolder})
                    payload = temp

                self.write_status(payload)
            else:
                # If a specific PID wasn't requested then return all
                # processes of the specific wrapper type
                self.write_status(SisApp.process_svc.get_all(wrapper_type))
        except RuntimeError, err:
            self.write_object("An error occurred: " + str(err))


class ApiHelpEntry(object):
    def __init__(self, link, description):
        self.link = self.prefix + link
        self.description = description


class ApiHelpHandler(BaseHandler):
    def get(self):
        ApiHelpEntry.prefix = self.api_link()
        doc = [
            ApiHelpEntry("/qc/run/runfolder",
                         "Run Sisyphus quality control for runfolder"),
            ApiHelpEntry("/qc/status/",
                         "Check status of all running Sisyphus quality control jobs"),
            ApiHelpEntry("/qc/status/run_id",
                         "Check status of a specific Sisyphus quality control job"),
            ApiHelpEntry("/report/run/runfolder",
                         "Start Sisyphus quick report for runfolder"),
            ApiHelpEntry("/report/status/",
                         "Check status of all Sisyphus quick reports"),
            ApiHelpEntry("/report/status/run_id",
                         "Check status of Sisyphus quick report with run_id")
        ]
        self.write_object(doc)


class SisApp(object):

    config_svc = None
    process_svc = None
    logger = None

    @classmethod
    def create_app(cls, debug):
        app = tornado.web.Application([
            (r"/api/1.0", ApiHelpHandler),
            (r"/api/1.0/(?:qc|report)/run/([\w_-]+)", RunHandler),
            (r"/api/1.0/(?:qc|report)/status/(\d*)", StatusHandler)
        ], debug=debug)
        return app

    @classmethod
    def start(cls, config, debug):
        if not os.path.isfile(config):
            raise Exception("Can't open config file '{0}'".format(config))

        SisApp.logger = Logger(debug)
        SisApp.config_svc = ConfigurationService(config)
        SisApp.process_svc = ProcessService(cls.config_svc, cls.logger)
        cls.DEBUG = debug

        startmsg = "Starting the runfolder micro service on {0} (debug={1})\
                   ".format(SisApp.config_svc.get_setting("port"), debug)
        SisApp.logger.info(startmsg)

        app = cls.create_app(debug)
        app.listen(SisApp.config_svc.get_setting("port"))
        tornado.ioloop.IOLoop.current().start()

    # For easier integration testing
    # @classmethod
    # def _clear_queue(cls):
    #    if cls.process_svc:
    #        cls.process_svc._clear_queue()


@click.command()
@click.option('--config', default="/opt/siswrap/etc/siswrap.config")
@click.option('--debug/--no-debug', default=False)
def start(config, debug):
    SisApp().start(config, debug)

if __name__ == "__main__":
    start()
