import requests

from maykin_common.vcr import SimpleVCRTestCase, VCRTestCase


def get(url: str) -> Exception | requests.Response:
    try:
        return requests.get(url)
    except Exception as e:  # noqa: BLE001
        return e


class VCRTests(VCRTestCase):
    def test_vcr_raises_default(self):
        with self.vcr_raises():
            response = get("https://example.com")

        assert isinstance(response, requests.exceptions.RequestException)

    def test_vcr_raises_exception(self):
        class MyException(Exception):
            pass

        with self.vcr_raises(MyException):
            response = get("https://example.com")

        assert isinstance(response, MyException)

    def test_vcr_raises_specific_instance(self):
        my_exception = Exception("With arguments")

        with self.vcr_raises(lambda: my_exception):
            response = get("https://example.com")

        assert response is my_exception


class VCRHeaderFilteringTests(SimpleVCRTestCase):
    def test_strips_out_authorization_header_by_default(self):
        requests.get(
            "https://example.com",
            headers={
                "Authorization": "supersecret",
                "X-API-Key": "more-secret",
            },
        )

        request = self.cassette.requests[0]

        assert "user-agent" in request.headers
        assert "authorization" not in request.headers
        assert "x-api-key" not in request.headers


class CustomVCRHeaderFilteringTests(SimpleVCRTestCase):
    VCR_FILTER_HEADERS = ("x-api-key",)

    def test_can_specify_which_headers_to_strip(self):
        requests.get(
            "https://example.com",
            headers={
                "Authorization": "supersecret",
                "X-API-Key": "more-secret",
            },
        )

        request = self.cassette.requests[0]

        assert "user-agent" in request.headers
        assert "authorization" in request.headers
        assert "x-api-key" not in request.headers
