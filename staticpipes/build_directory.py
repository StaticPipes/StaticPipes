import os
import pathlib


class BuildDirectory:

    def __init__(self, dir: str):
        self.dir = dir
        self.written_files: list = []

    def prepare(self):
        os.makedirs(self.dir, exist_ok=True)

    def write(self, dir: str, name: str, contents):
        if dir != "/":
            if dir.startswith("/"):
                dir = dir[1:]
            os.makedirs(os.path.join(self.dir, dir), exist_ok=True)
            f = os.path.join(self.dir, dir, name)
        else:
            f = os.path.join(self.dir, name)
        if isinstance(contents, bytes):
            with open(f, "wb") as fp:
                fp.write(contents)
        else:
            with open(f, "w") as fp:
                fp.write(contents)
        self.written_files.append((dir if dir else "/", name))

    def is_equal_to_source_dir(self, directory: str) -> bool:
        return os.path.realpath(self.dir) == os.path.realpath(directory)

    def remove_all_files_we_did_not_write(self):
        rpsd = os.path.realpath(self.dir)
        for root, dirs, files in os.walk(rpsd):
            for file in files:
                relative_dir = root[len(rpsd) + 1 :]
                if not relative_dir:
                    relative_dir = "/"
                if not (relative_dir, file) in self.written_files:
                    if relative_dir and relative_dir != "/":
                        pathlib.Path(
                            os.path.join(self.dir, relative_dir, file)
                        ).unlink()
                    else:
                        pathlib.Path(os.path.join(self.dir, file)).unlink()
