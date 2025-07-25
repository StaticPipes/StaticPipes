---
title: Internal Model
---

## Internal Model

This page describes the internal model of StaticPipes, and how pipes, processes, checks and more are called.

This is useful if you want to write your own procssing tools.

### Pipes

Instances of pipe classes are created and passed to the config. The same instance is used throughout. This means 
if a pipeline wants to store information early on to use later, it can do. Pipes classes should extend 
the `staticpipes.pipe_base.BasePipe` class.

### Build stage

During building, the `start_build` method is called on each pipeline. Methods are always called on each pipeline in the 
order the pipes are passed to the config.

Then, the `build_file` method is called on each pipeline for each file in the source directory. The order of files in 
the directory is not set and should not be relied on.

The `end_build` method is called on each pipeline.

A pipeline should deal with the file completely or not at all. Either it ignores it or it does something that ends 
with a method on `self.build_directory` being called to write some content to the site. 

A pipeline can write zero to many files to the site for a single source file. For instance, a image processing 
pipeline could write multiple files at different resolutions for every image in the source.

A `current_info` object is passed to all methods. This contains information and can be used to set information.

A pipeline can mark a file as excluded (by setting `current_info.current_file_excluded`), which means that later 
pipes won't have `build_file` called for that file. However, they will have `file_excluded_during_build` called for 
each excluded file.

A context is maintained on `current_info` via `get_context`, `set_context` and other methods. This is a dictionary of 
values that is initially set in the configuration object but pipes can read and modify. For example, an earlier 
pipeline might version a CSS file at a particular location and store the location in the context. A later pipeline 
might build Jinja2 templates with the context as temple variables so the html can actually load the CSS.

### Prepare stage

Before the build stage is started a prepare stage is done. `start_prepare` is called on each pipeline, then 
`prepare_file` for each file, then `end_prepare`. This can be used to collect  info before building. For example, 
see the `PipeCopyWithVersioning` pipeline that works out the filename for any file it will work with in the prepare 
stage. This ensures information about the new file name is already in the context before a single build method is 
called.

It's not possible to exclude any files during the prepare stage.

### Checks

After building, checks are called on the built website. These can check the site, and raise reports with any issues 
they find. A check should extend the base class `staticpipes.check_base.BaseCheck`. On each check the methods 
`start_check`, `check_file`, `end_check` are called. These methods should return a list of instances of the 
class `staticpipes.check_report.CheckReport` with details of any problems found.

### Watch mode

In watch mode, a normal build is done first. The `start_watch` method is then called on each pipeline. Then every time 
a file is changed, the `file_changed_during_watch` or `file_changed_but_excluded_during_watch` method is called for 
that file. The history of the context is tracked, and if the history changes the `context_changed_during_watch` method 
is called. There is no `end_watch` method, as the watch stage is ended by the user forcibly quitting the program.

Writing pipes for watch mode can be more complicated than writing pipes for build mode. This is due to the 
idea of dependencies. If the process of building source file A depends in some way on building source file B, 
when source file B changes then both files A and B must be rebuilt. 

Dependencies are left up to each pipeline to handle. Generally the pipeline should build up dependency information 
during the prepare or build stage and cache it for use during the watch stage. During prepare and build stage a flag 
`current_info.watch` is set if watch will be called afterwards. This means pipes can avoid doing any extra work 
tracking dependencies for the watch stage if it isn't going to be called.

If a pipeline has no possible interactions with dependencies it can usually use the same code for building. 
Just add this to the pipeline:

```python
    def file_changed_during_watch(self, dir, filename, current_info):
        self.build_file(dir, filename, current_info)
```

If a pipeline does not overwrite the `file_changed_during_watch` method then it is considered not to support 
watch mode and the user will see a warning when using watch mode.

Currently checks are only done after the first build and are not rerun when the built site changes.

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
`staticpipes.process_base.BaseProcessor` class. When that pipeline is called, the `process_file` method is called 
for every file. The `process_current_info` parameter has directory, filename and contents attributes and these should 
be changed as needed. 

At the end of calling all the processes, the file will be written to the site. 
During the prepare stage, `process_file` is called but the results are not written to the build site.

This has the limitation that one source file must produce exactly one destination file.

### Misc

Generally, the API is designed to be as easy to write pipes, processes and checks for as possible while maintaining 
flexibility and power. Extend the base classes and overwrite as little or as many methods as you need.
