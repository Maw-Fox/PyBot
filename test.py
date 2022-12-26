import json
import unittest
import modules.utils as utils

from modules.config import do_crypt

__f = open('tests/tests.json', 'r', encoding='UTF-8')
TESTS: dict[str, list[dict[str, str | bool]]] = json.load(__f)
__f.close()
AGE_TESTER: list[dict[str, str | bool]] = TESTS['age_tester']


class TestMainTest(unittest.TestCase):
    def test_age_tester(self) -> None:
        """
        Test cases for expected string manips.
        """
        for test in AGE_TESTER:
            self.assertEqual(
                utils.age_tester(test['test']),
                test['expects']
            )


class TestConfigTest(unittest.TestCase):
    def test_crypto(self) -> None:
        """
        Make sure forward/reverse cryptography is generating expected values.
        """
        phrase: str = 'cat'
        password: str = 'dog'
        hash: str = (
            '13c0108b51abd4a3c51c5ddd97204a9c' +
            '3ae614ebccb75a606c3b6865aed6744e'
        )

        # Forward test
        self.assertEqual(
            do_crypt(phrase, password, _t='sha256').hex(),
            hash
        )

        rev: str = str(do_crypt(phrase, hash, False, _t='sha256'), 'utf-8')

        # Reverse test
        self.assertEqual(
            rev.replace('\x00', ''),
            password
        )


def run() -> None:
    unittest.main()


run()
