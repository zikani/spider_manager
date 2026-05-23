"""
Test script for Download Engine segment handling.
Tests segment planning, splitting, and merging logic.
"""

import asyncio
import os
import tempfile
from core.download_engine import DownloadEngine, DownloadTask, DownloadSegment
from utils.logger import get_logger

log = get_logger(__name__)


def test_segment_planning():
    """Test segment splitting logic."""
    print("\n=== Testing Segment Planning ===")
    
    engine = DownloadEngine(segments=4)
    
    task = DownloadTask(
        id="test1",
        url="http://example.com/file.bin",
        filename="test.bin",
        save_path=tempfile.gettempdir(),
        total_size=1000
    )
    
    segments = engine._plan_segments(task)
    
    print(f"File size: {task.total_size} bytes")
    print(f"Number of segments: {len(segments)}")
    
    total_span = 0
    for i, seg in enumerate(segments):
        span = seg.end - seg.start + 1
        total_span += span
        print(f"  Segment {i}: {seg.start} - {seg.end} ({span} bytes)")
    
    assert total_span == task.total_size, f"Total span mismatch: {total_span} != {task.total_size}"
    print(f"✓ Total span matches file size: {total_span} bytes")
    
    task2 = DownloadTask(
        id="test2",
        url="http://example.com/file.bin",
        filename="test.bin",
        save_path=tempfile.gettempdir(),
        total_size=0
    )
    
    segments2 = engine._plan_segments(task2)
    print(f"\nUnknown size - Number of segments: {len(segments2)}")
    assert len(segments2) == 1, "Unknown size should result in single segment"
    print("✓ Unknown size handled correctly")
    
    task3 = DownloadTask(
        id="test3",
        url="http://example.com/file.bin",
        filename="test.bin",
        save_path=tempfile.gettempdir(),
        total_size=1003
    )
    
    segments3 = engine._plan_segments(task3)
    total_span3 = sum(s.end - s.start + 1 for s in segments3)
    print(f"\nFile size: {task3.total_size} bytes (not evenly divisible)")
    print(f"Number of segments: {len(segments3)}")
    print(f"Total span: {total_span3} bytes")
    assert total_span3 == task3.total_size, f"Total span mismatch: {total_span3} != {task3.total_size}"
    print("✓ Non-divisible file size handled correctly")
    
    print("\n=== Segment Planning Tests Passed ===\n")


async def test_segment_merge():
    """Test segment merging logic."""
    print("=== Testing Segment Merging ===")
    
    temp_dir = tempfile.mkdtemp()
    
    task = DownloadTask(
        id="test_merge",
        url="http://example.com/file.bin",
        filename="merged_test.bin",
        save_path=temp_dir,
        total_size=100
    )
    
    segments = []
    segment_data = [
        b"A" * 25,
        b"B" * 25,
        b"C" * 25,
        b"D" * 25,
    ]
    
    for i, data in enumerate(segment_data):
        start = i * 25
        end = start + len(data) - 1
        temp_path = os.path.join(temp_dir, f"merged_test.bin.part{i}")
        
        with open(temp_path, "wb") as f:
            f.write(data)
        
        seg = DownloadSegment(
            index=i,
            start=start,
            end=end,
            downloaded=len(data),
            temp_path=temp_path,
            complete=True
        )
        segments.append(seg)
    
    task.segments = segments
    
    print(f"Created {len(segments)} segments with test data")
    
    from core.download_engine import DownloadEngine
    engine = DownloadEngine(segments=4)
    await engine._merge_segments(task)
    
    merged_path = task.full_path
    assert os.path.exists(merged_path), "Merged file does not exist"
    
    with open(merged_path, "rb") as f:
        merged_data = f.read()
    
    expected_data = b"".join(segment_data)
    assert merged_data == expected_data, f"Merged data mismatch: {len(merged_data)} != {len(expected_data)}"
    
    print(f"✓ Merged file created: {merged_path}")
    print(f"✓ Merged file size: {len(merged_data)} bytes")
    print(f"✓ Data integrity verified")
    
    for seg in segments:
        assert not os.path.exists(seg.temp_path), f"Temp file not removed: {seg.temp_path}"
    print("✓ Temp files removed")
    
    os.remove(merged_path)
    os.rmdir(temp_dir)
    
    print("\n=== Segment Merging Tests Passed ===\n")


async def test_range_header_calculation():
    """Test Range header calculation for resume."""
    print("=== Testing Range Header Calculation ===")
    
    seg = DownloadSegment(
        index=0,
        start=0,
        end=999,
        downloaded=500,
        temp_path="/tmp/test.part0"
    )
    
    range_start = seg.start + seg.downloaded
    range_end = seg.end
    range_header = f"bytes={range_start}-{range_end}"
    
    print(f"Segment range: {seg.start} - {seg.end}")
    print(f"Already downloaded: {seg.downloaded} bytes")
    print(f"Range header: {range_header}")
    print(f"Expected: bytes=500-999")
    
    assert range_header == "bytes=500-999", f"Range header incorrect: {range_header}"
    print("✓ Range header calculation correct")
    
    seg2 = DownloadSegment(
        index=1,
        start=1000,
        end=1999,
        downloaded=0,
        temp_path="/tmp/test.part1"
    )
    
    range_start2 = seg2.start + seg2.downloaded
    range_end2 = seg2.end
    range_header2 = f"bytes={range_start2}-{range_end2}"
    
    print(f"\nSegment range: {seg2.start} - {seg2.end}")
    print(f"Already downloaded: {seg2.downloaded} bytes")
    print(f"Range header: {range_header2}")
    print(f"Expected: bytes=1000-1999")
    
    assert range_header2 == "bytes=1000-1999", f"Range header incorrect: {range_header2}"
    print("✓ Range header with no downloaded bytes correct")
    
    print("\n=== Range Header Tests Passed ===\n")


async def main():
    """Run all tests."""
    print("\n" + "="*50)
    print("Download Engine Segment Handling Tests")
    print("="*50)
    
    try:
        test_segment_planning()
        
        await test_range_header_calculation()
        
        await test_segment_merge()
        
        print("\n" + "="*50)
        print("ALL TESTS PASSED ✓")
        print("="*50 + "\n")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\n✗ TEST ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
