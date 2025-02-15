import os
import shutil
import tempfile

import staticpipes.build_directory
import staticpipes.config
import staticpipes.pipes.exclude_underscore_directories
import staticpipes.pipes.jinja2
import staticpipes.watcher
import staticpipes.worker
from staticpipes.current_info import CurrentInfo


class PipeJinja2TestClass(staticpipes.pipes.jinja2.PipeJinja2):
    def _actually_build_template(
        self, dir: str, filename: str, current_info: CurrentInfo
    ) -> None:
        # In our tests, we want to keep a count of which templates are actually built
        # So we can check that dependent templates are build efficiently during watch
        if hasattr(self, "_actually_built_templates"):
            self._actually_built_templates.append((dir, filename))
        else:
            self._actually_built_templates = [(dir, filename)]
        # Do the actual work
        super()._actually_build_template(dir, filename, current_info)


def test_jinja2_then_watch_while_change_output_file(monkeypatch):
    monkeypatch.setattr(staticpipes.watcher.Watcher, "watch", lambda self: None)
    # setup
    in_dir = tempfile.mkdtemp(prefix="staticpipes_tests_")
    shutil.copytree(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "fixtures",
            "jinja2_and_exclude_underscore_directories",
        ),
        os.path.join(in_dir, "in"),
    )
    out_dir = tempfile.mkdtemp(prefix="staticpipes_tests_")
    jinja2_pipeline = PipeJinja2TestClass(extensions=["html"])
    config = staticpipes.config.Config(
        pipes=[
            staticpipes.pipes.exclude_underscore_directories.PipeExcludeUnderscoreDirectories(),  # noqa
            jinja2_pipeline,
        ],
        context={"hello": "World"},
    )
    worker = staticpipes.worker.Worker(
        config,
        os.path.join(in_dir, "in"),
        out_dir,
    )
    # run
    worker.watch()
    # test _watch_rebuild_all not set by pipe
    assert jinja2_pipeline._watch_rebuild_all is False
    # test 1
    with open(os.path.join(out_dir, "index.html")) as fp:
        contents = fp.read()
    contents = "".join([i.strip() for i in contents.split("\n")])
    assert (
        "<!doctype html><html><head><title>Hello</title></head><body><h1>Hello</h1>Hello World</body></html>"  # noqa
        == contents
    )
    # Edit index.html
    with open(os.path.join(in_dir, "in", "index.html")) as fp:
        contents = fp.read()
    with open(os.path.join(in_dir, "in", "index.html"), "w") as fp:
        fp.write(contents.replace("Hello", "Goodbye"))
    # Manually trigger watch handler, and test which templates are actually built
    jinja2_pipeline._actually_built_templates = []
    worker.process_file_during_watch("/", "index.html")
    # about.html should not be rebuilt, it or it's layout file wasn't touched.
    assert jinja2_pipeline._actually_built_templates == [("", "index.html")]
    # test 2
    with open(os.path.join(out_dir, "index.html")) as fp:
        contents = fp.read()
    contents = "".join([i.strip() for i in contents.split("\n")])
    assert (
        "<!doctype html><html><head><title>Hello</title></head><body><h1>Hello</h1>Goodbye World</body></html>"  # noqa
        == contents
    )


def test_jinja2_then_watch_while_change_parent_one_level_up(monkeypatch):
    monkeypatch.setattr(staticpipes.watcher.Watcher, "watch", lambda self: None)
    # setup
    in_dir = tempfile.mkdtemp(prefix="staticpipes_tests_")
    shutil.copytree(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "fixtures",
            "jinja2_and_exclude_underscore_directories",
        ),
        os.path.join(in_dir, "in"),
    )
    out_dir = tempfile.mkdtemp(prefix="staticpipes_tests_")
    jinja2_pipeline = PipeJinja2TestClass(extensions=["html"])
    config = staticpipes.config.Config(
        pipes=[
            staticpipes.pipes.exclude_underscore_directories.PipeExcludeUnderscoreDirectories(),  # noqa
            jinja2_pipeline,
        ],
        context={"hello": "World"},
    )
    worker = staticpipes.worker.Worker(
        config,
        os.path.join(in_dir, "in"),
        out_dir,
    )
    # run
    worker.watch()
    # test _watch_rebuild_all not set by pipe
    assert jinja2_pipeline._watch_rebuild_all is False
    # test 1
    with open(os.path.join(out_dir, "index.html")) as fp:
        contents = fp.read()
    contents = "".join([i.strip() for i in contents.split("\n")])
    assert (
        "<!doctype html><html><head><title>Hello</title></head><body><h1>Hello</h1>Hello World</body></html>"  # noqa
        == contents
    )
    # Edit base template
    with open(os.path.join(in_dir, "in", "_templates", "layout.html")) as fp:
        contents = fp.read()
    with open(os.path.join(in_dir, "in", "_templates", "layout.html"), "w") as fp:
        fp.write(contents.replace("Hello", "Goodbye"))
    # Manually trigger watch handler, and test which templates are actually built
    jinja2_pipeline._actually_built_templates = []
    worker.process_file_during_watch("_templates", "layout.html")
    assert sorted(jinja2_pipeline._actually_built_templates) == [
        ("", "about.html"),
        ("", "index.html"),
    ]
    # test 2
    with open(os.path.join(out_dir, "index.html")) as fp:
        contents = fp.read()
    contents = "".join([i.strip() for i in contents.split("\n")])
    assert (
        "<!doctype html><html><head><title>Hello</title></head><body><h1>Goodbye</h1>Hello World</body></html>"  # noqa
        == contents
    )


