# StaticPipes, the flexible and extendable static site website generator in Python

Most static website generators have technologies, conventions and source code layout requirements that you have to 
follow. 

Instead this is a framework and a collection of pipelines to process your source files. 
Use only the pipelines you want and configure them as you need. 

If you are a python programmer and need something different, then write a python class that extends our base class and 
write what you need.

## Install

* `pip install staticpipes[allbuild]` - if you just want to build a website
* `pip install staticpipes[allbuild,dev]` - if you want to develop a website

If you are developing the actual tool, check it out from git, create a virtual environment and run 
`python3 -m pip install --upgrade pip && pip install -e .[allbuild,dev,staticpipesdev]`

## Getting started

Configure this tool with a simple Python `file.py` in the root of your site. This copies files with these extensions 
into the `_site` directory:

```python
from staticpipes.config import Config
from staticpipes.pipes.copy import PipeCopy

import os

config = Config(
    pipes=[
        PipeCopy(extensions=["html", "css", "js"]),
    ],
)

if __name__ == "__main__":
    from staticpipes.cli import cli
    cli(config, os.path.join(os.path.dirname(os.path.realpath(__file__))), "_site")
```

Then run with:

    python file.py build
    python file.py watch
    python file.py serve

Use Jinja2 templates for html files:

```python
from staticpipes.pipes.jinja2 import PipeJinja2

config = Config(
    pipes=[
        PipeCopy(extensions=["css", "js"]),
        PipeJinja2(extensions=["html"]),
    ],
    context={
        "title": "An example website",
    }
)
```

If you like putting your CSS and JS in a `assets` directory in your source, you can do:

```python
config = Config(
    pipes=[
        PipeCopy(extensions=["css", "js"], source_sub_directory="assets"),
        PipeJinja2(extensions=["html"]),
    ],
    context={
        "title": "An example website",
    }
)
```

(Now `assets/css/main.css` will appear in `css/main.css`)

Version your assets:

```python
from staticpipes.pipes.copy_with_versioning import PipeCopyWithVersioning

config = Config(
    pipes=[
        PipeCopyWithVersioning(extensions=["css", "js"]),
        PipeJinja2(extensions=["html"]),
    ]
)
```

(files like `js/main.ceba641cf86025b52dfc12a1b847b4d8.js` will be created, and that string will be available in Jinja2 
variables so you can load them.)

Exclude library files like `_layouts/base.html` templates:

```python
from staticpipes.pipes.exclude_underscore_directories import PipeExcludeUnderscoreDirectories

config = Config(
    pipes=[
        PipeExcludeUnderscoreDirectories(),
        PipeCopyWithVersioning(extensions=["css", "js"]),
        PipeJinja2(extensions=["html"]),
    ],
)
```

Minify your JS & CSS:

```python
from staticpipes.pipes.javascript_minifier import PipeJavascriptMinifier
from staticpipes.pipes.css_minifier import PipeCSSMinifier

config = Config(
    pipes=[
        PipeExcludeUnderscoreDirectories(),
        PipeJavascriptMinifier(),
        PipeCSSMinifier(),
        PipeJinja2(extensions=["html"]),
    ],
)
```

Use the special Process pipeline to chain together processes, so the same source file goes through multiple steps 
before being published. This minifies then versions JS & CSS, putting new filenames in the context for templates to use:

```python
from staticpipes.pipes.process import PipeProcess
from staticpipes.processes.version import ProcessVersion
from staticpipes.processes.javascript_minifier import ProcessJavascriptMinifier
from staticpipes.processes.css_minifier import ProcessCSSMinifier

config = Config(
    pipes=[
        PipeExcludeUnderscoreDirectories(),
        PipeProcess(extensions=["js"], processors=[ProcessJavascriptMinifier(), ProcessVersion()]),
        PipeProcess(extensions=["css"], processors=[ProcessCSSMinifier(), ProcessVersion()]),
        PipeJinja2(extensions=["html"]),
    ],
)
```

Or write your own pipeline! For instance, if you want your robots.txt to block AI crawlers here's all you need:

```python
from staticpipes.pipes.pipe_base.py import BasePipe

class PipeNoAIRobots(BasePipe):
    def start_build(self, current_info) -> None:
        r = requests.get("https://raw.githubusercontent.com/ai-robots-txt/ai.robots.txt/refs/heads/main/robots.txt")
        self.build_directory.write("/", "robots.txt", r.text)

config = Config(
    pipes=[
        PipeNoAIRobots(),
    ],
)
```

