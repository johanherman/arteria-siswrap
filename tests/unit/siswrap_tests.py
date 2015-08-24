import pytest
from siswrap.siswrap import *
from siswrap.siswrap_ws import *
from siswrap.configuration import *

# Some tests for siswrap/siswrap.py.


class TestProcessInfo(object):

    STATE_NONE = "none"
    STATE_STARTED = "started"
    NR_ELEMENTS = 7  # runfolder, host, state, proc, msg, pid, link

    # A newly created object should be STATE_NONE, and
    # have the right number of properties
    def test_creation(self):
        proc_info = ProcessInfo()
        assert proc_info.state == self.STATE_NONE
        assert len(vars(proc_info)) == self.NR_ELEMENTS

    # A ProcessInfo without an existing process should
    # still contain some valid data
    def test_none_process(self):
        pid = 4242
        proc_info = ProcessInfo.none_process(pid)
        assert proc_info.pid == pid
        assert proc_info.state == self.STATE_NONE
        assert len(proc_info.msg) > 0

    # A ProcessInfo set as started should have a proper
    # state and its process property with a valid pid.
    def test_started(self):
        class BarObject(object):
            pid = None

            def __init__(self, arg):
                self.pid = arg

        pid = 4242
        proc_info = ProcessInfo()
        test_object = BarObject(pid)
        proc_info.set_started(test_object)

        assert proc_info.state == self.STATE_STARTED
        assert isinstance(proc_info.proc, BarObject)
        assert proc_info.proc.pid == pid
        assert len(proc_info.msg) > 0


# Mini helper class for some of the tests
class Helper(object):
    runfolder = "foo"
    conf = ConfigurationService("../../config/siswrap.config")
    root = conf.get_setting("runfolder_root")
    logger = Logger(True)
#    report = ReportWrapper(runfolder, conf, logger)
    proc_svc = ProcessService(conf, logger)


class TestReportWrapper(object):

    report = ReportWrapper(Helper.runfolder, Helper.conf, Helper.logger)

    # The ReportWrapper class should be setup properly
    def test_creation(self):
        assert isinstance(self.report.conf_svc, ConfigurationService) is True
        assert isinstance(self.report.logger, Logger) is True

    # We should be able to access the ProcessInfo's attributes
    def test_info_attr(self):
        assert isinstance(self.report.info, ProcessInfo) is True
        assert self.report.info.runfolder == Helper.root + Helper.runfolder

    # And we should inherit from the base Wrapper class
    def test_inheritance(self):
        assert issubclass(ReportWrapper, Wrapper) is True


class TestWrapper(object):

    # Wrapper base class should be setup properly
    def test_creation(self, monkeypatch):

        def mocked_isdir(runpath):
            return True

        monkeypatch.setattr("os.path.isdir", mocked_isdir)
        wrapper = Wrapper(Helper.runfolder, Helper.conf, Helper.logger)

        assert isinstance(wrapper.info, ProcessInfo) is True
        assert isinstance(wrapper.conf_svc, ConfigurationService) is True
        assert isinstance(wrapper.logger, Logger) is True

        assert wrapper.QC_TYPE == "qc"
        assert wrapper.REPORT_TYPE == "report"

    # Run method should setup a ExecString for the calling object in question
    # and spawn a subprocess with it, as well as update the process info's
    # attributes.
    def test_run(self, monkeypatch):
        pass_mocked = True

        class MockedExecString(object):
            def __init__(self, wrapper, conf, runfolder):
                if pass_mocked:
                    self.text = ["/bin/bash", "-c", "echo uggla"]
                else:
                    self.text = ["/bin/uggla"]

        monkeypatch.setattr("siswrap.siswrap.ExecString", MockedExecString)
        w = Wrapper(Helper.runfolder, Helper.conf, Helper.logger)
        w.run()

        assert isinstance(w.info.proc, subprocess.Popen)
        assert w.info.state == "started"
        out, err = w.info.proc.communicate()
        assert out == "uggla\n"

        pass_mocked = False
        w.run()
        with pytest.raises(Exception) as err:
            out, err = w.info.proc.communicate()

    # Helper method should return the correct wrapper object for
    # different text inputs
    def test_new_wrapper(self):
        qc_wrap = Wrapper.new_wrapper("qc", Helper.runfolder,
                                      Helper.conf, Helper.logger)
        report_wrap = Wrapper.new_wrapper("report", Helper.runfolder,
                                          Helper.conf, Helper.logger)

        assert qc_wrap.type_txt == "qc"
        assert report_wrap.type_txt == "report"

        with pytest.raises(Exception) as err:
            Wrapper.new_wrapper("foo", Helper.runfolder,
                                Helper.conf, Helper.logger)

    # Helper method should return the correct wrapper type in text
    # format for different URLs
    def test_url_to_type(self):
        test_urls = ["http://arteria1:1111/v1/api/qc/run/8312",
                     "https://arteria12:3232/v2/api/report/run/3232",
                     "http://testweb/api/1/qc/status",
                     "http://testtest/api/v1/report/run"]
        test_types = ["qc", "report", "qc", "report"]

        for idx, url in enumerate(test_urls):
            assert Wrapper.url_to_type(url) == test_types[idx]

        with pytest.raises(Exception) as err:
            Wrapper.url_to_type("foo")


