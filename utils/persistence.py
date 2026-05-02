import json
import os
from pathlib import Path
from core.download_engine import DownloadTask, DownloadSegment
from utils.logger import get_logger

log = get_logger(__name__)

def save_queue(queue_manager):
    """Save the current queue to a JSON file."""
    data = {
        "queue": [task_to_dict(t) for t in queue_manager._queue],
        "active": [task_to_dict(t) for t in queue_manager._active.values()],
        "completed": [task_to_dict(t) for t in queue_manager._completed]
    }
    
    config_dir = Path.home() / ".spider_manager"
    config_dir.mkdir(exist_ok=True)
    
    with open(config_dir / "queue.json", "w") as f:
        json.dump(data, f, indent=4)

def load_queue(queue_manager):
    """Load the queue from a JSON file."""
    config_path = Path.home() / ".spider_manager" / "queue.json"
    if not config_path.exists():
        return
    
    try:
        with open(config_path, "r") as f:
            data = json.load(f)
            
        for task_dict in data.get("queue", []):
            queue_manager._queue.append(dict_to_task(task_dict))
            
        for task_dict in data.get("active", []):
            # Active tasks are loaded into the queue as paused
            task = dict_to_task(task_dict)
            task.state = "ps" # PAUSED
            queue_manager._queue.append(task)
            
        for task_dict in data.get("completed", []):
            queue_manager._completed.append(dict_to_task(task_dict))
            
    except Exception as e:
        log.error("Error loading queue: %s", e)

def task_to_dict(task):
    return {
        "id": task.id,
        "url": task.url,
        "filename": task.filename,
        "save_path": task.save_path,
        "total_size": task.total_size,
        "downloaded": task.downloaded,
        "state": task.state,
        "category": task.category,
        "segments": [
            {
                "index": s.index,
                "start": s.start,
                "end": s.end,
                "downloaded": s.downloaded,
                "temp_path": s.temp_path,
                "complete": s.complete
            } for s in task.segments
        ]
    }

def dict_to_task(d):
    task = DownloadTask(
        id=d["id"],
        url=d["url"],
        filename=d["filename"],
        save_path=d["save_path"],
        total_size=d["total_size"],
        downloaded=d["downloaded"],
        state=d["state"],
        category=d.get("category", "Other")
    )
    task.segments = [
        DownloadSegment(
            index=s["index"],
            start=s["start"],
            end=s["end"],
            downloaded=s["downloaded"],
            temp_path=s["temp_path"],
            complete=s["complete"]
        ) for s in d.get("segments", [])
    ]
    return task
