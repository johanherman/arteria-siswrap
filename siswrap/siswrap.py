import os.path
from .configuration import ConfigurationService
import socket
import subprocess

""" Simple wrapper for the Sisyphus tools suite.
"""


# TODO: Temporary - will be replaced with logging framework
class Logger:
    DEBUG = False

    def __init__(self, debug):
        self.DEBUG = debug

    def debug(self, msg): print msg if self.DEBUG else None

    def info(self, msg): print msg

    def warn(self, msg): print msg

    def error(self, msg): print msg


class ProcessInfo(object):
    """Information about a process.

        State can be:
            none: Not ready for processing or invalid
            ready: Ready for processing by Arteria
            started: Arteria started processing the runfolder
            done: Arteria is done processing the runfolder
            error: Arteria started processing the runfolder but there was an
                   error; see property msg for details

        Also keeps track of other meta data for the process.
    """
    STATE_NONE = "none"
    STATE_READY = "ready"
    STATE_STARTED = "started"
    STATE_DONE = "done"
    STATE_ERROR = "error"

    def __init__(self, runfolder=None, host=None, state=STATE_NONE,
                 proc=None, msg=None, pid=None):
        self.runfolder = runfolder
        self.host = host
        self.state = state
        self.proc = proc
        self.msg = msg
        self.pid = pid
        self.link = None

    def __str__(self):
        return "{0} {3}: {1}@{2}".format(self.state, self.runfolder,
                                         self.host, self.pid)

    # Update the appropriate meta data for the process when it has been started
    def set_started(self, proc):
        self.host = ProcessService._host()
        self.state = self.STATE_STARTED
        self.proc = proc
        self.msg = "Process has been started"
        self.pid = proc.pid

    # Return an empty process information container if a non valid PID
    # was requested
    @staticmethod
    def none_process(pid):
        return ProcessInfo(host=ProcessService._host(), pid=pid,
                           state=ProcessInfo.STATE_NONE,
                           msg="No such process exists")


class ExecString(object):
    """ Object for storing the string that will be executed. Content is semi
        standardised, as the called Perl scripts almost looks the same. It will
        vary somewhat depending on which wrapper is creating the object.

         Args:
            wrapper: the object creating ExecString
            conf_svc: the ConfigurationService serving our config lookups
            runfolder: which runfolder to use

         Returns:
            Sets its property 'text' to the string that will be executed
            in a subprocess.
     """
    def __init__(self, wrapper, conf_svc, runfolder):
        self.text = None
        bin_lookup = wrapper.binary_conf_lookup
        self.text = [conf_svc.get_setting("perl"),
                     conf_svc.get_setting(bin_lookup),
                     "-runfolder", runfolder,
                     "-mail", conf_svc.get_setting("receiver"),
                     "-sender", conf_svc.get_setting("sender")]


