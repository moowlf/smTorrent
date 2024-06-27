
import os

class FileManager:

    def __init__(self, metadata) -> None:
        
        self._files = metadata.files()

        # Create the files
        for file in self._files:

            path = file.path.split("/")

            if len(path) > 1:
                path = path[:-1]
                path = "/".join(path)
                os.makedirs(path, exist_ok=True)

            with open(file.path, "wb") as f:
                f.seek(file.length - 1)
                f.write(b"\0")
    
    def write(self, index, data):

        current_offset = 0

        for file in self._files:

            if current_offset + file.length > index:
                with open(file.path, "r+b") as f:
                    f.seek(index - current_offset)
                    f.write(data)
                    return

            current_offset += file.length