import unittest

class NewTest(unittest.TestCase):

    def setUp(self):
        pass

    def test_sample(self):
        self.assertEqual(1, 1)


if __name__ == '__main__':
    unittest.main()
