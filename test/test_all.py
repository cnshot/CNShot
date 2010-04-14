#!/usr/bin/python

import unittest

from shot_service_test import ScreenshotWorkerTest
from link_rating_test import LinkRatingTest

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTest(loader.loadTestsFromTestCase(ScreenshotWorkerTest))
    suite.addTest(loader.loadTestsFromTestCase(LinkRatingTest))

    unittest.TextTestRunner(verbosity=1).run(suite)
