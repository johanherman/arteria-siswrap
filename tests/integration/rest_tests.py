import pytest
import requests
import time
import jsonpickle
from siswrap.configuration import ConfigurationService
from siswrap.siswrap import ProcessService
# from siswrap.siswrap_ws import SisApp


# Recommended to have the environment variable ARTERIA_TEST set to 1
# for the siswrap-wsd to test with a 1 min long running process


class TestRestApi(object):
    BASE_URL = "http://localhost:10900/api/1.0"
    REPORT_URL = BASE_URL + "/report"
    QC_URL = BASE_URL + "/qc"

    RUNFOLDER = "runfolder_inttest_1437474276963"

    CONF = "/opt/siswrap/etc/siswrap.config"
    conf = ConfigurationService(CONF)

    STATE_NONE = "none"
    STATE_READY = "ready"
    STATE_STARTED = "started"
    STATE_DONE = "done"
    STATE_ERROR = "error"

    my_queue = {}

    def is_number(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

        try:
            import unicodedata
            unicodedata.numeric(s)
            return True
        except (TypeError, ValueError):
            return False

    def start_runfolder(self, handler, runfolder):
        payload = {"runfolder": runfolder}

        if handler == "qc":
            url = self.QC_URL + "/run/" + runfolder
        elif handler == "report":
            url = self.REPORT_URL + "/run/" + runfolder

        resp = requests.post(url, json=payload)

        return resp

    def get_url(self, handler):
        if handler == "qc":
            return self.QC_URL
        elif handler == "report":
            return self.REPORT_URL

    def start_handler(self, handler, monkeypatch):
        runfolder = self.RUNFOLDER

        # Clear the process queue
        self.my_queue = {}
        monkeypatch.setattr("siswrap.siswrap.ProcessService.proc_queue",
                            self.my_queue)

        resp = self.start_runfolder(handler, runfolder)
        assert resp.status_code == 202

        payload = jsonpickle.decode(resp.text)

        assert payload.get("runfolder") == \
            self.conf.get_setting("runfolder_root") + runfolder
        assert self.is_number(payload.get("pid")) is True
        pid = payload.get("pid")
        assert payload.get("state") == "started"
        assert payload.get("link") == \
            self.get_url(handler) + "/status/" + str(pid)

        link = payload.get("link")

        # We should get 200 or 500 on status check if job has started
        resp = requests.get(link)
        assert resp.status_code == 200 or resp.status_code == 500

    def check_all_statuses(self, handler, sleep_time, monkeypatch):
        runfolders = [self.RUNFOLDER, self.RUNFOLDER]
        mypids = []

        # Clear the queue just in case
        self.my_queue = {}
        monkeypatch.setattr("siswrap.siswrap.ProcessService.proc_queue",
                            self.my_queue)

        # Request two new runs
        for runfolder in runfolders:
            resp = self.start_runfolder(handler, runfolder)
            assert resp.status_code == 202
            payload = jsonpickle.decode(resp.text)
            mypids.append(payload["pid"])

        # See so we get back statuses for both and the jobs have started
        resp = requests.get(self.get_url(handler) + "/status/")
        assert resp.status_code == 200
        outerpayload = jsonpickle.decode(resp.text)
        print "first outerpayload", outerpayload

        counter = 0
        for idx, run in enumerate(outerpayload):
            # assert run["pid"] in mypids

            if run["pid"] in mypids:
                assert run.get("runfolder").split("/")[-1] in runfolders
                assert run.get("state") in ["started", "error"]
                counter = counter + 1

        assert counter == len(runfolders)

        # Sleep before we check again
        if sleep_time <= 60:
            time.sleep(sleep_time)

            outerpayload = jsonpickle.decode(resp.text)

            for idx, run in enumerate(outerpayload):
                if run["pid"] in mypids and run["state"] == "started":
                    # Sleep before we check again
                    # time.sleep(60)

                    resp = requests.get(self.get_url(handler) + "/status/")
                    assert resp.status_code == 200
                    innerpayload = jsonpickle.decode(resp.text)
                    innerpayloadpids = []

                    for innerrun in innerpayload:
                        # assert innerrun.get("pid") in mypids
                        innerpayloadpids.append(innerrun.get("pid"))
                        assert innerrun.get("state") in ["done", "error"]

                    # FIXME: Need to refactor this test into more managable parts
                    # for pid in mypids:
                    #    assert pid in innerpayloadpids

                    # Request detailed status
                    resp = requests.get(self.get_url(handler) + "/status/" +
                                        str(run["pid"]))
                    assert resp.status_code == 200
                    innerpayload = jsonpickle.decode(resp.text)
                    assert innerpayload.get("state") == "done"

                    # And if we check the detailed status yet again then the
                    # process shouldn't still exist.
                    resp = requests.get(self.get_url(handler) + "/status/" +
                                        str(run["pid"]))
                    assert resp.status_code == 500
                    innerpayload = jsonpickle.decode(resp.text)
                    assert innerpayload.get("state") == "none"
                    assert self.is_number(innerpayload.get("pid")) is True
                elif run["state"] == "error":
                    resp = requests.get(self.get_url(handler) + "/status/" +
                                        str(run["pid"]))
                    assert resp.status_code == 200
                    innerpayload = jsonpickle.decode(resp.text)
                    assert innerpayload.get("state") == "error"

            # Now our pids shouldn't exist in the global status
            resp = requests.get(self.get_url(handler) + "/status/")
            outerpayload = jsonpickle.decode(resp.text)
            for run in outerpayload:
                assert run.get("pid") not in mypids

    def check_a_status(self, handler, sleep_time, monkeypatch):
        runfolder = self.RUNFOLDER

        # Clear the process queue
        self.my_queue = {}
        monkeypatch.setattr("siswrap.siswrap.ProcessService.proc_queue",
                            self.my_queue)

        # We should receive a HTTP status code 202 after submission
        resp = self.start_runfolder(handler, runfolder)
        assert resp.status_code == 202

        payload = jsonpickle.decode(resp.text)
        pid = str(payload.get("pid"))

        # The status handler should return a HTTP status 200 if the process
        # is found
        resp = requests.get(self.get_url(handler) + "/status/" + pid)
        assert resp.status_code == 200
        payload = jsonpickle.decode(resp.text)
        assert payload.get("state") == "started"
        assert payload.get("runfolder") == \
            self.conf.get_setting("runfolder_root") + runfolder
        assert self.is_number(payload.get("pid")) is True

        # We want to make sure that the process has finished, or still ongoing
        if sleep_time <= 60:
            time.sleep(sleep_time)

            # And now we check it again and should get a done response
            resp = requests.get(self.get_url(handler) + "/status/" + pid)
            assert resp.status_code == 200
            payload = jsonpickle.decode(resp.text)
            assert payload.get("state") == "done"

            # Now when we have checked it again the process should be gone
            resp = requests.get(self.get_url(handler) + "/status/" + pid)
            assert resp.status_code == 500
            payload = jsonpickle.decode(resp.text)
            assert payload.get("state") == "none"
        else:
            resp = requests.get(self.get_url(handler) + "/status/" + pid)
            assert resp.status_code == 200
            payload = jsonpickle.decode(resp.text)
            assert payload.get("state") == "started"

    def test_basic_smoke_test(self):
        resp = requests.get(self.BASE_URL)
        assert resp.status_code == 200

    def test_can_start_a_report(self, monkeypatch):
        self.start_handler("report", monkeypatch)

    def test_can_start_a_qc(self, monkeypatch):
        self.start_handler("qc", monkeypatch)

    def test_can_check_a_report_status(self, monkeypatch):
        self.check_a_status("report", 15*60, monkeypatch)

    def test_can_check_a_qc_status(self, monkeypatch):
        self.check_a_status("qc", 10, monkeypatch)

    def test_can_check_all_report_statuses(self, monkeypatch):
        self.check_all_statuses("report", 15*60, monkeypatch)

    def test_can_check_all_qc_statuses(self, monkeypatch):
        self.check_all_statuses("qc", 10, monkeypatch)

if __name__ == '__main__':
    pytest.main()
