import logging
import os

from markdown_it import MarkdownIt

from staticpipes.checks.html_tags import CheckHtmlTags
from staticpipes.checks.html_with_tidy import CheckHtmlWithTidy
from staticpipes.checks.internal_links import CheckInternalLinks
from staticpipes.config import Config
from staticpipes.jinja2_environment import Jinja2Environment
from staticpipes.pipes.collection_records_process import PipeCollectionRecordsProcess
from staticpipes.pipes.copy import PipeCopy
from staticpipes.pipes.exclude_underscore_directories import (
    PipeExcludeUnderscoreDirectories,
)
from staticpipes.pipes.load_collection_python_docs import PipeLoadCollectionPythonDocs
from staticpipes.pipes.process import PipeProcess
from staticpipes.process_base import BaseProcessor
from staticpipes.processes.change_extension import ProcessChangeExtension
from staticpipes.processes.jinja2 import ProcessJinja2
from staticpipes.processes.markdown_yaml_to_html_context import (
    ProcessMarkdownYAMLToHTMLContext,
)


def render_markdown(content):
    md = MarkdownIt()
    return md.render(content) if content else ""


jinja2_environment = Jinja2Environment(filters={"render_markdown": render_markdown})


class ProcessMarkdownPages(BaseProcessor):

    def process_file(
        self,
        source_dir: str,
        source_filename: str,
        process_current_info,
        current_info,
    ):
        # Change all files to be in a directory with index.html
        # so we don't get .html in our site
        filename_main_bit = process_current_info.filename[:-5]
        if filename_main_bit != "index":
            process_current_info.filename = "index.html"
            process_current_info.dir = (
                filename_main_bit
                if process_current_info.dir == "/"
                else process_current_info.dir + "/" + filename_main_bit
            )
        # Add extra info we'll use in template
        breadcrumbs = []
        path = ""
        source_dir_bits = [i for i in source_dir.split("/") if i]
        for dir in source_dir_bits:
            path += dir + "/"
            breadcrumbs.append((path, dir))

        if source_filename != "index.md":
            # It should be
            # breadcrumbs.append((None, process_current_info.context["title"]))
            # But ProcessMarkdownYAMLToHTMLContext uses current_info.set_context
            # when I think it should use process_current_info.context
            # Also, ProcessJinja2 only takes 1 context when it should take both
            # Until that sorted, just do ...
            breadcrumbs.append((None, current_info.get_context("title")))

        process_current_info.context["breadcrumbs"] = breadcrumbs


config = Config(
    pipes=[
        PipeExcludeUnderscoreDirectories(),
        PipeProcess(
            extensions=["md"],
            processors=[
                ProcessMarkdownYAMLToHTMLContext(),
                ProcessChangeExtension("html"),
                ProcessMarkdownPages(),
                ProcessJinja2(
                    template="_templates/content.html",
                    jinja2_environment=jinja2_environment,
                ),
            ],
        ),
        PipeLoadCollectionPythonDocs(
            collection_name="python_docs",
            module_names=["staticpipes"],
        ),
        PipeCollectionRecordsProcess(
            collection_name="python_docs",
            output_dir="reference",
            context_key_record_data="python_document",
            processors=[
                ProcessJinja2(
                    template="_templates/reference.html",
                    jinja2_environment=jinja2_environment,
                ),
            ],
        ),
        PipeCopy(extensions=["css"]),
    ],
    checks=[
        CheckHtmlWithTidy(),
        CheckHtmlTags(),
        CheckInternalLinks(),
    ],
    context={"base_url": os.getenv("BASE_URL", "/")},
)


if __name__ == "__main__":
    from staticpipes.cli import cli

    base_url = os.getenv("BASE_URL", "/")
    if base_url != "/":
        output_dir = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "_site", base_url.lstrip("/")
        )
    else:
        output_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "_site")
    cli(
        config,
        os.path.join(os.path.dirname(os.path.realpath(__file__)), "docs"),
        output_dir,
        log_level=logging.DEBUG,
    )
