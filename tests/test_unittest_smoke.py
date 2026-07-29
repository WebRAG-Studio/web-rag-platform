import unittest


class ApplicationSmokeTest(unittest.TestCase):
    def test_application_imports_and_health_route_exists(self):
        from app.main import app

        paths = set(app.openapi()["paths"])
        self.assertIn("/health", paths)
        self.assertIn("/api/sites", paths)
        self.assertIn("/api/voice/status", paths)
        self.assertIn("/api/sites/{site_id}/progress", paths)
        self.assertIn("/api/sites/{site_id}/chat", paths)
        self.assertIn("/api/sites/{site_id}/documents", paths)
        self.assertIn("/api/sites/{site_id}/conversation/reset", paths)


if __name__ == "__main__":
    unittest.main()
