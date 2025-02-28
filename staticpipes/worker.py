import copy
import os

from .build_directory import BuildDirectory
from .current_info import CurrentInfo
from .exceptions import WatchFunctionalityNotImplementedException
from .source_directory import SourceDirectory


class Worker:

    def __init__(self, config, source_dir, build_directory):
        self.config = config
        self.source_directory = SourceDirectory(source_dir)
        self.build_directory = BuildDirectory(build_directory)
        self.current_info = None

        for pipeline in self.config.pipes:
            pipeline.config = self.config
            pipeline.source_directory = self.source_directory
            pipeline.build_directory = self.build_directory

    def build(self):
        self.current_info = CurrentInfo(
            context=copy.copy(self.config.context), watch=False
        )
        self._build()

    def _build(self):
        # Step 1: Prepare
        # start
        for pipeline in self.config.pipes:
            pipeline.start_prepare(self.current_info)
        # files
        rpsd = os.path.realpath(self.source_directory.dir)
        for root, dirs, files in os.walk(rpsd):
            if not self.build_directory.is_equal_to_source_dir(root):
                for file in files:
                    relative_dir = root[len(rpsd) + 1 :]
                    if not relative_dir:
                        relative_dir = "/"
                    self._prepare_file(relative_dir, file)
        # end
        for pipeline in self.config.pipes:
            pipeline.end_prepare(self.current_info)

        # Step 2: Build
        self.build_directory.prepare()
        # start
        for pipeline in self.config.pipes:
            pipeline.start_build(self.current_info)
        # files
        rpsd = os.path.realpath(self.source_directory.dir)
        for root, dirs, files in os.walk(rpsd):
            if not self.build_directory.is_equal_to_source_dir(root):
                for file in files:
                    relative_dir = root[len(rpsd) + 1 :]
                    if not relative_dir:
                        relative_dir = "/"
                    self._process_file(relative_dir, file)
        # end
        for pipeline in self.config.pipes:
            pipeline.end_build(self.current_info)
        self.build_directory.remove_all_files_we_did_not_write()

    def watch(self):
        # Only import this when watch function called,
        # so we can use build part without watch dependencies
        from .watcher import Watcher

        self.current_info = CurrentInfo(
            context=copy.copy(self.config.context), watch=True
        )
        # Build first - so we have complete site
        self._build()

        # start
        for pipeline in self.config.pipes:
            pipeline.start_watch(self.current_info)
        # Now watch
        watcher = Watcher(self)
        print("Watching ...")
        watcher.watch()

    def serve(self):

        # Only import this when watch function called,
        # so we can use build part without watch dependencies
        import threading

        from .serve import server
        from .watcher import Watcher

        self.current_info = CurrentInfo(
            context=copy.copy(self.config.context), watch=True
        )
        # Build first - so we have complete site
        self._build()

        # Start HTTP server in background
        threading.Thread(
            target=server, args=(self.build_directory.dir, "localhost", 8000)
        ).start()

        # start watching
        for pipeline in self.config.pipes:
            pipeline.start_watch(self.current_info)
        # Now watch
        watcher = Watcher(self)
        print("Watching ...")
        watcher.watch()

    def _prepare_file(self, dir, filename):
        print("Preparing {} {} ...".format(dir, filename))
        self.current_info.reset_for_new_file()
        for pipeline in self.config.pipes:
            pipeline.prepare_file(dir, filename, self.current_info)

    def _process_file(self, dir, filename):
        print("Processing {} {} ...".format(dir, filename))
        self.current_info.reset_for_new_file()
        for pipeline in self.config.pipes:
            if self.current_info.current_file_excluded:
                pipeline.file_excluded_during_build(dir, filename, self.current_info)
            else:
                pipeline.build_file(dir, filename, self.current_info)

    def process_file_during_watch(self, dir, filename):
        if self.build_directory.is_equal_to_source_dir(
            os.path.join(self.source_directory.dir, dir)
        ):
            return
        print("Processing during watch {} {} ...".format(dir, filename))
        self.current_info.reset_for_new_file()
        for pipeline in self.config.pipes:
            try:
                if self.current_info.current_file_excluded:
                    pipeline.file_changed_but_excluded_during_watch(
                        dir, filename, self.current_info
                    )
                else:
                    pipeline.file_changed_during_watch(dir, filename, self.current_info)
            except WatchFunctionalityNotImplementedException:
                print(
                    (
                        "WATCH FEATURE NOT IMPLEMENTED IN PIPELINE {}, "
                        + "YOU MAY HAVE TO BUILD MANUALLY"
                    ).format(str(pipeline))
                )
