import json
import unittest
import modules.utils as utils

__f = open('tests/tests.json', 'r', encoding='UTF-8')
TESTS: dict[str, list[dict[str, str | bool]]] = json.load(__f)
__f.close()

AGE_TESTER: list[dict[str, str | bool]] = TESTS['age_tester']


class TestAgeTest(unittest.TestCase):
    def test_age_tester(self) -> None:
        for test in AGE_TESTER:
            self.assertEqual(utils.age_tester(test['test']), test['expects'])


def run() -> None:
    unittest.main()


run()