class TestQCWrapper(object):
    qc = QCWrapper(Helper.runfolder, Helper.conf, Helper.logger)

    # QCWrapper should be setup correctly
    def test_creation(self, monkeypatch):
        assert isinstance(self.qc.info, ProcessInfo) is True
        assert isinstance(self.qc.logger, Logger) is True
        assert isinstance(self.qc.conf_svc, ConfigurationService) is True

        # test the file copy
        dstdir = "/tmp/test_siswrap/runfolder_root/"
        testsrc = dstdir + "qc_file.txt"

        def mocked_get_setting(self, setting):
            if setting == "qc_file":
                return testsrc
            elif setting == "runfolder_root":
                return dstdir
            else:
                return setting

        # Create the src file
        import io
        if not os.path.isdir(dstdir + Helper.runfolder):
            os.makedirs(dstdir + Helper.runfolder)
        if not os.path.exists(testsrc):
            io.open(testsrc, 'a').close()

        monkeypatch.setattr("siswrap.siswrap.ConfigurationService.get_setting",
                            mocked_get_setting)
        qc = QCWrapper(Helper.runfolder, Helper.conf, Helper.logger)
        assert os.path.exists(dstdir + Helper.runfolder +
                              "/sisyphus_qc.xml") is True

        # remove the files
        import shutil
        shutil.rmtree(dstdir)

    # QCWrapper should be able to get the attributes from ProcessInfo
    def test_info_attr(self):
        assert isinstance(self.qc.info, ProcessInfo) is True
        assert self.qc.info.runfolder == Helper.root + Helper.runfolder

    # QCWrapper should inherit Wrapper
    def test_inheritance(self):
        assert issubclass(QCWrapper, Wrapper) is True


class TestExecString(object):

    # ExecString should be created with a text field containing the string
    # to be spawned in a subprocess later. String will be somewhat different
    # on which wrapper is calling. Settings read from the conf service.
    def test_creation(self, monkeypatch):
        class FooBar(object):
            def __init__(self):
                self.binary_conf_lookup = "foobar"

        def mocked_get_setting(self, setting):
            return setting

        monkeypatch.setattr("siswrap.siswrap.ConfigurationService.get_setting",
                            mocked_get_setting)

        foobar = FooBar()
        retobj = ExecString(foobar, Helper.conf, Helper.runfolder)
        assert foobar.binary_conf_lookup in retobj.text

        # 8 elements in execstring: perl, binary, runfolder, runfolderpath,
        # mail, toadderss, sender, fromaddress
        assert len(retobj.text) == 8  # nr of elements in execstring
        assert Helper.runfolder in retobj.text


