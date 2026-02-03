import unittest
from gitshuffler.core.chunker import Chunker

class TestChunker(unittest.TestCase):
    def test_chunking_exact(self):
        files = ["a", "b", "c", "d"]
        chunks = Chunker.chunk_files(files, 2)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(len(chunks[0]) + len(chunks[1]), 4)

    def test_more_chunks_than_files(self):
        files = ["a", "b"]
        chunks = Chunker.chunk_files(files, 5)
        self.assertEqual(len(chunks), 2) # Should actuaully be capped at len(files) per logic

if __name__ == '__main__':
    unittest.main()