class Wrapper(object):
    """ Our main wrapper for the Sisyphus scripts (QuickReport and
        QualityControl at the moment).

        Args:
            runfolder: the name of the runfolder to use (not full path)
            configuration_svc: the ConfigurationService for our config lookups
            logger: logger object for printouts
    """

    QC_TYPE = "qc"
    REPORT_TYPE = "report"

    def __init__(self, runfolder, configuration_svc, logger):
        runpath = configuration_svc.get_setting("runfolder_root") + runfolder

        if not os.path.isdir(runpath):
            raise OSError("No runfolder {0} exists.".format(runpath))

        self.info = ProcessInfo(runpath)
        self.conf_svc = configuration_svc
        self.logger = logger

    def __get_attr__(self, attr):
        return getattr(self.info, attr)

    def stop(self):
        pass

    # Creates an execution string that will be unique depending on calling
    # object and spawns a subprocess with this.
    def run(self):
        try:
            if os.getenv("ARTERIA_TEST"):
                proc = subprocess.Popen(["/bin/sleep", "1m"])
            else:
                exec_string = ExecString(self, self.conf_svc,
                                         self.info.runfolder).text
                proc = subprocess.Popen(exec_string, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

            self.info.set_started(proc)
            self.logger.info("{0} started for {1} with: {2}".
                             format(type(self), self.info.runfolder,
                                    exec_string))
        except (OSError, ValueError), err:
            self.logger.error("An error occurred in Wrapper for {0}: {1}".
                              format(self.info.runfolder, err))

    # Helper method to see which wrapper object might belong to which URL
    @staticmethod
    def url_to_type(url):
        # TODO: Take out the correct part of the URL instead.
        if Wrapper.QC_TYPE in url:
            return Wrapper.QC_TYPE
        elif Wrapper.REPORT_TYPE in url:
            return Wrapper.REPORT_TYPE
        else:
            raise RuntimeError("Unknown wrapper runner requested: {0}".
                               format(url))

    # Helper method for returning an appropriate wrapper object, depending on
    # the requested type
    @staticmethod
    def new_wrapper(wrapper_type, runfolder, configuration_svc, logger):
        if wrapper_type == Wrapper.QC_TYPE:
            return QCWrapper(runfolder, configuration_svc, logger)
        elif wrapper_type == Wrapper.REPORT_TYPE:
            return ReportWrapper(runfolder, configuration_svc, logger)
        else:
            raise RuntimeError("Unknown wrapper runner requested: {0}".
                               format(wrapper_type))


class ReportWrapper(Wrapper):
    """ Wrapper around the QuickReport perl script. Inherits behaviour from its
        base class Wrapper.

        Args:
            runfolder: the runfolder to start processing (not full path)
            configuration_svc: the ConfigurationService for our conf lookups
            logger: the Logger object in charge of logging output
    """

    def __init__(self, runfolder, configuration_svc, logger):
        super(ReportWrapper, self).__init__(runfolder,
                                            configuration_svc,
                                            logger)
        self.binary_conf_lookup = "report_bin"
        self.type_txt = Wrapper.REPORT_TYPE


class QCWrapper(Wrapper):
    """ Wrapper around the QualityControl perl script. Inherits behaviour from
        its base class Wrapper.

         Args:
             runfolder: the runfolder to start processing (not full path)
             configuration_svc: ConfigurationService serving our conf lookups
             logger: the Logger object in charge of logging output
     """

    def __init__(self, runfolder, configuration_svc, logger):
        super(QCWrapper, self).__init__(runfolder, configuration_svc, logger)
        self.binary_conf_lookup = "qc_bin"
        self.type_txt = Wrapper.QC_TYPE

        try:
            # Copy QC settings file from central server location (provisioned
            # from elsewhere) to current runfolder destination
            import shutil
            src = self.conf_svc.get_setting("qc_file")
            dst = self.conf_svc.get_setting("runfolder_root") + \
                runfolder + "/sisyphus_qc.xml"
            shutil.copyfile(src, dst)
        except IOError, err:
            self.logger.error("Couldn't copy file {0} to {1}: {2}".
                              format(src, dst, err))


class ProcessService(object):
    """ Keeps a queue over all the processes currently running. Methods for
        starting a new process and checking the status for one process or many.
        Status check of a finished process will remove it from the queue.

        NB. The processes are saved in a dict with the process' Linux PID as
        the key. The maximum number of Linux PIDs for a system can be found in
        /proc/sys/kernel/pid_max. New PIDs usually start at a low number and
        is then increased up to this maximum. When the limit is reached the
        kernel will wrap around and start generating low PIDs again. Some
        security patches can make this behaviour more random though. This
        means that if someone starts running a process but never checks it
        its status after it has finished, or takes a VERY long time before
        doing it, can get the status response from a different process in the
        future, as the entry might have been overwritten by a new process
        with the same PID.

        Args:
            configuration_svc: the ConfigurationService serving conf lookups
            logger: the Logger object in charge of printouts
    """

    proc_queue = {}

    def __init__(self, configuration_svc, logger):
        self.conf_svc = configuration_svc
        self.logger = logger

    @staticmethod
    def _host():
        return socket.gethostname()

    # Execute the wrapper object and add it to the process queue.
    # Return the object to the caller, since it will contain information
    # about the process.
    def run(self, wrapper_object):
        try:
            wrapper_object.run()
            ProcessService.proc_queue[wrapper_object.info.pid] = wrapper_object
            return wrapper_object
        except RuntimeError, err:
            self.info.error("An error ocurred in ProcessService for: {0}".
                            format(err))

    # Poll the status of the process. Removes it from the queue if finished.
    # Accepts a pid and returns the associated ProcessInfo if it exists,
    # otherwise an empty ProcessInfo with state NONE.
    def poll_process(self, pid):

        pid = int(pid)
        wrapper = ProcessService.proc_queue.get(pid)
        debugmsg = ""

        # No such process exists
        if wrapper is None:
            return ProcessInfo.none_process(pid)

        proc = wrapper.info.proc
        returncode = proc.poll()

        if returncode < 0 and returncode is not None:
            wrapper.info.msg = ("Process was terminated with "
                                "Unix code {0}.").format(returncode)
            wrapper.info.state = ProcessInfo.STATE_ERROR
        elif returncode == 0 and returncode is not None:
            # We can't communicate with a dead process; became obvious
            # within Docker testing
            if wrapper.info.state is not ProcessInfo.STATE_DONE:
                out, err = proc.communicate()
                wrapper.info.msg = ("Process was completed successfully with "
                                    "return code ") + str(returncode) + "."

                if out is None:
                    out = "(no txt msg)"

                debugmsg = "Message was: " + out
                wrapper.info.state = ProcessInfo.STATE_DONE
        elif returncode > 0:
            try:
                # We can only communicate with the process if it hasn't been
                # killed off.
                if wrapper.info.state is not ProcessInfo.STATE_ERROR:
                    out, err = proc.communicate()
                    wrapper.info.msg = ("Process was completed successfully, "
                                        "but encounted an error, with return "
                                        "code {0}.").format(returncode)
                    debugmsg = "Message was: " + err
                    wrapper.info.state = ProcessInfo.STATE_ERROR
            except OSError, err:
                self.logger.debug(("An error occurred in "
                                   "ProcessService:poll_process() for {0}/{1} "
                                   "when communicating with the process: {2}").
                                  format(pid, wrapper.type_txt, err))
        else:
            wrapper.info.msg = "Process " + str(pid) + " hasn't finished yet."
            wrapper.info.state = ProcessInfo.STATE_STARTED

        self.logger.debug(("In ProcessService:poll_process() for "
                           "{0}/{1}: {2} {3}").format(pid,
                                                      wrapper.type_txt,
                                                      wrapper.info.msg,
                                                      debugmsg))
        return wrapper.info

    # At the moment we only delete the entry from the queue when we're
    # checking the status per pid.
    def get_status(self, pid, wrapper_type):
        pid = int(pid)

        # If someone is requesting an existing process but of the wrong type
        # we should respond with an empty answer.
        wrapper = ProcessService.proc_queue.get(pid)

        if wrapper and wrapper.type_txt == wrapper_type:
            proc_info = self.poll_process(pid)
        else:
            self.logger.debug(("No process found for PID {0} in "
                              "ProcessService:get_status().").format(pid))
            return ProcessInfo.none_process(pid)

        # Remove the process from the queue if we're checking the status and
        # it has finished. Don't remove a key if we are still working, or if
        # the process doesn't exist
        if proc_info.state not in [ProcessInfo.STATE_STARTED,
                                   ProcessInfo.STATE_NONE]:
            self.logger.debug(("Process {0} has finished/terminated. "
                              "Removing from queue.").format(pid))
            del ProcessService.proc_queue[pid]

        return proc_info

    # Get status of all running processes
    # Should we respond with a status link? Should we return something more
    # than empty list when we have no results?
    def get_all(self, wrapper_type):
        # Only update processes of our requested wrapper class
        map(lambda pid: self.poll_process(pid)
            if ProcessService.proc_queue[pid].type_txt is wrapper_type
            else None, ProcessService.proc_queue.keys())

        results = map(lambda p: {"host": p.info.host,
                                 "runfolder": p.info.runfolder,
                                 "pid": p.info.pid,
                                 "state": p.info.state}
                      if p.type_txt == wrapper_type
                      else None, ProcessService.proc_queue.values())

        self.logger.debug("Fetching all PIDs of type {0} from queue.".
                          format(wrapper_type))

        return filter(None, results)
