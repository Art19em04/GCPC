import json, os, time, threading
from platformdirs import user_log_dir
from utils.timing import now_ns, ns_to_ms

class Telemetry:
    def __init__(self, cfg):
        self.cfg = cfg
        self.dir = cfg["telemetry"]["dir"]
        os.makedirs(self.dir, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        self.path = os.path.join(self.dir, f'{cfg["telemetry"]["file_prefix"]}_{stamp}.jsonl')
        self.lock = threading.Lock()

    def write(self, obj):
        with self.lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
