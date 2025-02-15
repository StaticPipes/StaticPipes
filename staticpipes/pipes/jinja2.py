import os.path

import jinja2
import jinja2.meta

import staticpipes.utils
from staticpipes.current_info import CurrentInfo
from staticpipes.pipe_base import BasePipe


class PipeJinja2(BasePipe):
    """A pipeline that builds Jinja2 templates to output files

    Pass:

    - extensions - a list of file extensions that will be copied
    eg ["jinja2"].
    defaults to ["html"]

    - watch_rebuild_all - Normally we try and be smart and only
    rebuild what we need to in watch mode.
    However, if you encounter a bug wth that you can set this to True
    and we will always rebuild all templates during watch mode.
    This is inefficient but is sure to bypass any dependency bugs.


    """

    def __init__(self, extensions=["html"], watch_rebuild_all=False):
        self.extensions = extensions
        self.jinja2_env = None
        self._template_information: dict = {}
        self._watch_rebuild_all = watch_rebuild_all

    def start_build(self, current_info: CurrentInfo) -> None:
        self.jinja2_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.source_directory.dir),
            autoescape=jinja2.select_autoescape(),
        )

    def _actually_build_template(
        self, dir: str, filename: str, current_info: CurrentInfo
    ) -> None:
        # print("JINJA2 {} {}".format(dir, filename))
        template = self.jinja2_env.get_template(os.path.join(dir, filename))
        contents = template.render(current_info.context)
        self.build_directory.write(dir, filename, contents)

    def _update_template_information(
        self, dir: str, filename: str, file_excluded: bool
    ):

        path = staticpipes.utils.make_path_from_dir_and_filename(dir, filename)

        self._template_information[path] = {
            "file_excluded": file_excluded,
        }

        if not self._watch_rebuild_all:
            ast = self.jinja2_env.parse(
                source=self.source_directory.get_contents_as_str(dir, filename),
                filename=os.path.join(dir, filename),
            )

            referenced_templates: list = [
                ("/" + i if isinstance(i, str) and not i.startswith("/") else i)
                for i in jinja2.meta.find_referenced_templates(ast)
            ]

            if len([i for i in referenced_templates if i is None]) > 0:
                # A None here means that one of the dependencies for
                # these templates is unknown.
                # We aren't clever enough (yet) to handle dependency
                # finding in these circumstances,
                # so just flip into _watch_rebuild_all mode instead.
                # More inefficient but output will be correct.
                self._watch_rebuild_all = True
            else:
                self._template_information[path][
                    "referenced_templates"
                ] = referenced_templates

    def build_file(self, dir: str, filename: str, current_info: CurrentInfo) -> None:
        if not staticpipes.utils.does_filename_have_extension(
            filename, self.extensions
        ):
            return

        self._actually_build_template(dir, filename, current_info)

        if current_info.watch:
            self._update_template_information(dir, filename, False)

    def file_excluded_during_build(
        self, dir: str, filename: str, current_info: CurrentInfo
    ) -> None:
        if not staticpipes.utils.does_filename_have_extension(
            filename, self.extensions
        ):
            return

        if current_info.watch:
            self._update_template_information(dir, filename, True)

    def file_changed_during_watch(self, dir, filename, current_info):
        self._template_changed_during_watch(dir, filename, current_info, False)

    def file_changed_but_excluded_during_watch(self, dir, filename, current_info):
        self._template_changed_during_watch(dir, filename, current_info, True)

    def _template_changed_during_watch(
        self, dir: str, filename: str, current_info, file_excluded: bool
    ):
        if not staticpipes.utils.does_filename_have_extension(
            filename, self.extensions
        ):
            return

        self._update_template_information(dir, filename, file_excluded)

        if self._watch_rebuild_all:
            for template_path, template_info in self._template_information.items():
                if not template_info["file_excluded"]:
                    d, f = staticpipes.utils.make_dir_and_filename_from_path(
                        template_path
                    )
                    self._actually_build_template(d, f, current_info)
        else:

            for t in self._get_templates_dependent_on_template_to_rebuild(
                dir, filename, file_excluded
            ):
                d, f = staticpipes.utils.make_dir_and_filename_from_path(t)
                self._actually_build_template(d, f, current_info)

    def _get_templates_dependent_on_template_to_rebuild(
        self, dir: str, filename: str, file_excluded: bool
    ) -> list:

        path = staticpipes.utils.make_path_from_dir_and_filename(dir, filename)

        out: list = [] if file_excluded else [path]

        for template_path, template_info in self._template_information.items():
            if path in template_info["referenced_templates"]:
                # Add this path to out, if we want to build it
                if not template_info["file_excluded"]:
                    out.append(template_path)
                # Whether we build it or not,
                # call recursively to look for dependencies in this template
                d, f = staticpipes.utils.make_dir_and_filename_from_path(template_path)
                for x in self._get_templates_dependent_on_template_to_rebuild(
                    d, f, True
                ):
                    if x not in out:
                        out.append(x)
        return out
