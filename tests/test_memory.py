import unittest
import os
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
from src.memory import MemorySystem

class TestMemory(unittest.TestCase):
    def setUp(self):
        self.db_path = "data/test_memory.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.memory = MemorySystem(self.db_path)

    def test_add_and_search_episode(self):
        self.memory.add_episode("Test Prompt", "Test Response")
        results = self.memory.search_episodes("Test")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "Test Prompt")

    def test_add_fact(self):
        self.memory.add_fact("test", "key", "value")
        # Direct check if needed or just verify no crash
        cursor = self.memory.conn.cursor()
        cursor.execute("SELECT value FROM semantic_memory WHERE key='key'")
        row = cursor.fetchone()
        self.assertEqual(row[0], "value")

    def tearDown(self):
        self.memory.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

if __name__ == '__main__':
    unittest.main()