## How it works

Instances of pipeline classes are created and passed to the config. The same instance is used throughout. This means 
if a pipeline wants to store information early on to use later, it can do. Pipelines classes should extend 
the `staticpipes.pipe_base.BasePipe` class.

### Build stage 

During building, the `start_build` method is called on each pipeline. Methods are always called on each pipeline in the 
order the pipelines are passed to the config.

Then, the `build_file` method is called on each pipeline for each file in the source directory. The order of files in 
the directory is not set and should not be relied on.

The `end_build` method is called on each pipeline.

A pipeline should deal with the file completely or not at all. Either it ignores it or it does something that ends 
with a method on `self.build_directory` being called to write some content to the site. 

A pipeline can write zero to many files to the site for a single source file. For instance, a image processing 
pipeline could write multiple files at different resolutions for every image in the source.

A `current_info` object is passed to all methods. This contains information and can be used to set information.

A pipeline can mark a file as excluded (by setting `current_info.current_file_excluded`) , which means that later 
pipelines won't have `build_file` called for that file. However, they will have `file_excluded_during_build` called for 
each excluded file.

A context is maintained on `current_info.context`. This is a dictionary of values that is initially set in the 
configuration object but pipelines can read and modify. For example, an earlier pipeline might version a CSS file 
at a particular location and store the location in the context. A later pipeline might build Jinja2 templates 
with the context as temple variables so the html can actually load the CSS.

### Prepare stage

Before the build stage is started a prepare stage is done. `start_prepare` is called on each pipeline, then 
`prepare_file` for each file, then `end_prepare`. This can be used to collect  info before building. For example, 
see the `PipeCopyWithVersioning` pipeline that works out the filename for any file it will work with in the prepare 
stage. This ensures information about the new file name is already in the context before a single build method is 
called.

It's not possible to exclude any files during the prepare stage.


### Watch mode

In watch mode, a normal build is done first. The `start_watch` method is then called on each pipeline. Then every time 
a file is changed, the `file_changed_during_watch` or `file_changed_but_excluded_during_watch` method is called for 
that file. There is no `end_watch` method, as the watch stage is ended by the user forcibly quitting the program.

Writing pipelines for watch mode can be more complicated than writing pipelines for build mode. This is due to the 
idea of dependencies. If the process of building source file A depends in some way on building source file B, 
when source file B changes then both files A and B must be rebuilt. 

Dependencies are left up to each pipeline to handle. Generally the pipeline should build up dependency information 
during the prepare or build stage and cache it for use during the watch stage. During prepare and build stage a flag 
`current_info.watch` is set if watch will be called afterwards. This means pipelines can avoid doing any extra work 
tracking dependencies for the watch stage if it isn't going to be called.

If a pipeline has no possible interactions with dependencies it can usually use the same code for building. 
Just add this to the pipeline:

```python
    def file_changed_during_watch(self, dir, filename, current_info):
        self.build_file(dir, filename, current_info)
```

If a pipeline does not overwrite the `file_changed_during_watch` method then it is considered not to support 
watch mode and the user will see a warning when using watch mode.


### Multiple processes for each source file

If you want to set up a situation where every source file can go through more than one process you will want to 
use the special process pipeline. Pass this as a pipeline to the config and also pass instances of the processes for 
each file.


```python
from staticpipes.pipes.process import PipeProcess
from staticpipes.processes.version import ProcessVersion
from staticpipes.processes.javascript_minifier import ProcessJavascriptMinifier

config = Config(
    pipes=[
        PipeProcess(extensions=["js"], processors=[ProcessJavascriptMinifier(), ProcessVersion()]),
    ],
)
```

Again, processes are class instances and the same class instance is used all the time. They should extend the 
`staticpipes.pipes.process.BaseProcessor` class. When that pipeline is called, the `process_file` method is called 
for every file. The `process_current_info` parameter has directory, filename and contents attributes and these should 
be changed as needed. 

At the end of calling all the processes, the file will be written to the site. 
During the prepare stage, `process_file` is called but the results are not written to the build site.

This has the limitation that one source file must produce exactly one destination file.

### Misc

Generally, the pipeline API is designed to be as easy to write pipelines for as possible while maintaining flexibility 
and power. Extend the base classes and overwrite as little or as many methods as you need.

## More information and feedback

* https://github.com/StaticPipes/StaticPipes



