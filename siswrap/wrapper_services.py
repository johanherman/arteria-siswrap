import os.path
import socket
import subprocess
import shutil
import datetime
from subprocess import check_output
import logging
from arteria.web.state import State

""" Simple wrapper for the Sisyphus tools suite.
"""


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

    def __init__(self, runfolder=None, host=None, state=State.NONE,
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

    def set_started(self, process):
        """ Update the appropriate meta data for the process when it has been started.
        """
        self.host = ProcessService._host()
        self.state = State.STARTED
        self.proc = process
        self.msg = "Process has been started"
        self.pid = process.pid

    @staticmethod
    def none_process(pid):
        """  Return an empty process information container if a non valid PID
             was requested.
        """
        return ProcessInfo(host=ProcessService._host(), pid=pid,
                           state=State.NONE,
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
        conf = conf_svc.get_app_config()
        self.text = [conf["perl"], conf[bin_lookup], "-runfolder", runfolder,
                     "-mail", conf["receiver"], "-sender", conf["sender"]]


class Wrapper(object):
    """ Our main wrapper for the Sisyphus scripts (QuickReport and
        QualityControl at the moment).

        Args:
            params: Dict of parameters to the wrapper. Must contain the name of
                    the runfolder to use (not full path). Can contain a YAML
                    object containing the Sisyphus config to use, and a XML
                    object cotaining the QC config to use.
            configuration_svc: The ConfigurationService for our config lookups
            logger: Logger object for printouts

        Raises:
            OSError: If the given runfolder doesn't exist.
    """

    QC_TYPE = "qc"
    REPORT_TYPE = "report"

    def __init__(self, params, configuration_svc, logger=None):
        self.conf_svc = configuration_svc
        self.logger = logger or logging.getLogger(__name__)

        conf = configuration_svc.get_app_config()
        runpath = conf["runfolder_root"] + "/" + params["runfolder"]

        if not os.path.isdir(runpath):
            raise OSError("No runfolder {0} exists.".format(runpath))

        self.info = ProcessInfo(runpath)

        if "sisyphus_config" in params:
            path = runpath + "/sisyphus.yml"
            self.write_new_config_file(path, params["sisyphus_config"])


    def __get_attr__(self, attr):
        return getattr(self.info, attr)

    @staticmethod
    def write_new_config_file(path, content):
        """ Writes new config file (especially used for Sisyphus YAML and QC XML).
            If the file already exists a backup copy will be created.

            Args:
                - path: The path to the config file that should be written.
                - content: The content of the new config file.
        """
        try:
            logger = logging.getLogger(__name__)

            logger.debug("Writing new config file " + path)

            now = datetime.datetime.now().isoformat()

            if os.path.isfile(path):
                logger.debug("Config file already existed. Making backup copy.")
                shutil.move(path, path + "." + now)

            with open(path, "w") as f:
                f.write(content)

        except OSError, err:
            logger.error("Error writing new config file {0}: {1}".
                              format(path, err))


    def sisyphus_version(self):
        """
        Use Sisyphus own script to check which version is used.
        :return: the sisyphus version used.
        """
        conf = self.conf_svc.get_app_config()
        cmd = [conf["perl"], conf["version_bin"]]
        sisphus_version = check_output(cmd)
        return sisphus_version

    # TODO: Perhaps implement support for stopping running process.
    def stop(self):
        pass

    def run(self):
        """  Creates an execution string that will be unique depending on
             what kind of object did the call to the method. Spawns a subprocess
             with this execution string.

             Raises:
                OSError, ValueError: if an error occured with the subprocess
        """
        try:
            if os.getenv("ARTERIA_TEST"):
                proc = subprocess.Popen(["/bin/sleep", "1m"])
                exec_string = "/bin/sleep 1m"
            else:
                exec_string = ExecString(self, self.conf_svc,
                                         self.info.runfolder).text
                proc = subprocess.Popen(exec_string, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

            self.info.set_started(proc)
            self.logger.info("{0} started for {1} with: {2}".
                             format(type(self), self.info.runfolder, exec_string))
        except (OSError, ValueError), err:
            self.logger.error("An error occurred in Wrapper for {0}: {1}".
                              format(self.info.runfolder, err))

    @staticmethod
    def url_to_type(url):
        """ Helper method to see which wrapper object might belong to which URL.
        """
        # TODO: Take out the correct part of the URL instead.
        if Wrapper.QC_TYPE in url:
            return Wrapper.QC_TYPE
        elif Wrapper.REPORT_TYPE in url:
            return Wrapper.REPORT_TYPE
        else:
            raise RuntimeError("Unknown wrapper runner requested: {0}".
                               format(url))

    @staticmethod
    def new_wrapper(wrapper_type, runfolder, configuration_svc):
        """ Helper method for returning an appropriate wrapper object, depending on
            the requested type.
        """
        if wrapper_type == Wrapper.QC_TYPE:
            return QCWrapper(runfolder, configuration_svc)
        elif wrapper_type == Wrapper.REPORT_TYPE:
            return ReportWrapper(runfolder, configuration_svc)
        else:
            raise RuntimeError("Unknown wrapper runner requested: {0}".
                               format(wrapper_type))


class ReportWrapper(Wrapper):
    """ Wrapper around the QuickReport perl script. Inherits behaviour from its
        base class Wrapper.

        Args:
            params: Dict of parameters to the wrapper. Must contain the name of
                    the runfolder to use (not full path). Can contain a YAML
                    object containing the Sisyphus config to use.
            configuration_svc: the ConfigurationService for our conf lookups
            logger: the Logger object in charge of logging output
    """

    def __init__(self, params, configuration_svc, logger=None):
        super(ReportWrapper, self).__init__(params, configuration_svc, logger)
        self.binary_conf_lookup = "report_bin"
        self.type_txt = Wrapper.REPORT_TYPE

class QCWrapper(Wrapper):
    """ Wrapper around the QualityControl perl script. Inherits behaviour from
        its base class Wrapper.

         Args:
            params: Dict of parameters to the wrapper. Must contain the name of
                    the runfolder to use (not full path). Can contain a YAML
                    object containing the Sisyphus config to use, and a XML
                    object containing the QC config to use. If a config is given
                    then they will be written to the runfolder where Sisyphus
                    will be able to use them.
             configuration_svc: ConfigurationService serving our conf lookups
             logger: the Logger object in charge of logging output

        Raises:
            IOError: if we couldn't copy the QC settings input file
     """

    def __init__(self, params, configuration_svc, logger=None):
        super(QCWrapper, self).__init__(params, configuration_svc, logger)
        self.binary_conf_lookup = "qc_bin"
        self.type_txt = Wrapper.QC_TYPE
        conf = self.conf_svc.get_app_config()

        if "qc_config" in params:
            path = conf["runfolder_root"] + "/" + params["runfolder"] + "/sisyphus_qc.xml"
            self.write_new_config_file(path, params["qc_config"])


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

    def __init__(self, configuration_svc, logger=None):
        self.conf_svc = configuration_svc
        self.logger = logger or logging.getLogger(__name__)

    @staticmethod
    def _host():
        return socket.gethostname()

    def run(self, wrapper_object):
        """  Execute the wrapper object and add it to the process queue.

            Args:
                wrapper_object: the object to put in the process queue and run

            Returns:
                the wrapper_object, filled with some extra meta information

            Raises:
                RuntimeError: something unexpected happened when running the process
        """
        try:
            wrapper_object.run()
            ProcessService.proc_queue[wrapper_object.info.pid] = wrapper_object
            return wrapper_object
        except RuntimeError, err:
            self.logger.error("An error ocurred in ProcessService for: {0}".
                              format(err))

    def poll_process(self, pid):
        """ Poll the status of the process. Removes it from the queue if finished.
            Accepts a pid and returns the associated ProcessInfo if it exists,
            otherwise an empty ProcessInfo with state NONE.

            Args:
                pid: the pid of the process to poll

            Returns:
                the associated ProcessInfo if it exists, otherwise an empty ProcessInfo
        """

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
            wrapper.info.state = State.ERROR
        elif returncode == 0 and returncode is not None:
            # We can't communicate with a dead process; became obvious
            # within Docker testing
            if wrapper.info.state is not State.DONE:
                out, err = proc.communicate()
                wrapper.info.msg = ("Process was completed successfully with "
                                    "return code ") + str(returncode) + "."

                if out is None:
                    out = "(no txt msg)"

                debugmsg = "Message was: " + out
                wrapper.info.state = State.DONE
        elif returncode > 0:
            try:
                # We can only communicate with the process if it hasn't been
                # killed off.
                if wrapper.info.state is not State.ERROR:
                    out, err = proc.communicate()
                    wrapper.info.msg = ("Process was completed successfully, "
                                        "but encounted an error, with return "
                                        "code {0}.").format(returncode)
                    debugmsg = "Message was: " + err
                    wrapper.info.state = State.ERROR
            except OSError, err:
                self.logger.error(("An error occurred in "
                                   "ProcessService:poll_process() for {0}/{1} "
                                   "when communicating with the process: {2}").
                                  format(pid, wrapper.type_txt, err))
        else:
            wrapper.info.msg = "Process " + str(pid) + " hasn't finished yet."
            wrapper.info.state = State.STARTED

        self.logger.info(("In ProcessService:poll_process() for "
                           "{0}/{1}: {2} {3}").format(pid,
                                                      wrapper.type_txt,
                                                      wrapper.info.msg,
                                                      debugmsg))
        return wrapper.info

    def get_status(self, pid, wrapper_type):
        """ Get status of a specific process. Removes the pid from the queue
            if the proecess has finished executing.

            Args:
                pid: the pid of the process to check for
                wrapper_type: the type of the process we want to check

            Returns:
                a ProcessInfo filled with status information if it is still
                running, otherwise an empty ProcessInfo
        """
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
        if proc_info.state not in [State.STARTED,
                                   State.NONE]:
            self.logger.debug(("Process {0} has finished/terminated. "
                              "Removing from queue.").format(pid))
            del ProcessService.proc_queue[pid]

        return proc_info

    # Should we respond with a status link? Should we return something more
    # than empty list when we have no results?
    def get_all(self, wrapper_type):
        """ Get status of all running processes

            Args:
                wrapper_type: the object type to check statuses for

            Returns:
                a dict of processes and some meta information if they are running, otherwise
                an empty dict
        """
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