def test_jinja2_then_watch_while_change_parent_two_levels_up(monkeypatch):
    monkeypatch.setattr(staticpipes.watcher.Watcher, "watch", lambda self: None)
    # setup
    in_dir = tempfile.mkdtemp(prefix="staticpipes_tests_")
    shutil.copytree(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "fixtures",
            "jinja2_and_exclude_underscore_directories",
        ),
        os.path.join(in_dir, "in"),
    )
    out_dir = tempfile.mkdtemp(prefix="staticpipes_tests_")
    jinja2_pipeline = PipeJinja2TestClass(extensions=["html"])
    config = staticpipes.config.Config(
        pipes=[
            staticpipes.pipes.exclude_underscore_directories.PipeExcludeUnderscoreDirectories(),  # noqa
            jinja2_pipeline,
        ],
        context={"hello": "World"},
    )
    worker = staticpipes.worker.Worker(
        config,
        os.path.join(in_dir, "in"),
        out_dir,
    )
    # run
    worker.watch()
    # test _watch_rebuild_all not set by pipe
    assert jinja2_pipeline._watch_rebuild_all is False
    # test 1
    with open(os.path.join(out_dir, "index.html")) as fp:
        contents = fp.read()
    contents = "".join([i.strip() for i in contents.split("\n")])
    assert (
        "<!doctype html><html><head><title>Hello</title></head><body><h1>Hello</h1>Hello World</body></html>"  # noqa
        == contents
    )
    # Edit base template
    with open(os.path.join(in_dir, "in", "_templates", "base.html")) as fp:
        contents = fp.read()
    with open(os.path.join(in_dir, "in", "_templates", "base.html"), "w") as fp:
        fp.write(contents.replace("Hello", "Goodbye"))
    # Manually trigger watch handler, and test which templates are actually built
    jinja2_pipeline._actually_built_templates = []
    worker.process_file_during_watch("_templates", "base.html")
    assert sorted(jinja2_pipeline._actually_built_templates) == [
        ("", "about.html"),
        ("", "index.html"),
    ]
    # test 2
    with open(os.path.join(out_dir, "index.html")) as fp:
        contents = fp.read()
    contents = "".join([i.strip() for i in contents.split("\n")])
    assert (
        "<!doctype html><html><head><title>Goodbye</title></head><body><h1>Hello</h1>Hello World</body></html>"  # noqa
        == contents
    )


def test_jinja2_unknown_depends_then_watch_while_change_library(monkeypatch):
    monkeypatch.setattr(staticpipes.watcher.Watcher, "watch", lambda self: None)
    # setup
    in_dir = tempfile.mkdtemp(prefix="staticpipes_tests_")
    shutil.copytree(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "fixtures",
            "jinja2_unknown_dependents",
        ),
        os.path.join(in_dir, "in"),
    )
    out_dir = tempfile.mkdtemp(prefix="staticpipes_tests_")
    jinja2_pipeline = PipeJinja2TestClass(extensions=["html"])
    config = staticpipes.config.Config(
        pipes=[
            staticpipes.pipes.exclude_underscore_directories.PipeExcludeUnderscoreDirectories(),  # noqa
            jinja2_pipeline,
        ],
        context={"content_template_filename": "/_templates/content.html"},
    )
    worker = staticpipes.worker.Worker(
        config,
        os.path.join(in_dir, "in"),
        out_dir,
    )
    # run
    worker.watch()
    # test _watch_rebuild_all set automatically by pipe due to unknown dependencies
    assert jinja2_pipeline._watch_rebuild_all is True
    # test 1
    with open(os.path.join(out_dir, "index.html")) as fp:
        contents = fp.read()
    contents = "".join([i.strip() for i in contents.split("\n")])
    assert (
        "<!doctype html><html><head><title>Hello</title></head><body>Hello World</body></html>"  # noqa
        == contents
    )
    # Edit base template
    with open(os.path.join(in_dir, "in", "_templates", "content.html")) as fp:
        contents = fp.read()
    with open(os.path.join(in_dir, "in", "_templates", "content.html"), "w") as fp:
        fp.write(contents.replace("Hello", "Goodbye"))
    # Manually trigger watch handler, and test which templates are actually built
    jinja2_pipeline._actually_built_templates = []
    worker.process_file_during_watch("_templates", "content.html")
    assert sorted(jinja2_pipeline._actually_built_templates) == [
        ("", "about.html"),
        ("", "index.html"),
    ]
    # test 2
    with open(os.path.join(out_dir, "index.html")) as fp:
        contents = fp.read()
    contents = "".join([i.strip() for i in contents.split("\n")])
    assert (
        "<!doctype html><html><head><title>Hello</title></head><body>Goodbye World</body></html>"  # noqa
        == contents
    )