class TestProcessService(object):

    my_queue = {}

    # The ProcessService should be setup up properly with logging and
    # a config
    def test_creation(self):
        ps = ProcessService(Helper.proc_svc.conf_svc, Helper.logger)
        assert isinstance(ps.conf_svc, ConfigurationService) is True
        assert isinstance(ps.logger, Logger) is True
        assert type(ps.proc_queue) is dict

    # ProcessService should be able to run a specified wrapper object,
    # which should then end up in the process queue for later status polling
    def test_run(self):
        ps = ProcessService(Helper.proc_svc.conf_svc, Helper.logger)

        class MyInfo(object):
            pid = 4242

        class MyWrapper(object):
            info = MyInfo()

            def run(self):
                return "foo"

        my_obj = MyWrapper()
        res = ps.run(my_obj)
        assert res == my_obj
        assert res.info.pid == 4242
        assert ps.proc_queue[res.info.pid] == res

    def setup_queue(self):
        class MyInfo(object):
            def __init__(self, pid):
                self.pid = pid
                self.runfolder = pid
                self.host = pid
                self.state = ProcessInfo.STATE_STARTED
                self.proc = subprocess.Popen("/bin/bash")
                print "self", self.pid

        class MyWrapper(object):
            def __init__(self, pid, wrapper_type=None):
                self.info = MyInfo(pid)
                self.type_txt = wrapper_type

            def run(self):
                return "foo"

        queue = {4242: MyWrapper(4242, "qc"), 3131:
                 MyWrapper(3131, "report"), 5353: MyWrapper(5353)}
        return queue

    def my_poll(self, pid):
        # print "polling pid", pid
        # wrapper_type = self.my_queue.get(pid).type_txt
        # print "returning wrapper type", wrapper_type,
        # "with state",self.my_queue.get(pid).info.state
        return self.my_queue.get(pid).info

    # Test that we can poll a specific process in the process queue correctly
    def test_polling(self, monkeypatch):
        ps = ProcessService(Helper.proc_svc.conf_svc, Helper.logger)
        poll_return = 0
        # populate queue
        self.my_queue = self.setup_queue()
        monkeypatch.setattr("siswrap.siswrap.ProcessService.proc_queue",
                            self.my_queue)

        # mock syscall
        def my_communicate(self):
            return ("", "")

        def my_poll(self):
            return poll_return
        monkeypatch.setattr("subprocess.Popen.communicate", my_communicate)
        monkeypatch.setattr("subprocess.Popen.poll", my_poll)
        # self.my_queue[4242].info.proc = MyProc

        # check that we get none process info if we request invalid pid
        res = ps.poll_process(7575)
        assert res.pid == 7575
        assert res.state == ProcessInfo.STATE_NONE

        # check that we get a state_error if the return value from poll
        # is negative
        poll_return = -1
        res = ps.poll_process(4242)
        assert res.pid == 4242
        assert res.state == ProcessInfo.STATE_ERROR

        # check that we get a state_done if the return value is 0.
        poll_return = 0
        res = ps.poll_process(3131)
        assert res.pid == 3131
        assert res.state == ProcessInfo.STATE_DONE

        # check that we get a state_error when retcode > 0
        poll_return = 1
        res = ps.poll_process(5353)
        assert res.pid == 5353
        assert res.state == ProcessInfo.STATE_ERROR

        # check that we get state_started when we don't have a return code
        poll_return = None
        res = ps.poll_process(4242)
        assert res.pid == 4242
        assert res.state == ProcessInfo.STATE_STARTED

    # Test that we can check the status of a specific process in the
    # process queue
    def test_status(self, monkeypatch):
        ps = ProcessService(Helper.proc_svc.conf_svc, Helper.logger)

        # Insert a wrapper manually in the queue
        self.my_queue = self.setup_queue()
        monkeypatch.setattr("siswrap.siswrap.ProcessService.proc_queue",
                            self.my_queue)

        # Check that the type_txt describes the same wrapper_type as we request
        # in the call to get_status; if so, poll the wrappers pid; else
        # return an empty ProcessInfo
        monkeypatch.setattr("siswrap.siswrap.ProcessService.poll_process",
                            self.my_poll)

        res = ps.get_status(4242, "qc")
        assert res.pid == 4242
        assert res.state == ProcessInfo.STATE_STARTED
        assert self.my_queue[4242].info.pid == 4242

        res = ps.get_status(3131, "report")
        assert res.pid == 3131
        assert res.state == ProcessInfo.STATE_STARTED
        assert self.my_queue[3131].info.pid == 3131

        # Check that the wrapper is removed from the queue if it has
        # some other status than none and started.

        self.my_queue[4242].info.state = ProcessInfo.STATE_ERROR
        res = ps.get_status(4242, "qc")
        assert res.pid == 4242
        assert res.state == ProcessInfo.STATE_ERROR
        with pytest.raises(Exception) as err:
            self.my_queue[4242]

        # Check that if we request a pid with wrong type we get none
        # as response
        res = ps.get_status(3131, "qc")
        assert res.pid == 3131
        assert res.state == ProcessInfo.STATE_NONE

    # Test that we can fetch the status of all the current processes
    # in the queue
    def test_status_all(self, monkeypatch):
        self.my_queue = self.setup_queue()
        # populate the queue with some wrappers of different kinds
        monkeypatch.setattr("siswrap.siswrap.ProcessService.proc_queue",
                            self.my_queue)

        # mock poll_process
        monkeypatch.setattr("siswrap.siswrap.ProcessService.poll_process",
                            self.my_poll)

        # self.my_queue[4242].type_txt = "qc"
        # self.my_queue[3131].type_txt = "report"
        # print "my_queue", my_queue
        # print "types", my_queue[3131].type_txt, my_queue[4242].type_txt,
        # my_queue[5353].type_txt
        ps = ProcessService(Helper.conf, Helper.logger)

        # verify that we get back a list of dicts with correct keys
        # and values (which comes from the wrappers process info attribute.
        res = ps.get_all("qc")
        assert res[0]["host"] == 4242
        assert res[0]["runfolder"] == 4242
        assert res[0]["pid"] == 4242
        assert res[0]["state"] == ProcessInfo.STATE_STARTED

        res = ps.get_all("report")
        assert res[0]["host"] == 3131
        assert res[0]["runfolder"] == 3131
        assert res[0]["pid"] == 3131
        assert res[0]["state"] == ProcessInfo.STATE_STARTED

        res = ps.get_all("foo")
        assert len(res) == 0

if __name__ == '__main__':
    pytest.main()
