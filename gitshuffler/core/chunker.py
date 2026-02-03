import random
from typing import List

class Chunker:
    """
    Responsible for breaking a list of files into smaller chunks
    that form the content of individual commits.
    """
    
    @staticmethod
    def chunk_files(files: List[str], num_chunks: int) -> List[List[str]]:
        """
        Distributes files into num_chunks.
        Ensures every file is included exactly once.
        """
        if not files:
            return []
        
        if num_chunks <= 0:
            raise ValueError("Number of chunks must be at least 1")

        # Shuffle files to ensure randomness
        # We work on a copy to avoid side effects if the original list is used elsewhere
        shuffled_files = list(files)
        random.shuffle(shuffled_files)

        # If we have more chunks than files, cap chunks to len(files)
        # This means some "scheduled" commits might be empty if we forced it,
        # but better to just return fewer chunks.
        real_num_chunks = min(num_chunks, len(shuffled_files))
        
        chunks = [[] for _ in range(real_num_chunks)]
        
        # Distribute files round-robin style first to ensure no empty chunks (if possible)
        for i, file_path in enumerate(shuffled_files):
            chunk_index = i % real_num_chunks
            chunks[chunk_index].append(file_path)
            
        return chunks
