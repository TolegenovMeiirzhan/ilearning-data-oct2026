

import http.client
import threading
import unittest
from urllib.parse import urlencode

from app import create_server, email_path


class EndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.email = "Student.Name+demo@example.com"
        cls.route = "/Student_Name_demo_example_com"
        cls.server = create_server(cls.email, port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, path, method="GET"):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=5
        )
        try:
            connection.request(method, path)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def check_query(self, query, expected):
        status, headers, body = self.request(self.route + "?" + query)
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "text/plain; charset=utf-8")
        self.assertEqual(int(headers["Content-Length"]), len(body))
        self.assertEqual(body, expected.encode("ascii"))

    def test_normal_integers(self):
        self.check_query("x=12&y=18", "36")

    def test_coprime(self):
        self.check_query("x=17&y=19", "323")

    def test_equal(self):
        self.check_query("x=123456&y=123456", "123456")

    def test_x_zero(self):
        self.check_query("x=0&y=12", "0")

    def test_y_zero(self):
        self.check_query("x=12&y=0", "0")

    def test_both_zero(self):
        self.check_query("x=0&y=0", "0")

    def test_one(self):
        self.check_query("x=1&y=487", "487")

    def test_leading_zeros(self):
        self.check_query("x=00012&y=0018", "36")

    def test_query_order(self):
        self.check_query("y=18&x=12", "36")

    def test_extra_parameter(self):
        self.check_query("x=12&y=18&tracking=test", "36")

    def test_beyond_javascript_safe_integer(self):
        self.check_query("x=9007199254740993&y=2", "18014398509481986")

    def test_more_than_4300_digits(self):
        self.check_query("x=" + "1" + "0" * 4500 + "&y=2", "1" + "0" * 4500)

    def test_missing_x(self):
        self.check_query("y=18", "NaN")

    def test_missing_y(self):
        self.check_query("x=12", "NaN")

    def test_no_parameters(self):
        self.check_query("", "NaN")

    def test_empty(self):
        self.check_query("x=&y=18", "NaN")

    def test_negative(self):
        self.check_query("x=-12&y=18", "NaN")

    def test_fraction(self):
        self.check_query("x=1.5&y=18", "NaN")

    def test_decimal_point(self):
        self.check_query("x=12.0&y=18", "NaN")

    def test_letters(self):
        self.check_query("x=abc&y=18", "NaN")

    def test_infinity(self):
        self.check_query("x=Infinity&y=18", "NaN")

    def test_exponent(self):
        self.check_query("x=1e3&y=18", "NaN")

    def test_hexadecimal(self):
        self.check_query("x=0x10&y=18", "NaN")

    def test_space(self):
        self.check_query("x=%2012&y=18", "NaN")

    def test_plus(self):
        self.check_query("x=%2B12&y=18", "NaN")

    def test_unicode_digits(self):
        self.check_query(urlencode({"x": "١٢", "y": "18"}), "NaN")

    def test_duplicate_x(self):
        self.check_query("x=12&x=24&y=18", "NaN")

    def test_duplicate_y(self):
        self.check_query("x=12&y=18&y=36", "NaN")

    def test_invalid_y(self):
        self.check_query("x=12&y=wrong", "NaN")

    def test_invalid_value_with_zero(self):
        self.check_query("x=0&y=wrong", "NaN")

    def test_percent_encoded_digits(self):
        self.check_query("x=%31%32&y=%31%38", "36")

    def test_unknown_route(self):
        self.assertEqual(self.request("/wrong?x=12&y=18")[0], 404)

    def test_post_rejected(self):
        status, headers, _ = self.request(self.route + "?x=12&y=18", "POST")
        self.assertEqual(status, 405)
        self.assertEqual(headers["Allow"], "GET")


class ConfigurationTests(unittest.TestCase):
    def test_email_route(self):
        self.assertEqual(
            email_path("Student.Name+demo@example.com"),
            "/Student_Name_demo_example_com",
        )

    def test_each_non_ascii_character_replaced(self):
        self.assertEqual(email_path("a--б@x.kz"), "/a____x_kz")

    def test_email_required(self):
        with self.assertRaises(ValueError):
            email_path("")


if __name__ == "__main__":
    unittest.main(verbosity=2)
