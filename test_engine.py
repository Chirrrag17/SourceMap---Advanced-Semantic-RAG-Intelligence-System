import json
import tempfile
import unittest
from pathlib import Path

from codebase_context.indexer import build_index, load_index, save_index
from codebase_context.search import search


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "auth.py").write_text(
            "class AuthMiddleware:\n    def check_session(self, request):\n        return validate_token(request.token)\n",
            encoding="utf-8",
        )
        (self.root / "README.md").write_text("Repository overview and local instructions.\n", encoding="utf-8")
        (self.root / "node_modules").mkdir()
        (self.root / "node_modules" / "ignored.js").write_text("auth token secret", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_index_skips_dependency_directories_and_finds_source(self):
        index = build_index(self.root)
        paths = {chunk["path"] for chunk in index["chunks"]}
        self.assertIn("src/auth.py", paths)
        self.assertNotIn("node_modules/ignored.js", paths)
        self.assertEqual(index["file_count"], 2)

    def test_search_ranks_auth_symbol_and_returns_line_reference(self):
        index = build_index(self.root)
        results = search(index, "auth middleware session", limit=3)
        self.assertTrue(results)
        self.assertEqual(results[0].path, "src/auth.py")
        self.assertGreaterEqual(results[0].start_line, 1)
        self.assertIn("AuthMiddleware", results[0].symbols)

    def test_index_round_trip(self):
        index = build_index(self.root)
        path = save_index(index, self.root / "out" / "index.json")
        loaded = load_index(path)
        self.assertEqual(loaded["chunk_count"], index["chunk_count"])


if __name__ == "__main__":
    unittest.main()
