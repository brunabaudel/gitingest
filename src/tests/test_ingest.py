import pytest
from ingest import (
    scan_directory,
    extract_files_content,
)

# Test fixtures
@pytest.fixture
def sample_query():
    return {
        'user_name': 'test_user',
        'repo_name': 'test_repo',
        'local_path': '/tmp/test_repo',
        'subpath': '/',
        'branch': 'main',
        'commit': None,
        'max_file_size': 1000000,
        'slug': 'test_user/test_repo',
        'ignore_patterns': ['*.pyc', '__pycache__', '.git'],
        'include_patterns': None,
        'pattern_type': 'exclude'
        
    }

@pytest.fixture
def temp_directory(tmp_path):
    # Creates the following structure:
    # test_repo/
    # ├── file1.txt
    # ├── file2.py
    # └── src/
    # |   ├── subfile1.txt
    # |   └── subfile2.py
    # |   └── subdir/
    # |       └── file_subdir.txt
    # |       └── file_subdir.py
    # └── dir1/
    # |   └── file_dir1.txt
    # └── dir2/
    #     └── file_dir2.txt
    
    test_dir = tmp_path / "test_repo"
    test_dir.mkdir()
    
    # Root files
    (test_dir / "file1.txt").write_text("Hello World")
    (test_dir / "file2.py").write_text("print('Hello')")
    
    # src directory and its files
    src_dir = test_dir / "src"
    src_dir.mkdir()
    (src_dir / "subfile1.txt").write_text("Hello from src")
    (src_dir / "subfile2.py").write_text("print('Hello from src')")
    
    # src/subdir and its files
    subdir = src_dir / "subdir"
    subdir.mkdir()
    (subdir / "file_subdir.txt").write_text("Hello from subdir")
    (subdir / "file_subdir.py").write_text("print('Hello from subdir')")
    
    # dir1 and its file
    dir1 = test_dir / "dir1"
    dir1.mkdir()
    (dir1 / "file_dir1.txt").write_text("Hello from dir1")
    
    # dir2 and its file
    dir2 = test_dir / "dir2"
    dir2.mkdir()
    (dir2 / "file_dir2.txt").write_text("Hello from dir2")
    
    return test_dir

def test_scan_directory(temp_directory, sample_query):
    result = scan_directory(
        str(temp_directory),
        query=sample_query
    )
    
    assert result['type'] == 'directory'
    assert result['file_count'] == 8  # All .txt and .py files
    assert result['dir_count'] == 4   # src, src/subdir, dir1, dir2
    assert len(result['children']) == 5  # file1.txt, file2.py, src, dir1, dir2

def test_extract_files_content(temp_directory, sample_query):
    nodes = scan_directory(
        str(temp_directory),
        query=sample_query
    )
    
    files = extract_files_content(sample_query, nodes, max_file_size=1000000)
    assert len(files) == 8  # All .txt and .py files
    
    # Check for presence of key files
    paths = [f['path'] for f in files]
    assert any('file1.txt' in p for p in paths)
    assert any('subfile1.txt' in p for p in paths)
    assert any('file2.py' in p for p in paths)
    assert any('subfile2.py' in p for p in paths)
    assert any('file_subdir.txt' in p for p in paths)
    assert any('file_dir1.txt' in p for p in paths)
    assert any('file_dir2.txt' in p for p in paths)



def test_include_pattern_txt(temp_directory, sample_query):
    """Test including only .txt files"""
    sample_query['pattern_type'] = 'include'
    sample_query['include_patterns'] = ['*.txt']
    
    nodes = scan_directory(
        str(temp_directory),
        query=sample_query
    )
    
    files = extract_files_content(sample_query, nodes, max_file_size=1000000)
    
    # Should only include .txt files
    assert len(files) == 5  # All .txt files
    paths = [f['path'] for f in files]
    assert all('.txt' in p for p in paths)
    assert not any('.py' in p for p in paths)

def test_include_pattern_nonexistent(temp_directory, sample_query):
    """Test with pattern that matches no files"""
    sample_query['pattern_type'] = 'include'
    sample_query['include_patterns'] = ['*.qwerty']
    
    nodes = scan_directory(
        str(temp_directory),
        query=sample_query
    )
    
    files = extract_files_content(sample_query, nodes, max_file_size=1000000)
    assert len(files) == 0  # No files should match

def test_include_pattern_src_folder(temp_directory, sample_query):
    """Test various src folder pattern variations"""
    pattern_tests = [
        ('src/*', 2),      # Files directly in src
        ('/src/*', 2),     # Same with leading slash
        ('/src/', 4),      # All files in src and subdirs
        ('/src*', 4),      # All files in src and subdirs
    ]
    
    for pattern, expected_count in pattern_tests:
        sample_query['pattern_type'] = 'include'
        sample_query['include_patterns'] = [pattern]
        
        nodes = scan_directory(
            str(temp_directory),
            query=sample_query
        )
        
        files = extract_files_content(sample_query, nodes, max_file_size=1000000)
        assert len(files) == expected_count, f"Pattern '{pattern}' should match {expected_count} files"
        
        paths = [f['path'] for f in files]
        assert all('src' in p for p in paths), f"Pattern '{pattern}' should only match files in src directory"

def test_multiple_include_patterns(temp_directory, sample_query):
    """Test combinations of multiple include patterns"""
    pattern_tests = [
        (['*.txt', '*.py'], 8),                # All text and python files
        (['/src/*', '*.txt'], 6),              # All files in src + all txt files
        (['/src*', '*.txt'], 7),               # All files in src tree + all txt files
    ]
    
    for patterns, expected_count in pattern_tests:
        sample_query['pattern_type'] = 'include'
        sample_query['include_patterns'] = patterns
        
        nodes = scan_directory(
            str(temp_directory),
            query=sample_query
        )
        
        files = extract_files_content(sample_query, nodes, max_file_size=1000000)
        assert len(files) == expected_count, f"Patterns {patterns} should match {expected_count} files"
        
        # Verify specific pattern matches
        paths = [f['path'] for f in files]
        if '*.txt' in patterns:
            assert any('.txt' in p for p in paths)
        if '*.py' in patterns:
            assert any('.py' in p for p in paths)
        if any('src' in p for p in patterns):
            assert any('/src/' in p for p in paths)



