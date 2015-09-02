import jsonpickle
import arteria
from arteria.web.handlers import BaseRestHandler
from arteria.web.state import State
from wrapper_services import ProcessService, Wrapper, ProcessInfo


class BaseSiswrapHandler(BaseRestHandler):
    """ Provides core logic for Siswrap handlers
    """

    HTTP_OK = 200
    HTTP_ACCEPTED = 202
    HTTP_ERROR = 500

    # FIXME: This should probably be documented in arteria core.
    def initialize(self, process_svc, config_svc):
        self.process_svc = process_svc
        self.config_svc = config_svc

    def write_status(self, proc_info):
        """
        Respond with different HTTP messages depending on the return code
        from the process. Used when polling the status.

        Args:
            proc_info: the ProcessInfo to check so we know what kind of respond to send
        """
        http_code = self.HTTP_OK
        reason = "OK"

        # Write output for specific process
        if type(proc_info) is dict:
            state = proc_info.get("state")

            if state == State.STARTED:
                reason = "OK - still processing"
            elif state == State.DONE:
                reason = "OK - finished processing"
            elif state == State.ERROR:
                reason = "OK - but an error occured while processing"
            else:
                http_code = self.HTTP_ERROR
                reason = "An unexpected error occured"
        # Write output for all processes
        else:
            reason = "OK"

        self.set_status(http_code, reason)
        self.write_object(proc_info)

    def write_accepted(self, proc_info):
        """
        When responding to the initial POST request we should answer with 202
        if successful

        Args:
            proc_info: the ProcessInfo to write back to the client
        """
        state = proc_info.get("state")
        http_code = self.HTTP_OK
        reason = "OK"

        if state == State.STARTED:
            http_code = self.HTTP_ACCEPTED
            reason = "Request accepted"
        else:
            http_code = self.HTTP_ERROR
            reason = "An unexpected error occurred"

        self.set_status(http_code, reason)
        self.write_object(proc_info)

    def append_status_link(self, wrapper):
        wrapper.info.link = self.create_status_link(wrapper.type_txt,
                                                    wrapper.info.pid)

    def create_status_link(self, wrapper, pid):
        return "%s/%s/status/%s" % (self.api_link(), wrapper, pid)


class RunHandler(BaseSiswrapHandler):
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

            expect_param = ["runfolder"]
            body = self.body_as_object(expect_param)
            runfolder = body["runfolder"].strip()

            # Return a new wrapper object depending on what was requested in
            # the URL, and then ask the process service to start execution.
            wrapper_type = Wrapper.url_to_type(url)
            wrapper = Wrapper.new_wrapper(wrapper_type, str(runfolder),
                                          self.config_svc)
            result = self.process_svc.run(wrapper)

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


class StatusHandler(BaseSiswrapHandler):
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
                response = self.process_svc.get_status(int(pid), wrapper_type)

                payload = {"pid": response.pid,
                           "state": response.state,
                           "host": response.host,
                           "msg": response.msg}

                # If the process was found then we also want to return
                # the runfolder
                if response.state is not State.NONE:
                    temp = payload.copy()
                    temp.update({"runfolder": response.runfolder})
                    payload = temp

                self.write_status(payload)
            else:
                # If a specific PID wasn't requested then return all
                # processes of the specific wrapper type
                self.write_status(self.process_svc.get_all(wrapper_type))
        except RuntimeError, err:
            self.write_object("An error occurred: " + str(err))
