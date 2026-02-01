import os
import uuid
from werkzeug.utils import secure_filename

TMP_DIR = "/tmp/lifedger_scans"

os.makedirs(TMP_DIR, exist_ok=True)

def save_temp_file(file):
    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1]

    temp_name = f"{uuid.uuid4()}.{ext}"
    path = os.path.join(TMP_DIR, temp_name)

    file.save(path)
    return path