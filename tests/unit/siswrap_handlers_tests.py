import pytest
import tornado.web
import jsonpickle
from arteria import *
from arteria.configuration import ConfigurationService
from siswrap.app import *
from siswrap.handlers import *
from siswrap.wrapper_services import *


# Some unit tests for siswrap.handlers

API_URL = "/api/1.0"


@pytest.fixture
def app():
    config_svc = ConfigurationService(app_config_path="./config/app.config")
    process_svc = ProcessService(config_svc)
    args = dict(process_svc=process_svc, config_svc=config_svc)
    app = tornado.web.Application([
            (r"/api/1.0/(?:qc|report)/run/([\w_-]+)", RunHandler, args),
            (r"/api/1.0/(?:qc|report)/status/(\d*)", StatusHandler, args)
        ], debug=True)
    return app

@pytest.fixture
def stub_isdir(monkeypatch):
    def my_isdir(path):
        return True

    monkeypatch.setattr("os.path.isdir", my_isdir)

def json(payload):
    return jsonpickle.encode(payload)


class TestRunHandler(object):

    @pytest.mark.gen_test
    def test_post_job(self, http_client, http_server, base_url, stub_isdir):
        payload = {"runfolder": "foo"}
        resp = yield http_client.fetch(base_url + API_URL + "/report/run/123",
                                       method="POST", body=json(payload))

        assert resp.code == 202
        payload = jsonpickle.decode(resp.body)
        assert payload["runfolder"] == "/data/testarteria1/mon1/foo"


class TestStatusHandler(object):

    @pytest.mark.gen_test
    def test_get_global_status(self, http_client, http_server,
                               base_url, monkeypatch, stub_isdir):
        def my_get_all(self, wrapper_type):
            return []

        monkeypatch.setattr("siswrap.wrapper_services.ProcessService.get_all",
                            my_get_all)

        resp = yield http_client.fetch(base_url + API_URL + "/report/status/")
        assert resp.code == 200
        assert len(resp.body) == 2  # [ and ]

        resp = yield http_client.fetch(base_url + API_URL + "/qc/status/")
        assert resp.code == 200
        assert len(resp.body) == 2

    @pytest.mark.gen_test
    def test_get_global_filled_status(self, http_client, http_server,
                                      base_url, monkeypatch, stub_isdir):
        def my_get_all(self, wrapper_type):
            if wrapper_type == "report":
                return [{"pid": 4242}, {"pid": 3131}]
            elif wrapper_type == "qc":
                return [{"pid": 2424}, {"pid": 1313}]

        monkeypatch.setattr("siswrap.wrapper_services.ProcessService.get_all",
                            my_get_all)

        resp = yield http_client.fetch(base_url + API_URL + "/report/status/")
        assert resp.code == 200
        payload = jsonpickle.decode(resp.body)
        assert payload[0]["pid"] == 4242
        assert payload[1]["pid"] == 3131

    @pytest.mark.gen_test
    def test_get_existing_status(self, http_client, http_server,
                                 base_url, monkeypatch, stub_isdir):
        def my_get(self, pid, wrapper_type):
            return ProcessInfo(runfolder="foo", host="bar",
                               state=State.STARTED,
                               proc=None, msg=None, pid=pid)

        monkeypatch.setattr("siswrap.wrapper_services.ProcessService.get_status",
                            my_get)

        resp = yield http_client.fetch(base_url + API_URL +
                                       "/report/status/123")
        assert resp.code == 200
        payload = jsonpickle.decode(resp.body)
        assert payload["pid"] == 123
        assert payload["state"] == State.STARTED

        resp = yield http_client.fetch(base_url + API_URL + "/qc/status/321")
        assert resp.code == 200
        payload = jsonpickle.decode(resp.body)
        assert payload["pid"] == 321

    @pytest.mark.gen_test
    def test_get_invalid_status(self, http_client, http_server,
                                base_url, monkeypatch, stub_isdir):
        def my_get(self, pid, wrapper_type):
            return ProcessInfo(runfolder=None, host="foobar",
                               state=State.NONE,
                               proc=None, msg=None, pid=pid)

        monkeypatch.setattr("siswrap.wrapper_services.ProcessService.get_status",
                            my_get)

        with pytest.raises(Exception) as err:
            resp = yield http_client.fetch(base_url + API_URL +
                                           "/report/status/123")
            assert resp.code == 500

if __name__ == '__main__':
    pytest.main()
