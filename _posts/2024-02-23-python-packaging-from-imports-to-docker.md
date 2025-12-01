---
layout: post
title: Python packaging unboxed
description: A practical guide to understanding Python's import system and packaging tools.
---
<script src="/assets/js/mermaid/11.12.0/mermaid.min.js" integrity="sha512-5TKaYvhenABhlGIKSxAWLFJBZCSQw7HTV7aL1dJcBokM/+3PNtfgJFlv8E6Us/B1VMlQ4u8sPzjudL9TEQ06ww==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
<script>mermaid.initialize({startOnLoad:true, theme:"neutral"});</script>

**Python packaging has a reputation for being confusing. With tools like setuptools, pip, poetry, flit, pdm, and twine, it's easy to get lost. This post demystifies the packaging workflow from the import system to Docker deployments.**

*All complete code examples referenced in this post can be found in [my python-packaging repository](https://github.com/chr1st1ank/python-packaging).*


{% include toc.md %}

## The structure of installed Python packages

Before diving into packaging, it's worth understanding what happens when you `import` a module. Python supports different types of modules.

**Built-in modules** are linked directly to the interpreter:

```pycon
>>> import sys
>>> sys
<module 'sys' (built-in)>
```

**Standard library modules** come with Python itself:

```pycon
>>> import os
>>> os
<module 'os' from '/usr/lib/python3.10/os.py'>
```

**Site-packages** are third-party modules installed with pip. And you can see that they live in a directory called `site-packages`:

```pycon
>>> import pytoml
>>> pytoml
<module 'pytoml' from '/home/user/env/lib/python3.10/site-packages/pytoml/__init__.py'>
```

When you import a module, Python's import system searches through specific locations defined in `sys.path`. This list typically includes the current directory, the standard library location, and crucially, the `site-packages` directory where pip installs packages.

```pycon
>>> import sys
>>> sys.path
['', '/home/user/env/lib/python310.zip', '/home/user/env/lib/python3.10', '/home/user/env/lib/python3.10/lib-dynload', '/home/user/env/lib/python3.10/site-packages']
```

An installed Python package consists of three main components:

1. **Entry points** in `bin/` or `scripts/` - executable commands like `pip`, `pytest`
2. **Modules** in `site-packages/` - the actual Python code you import
3. **Metadata** in `*.dist-info/` directories - package information, dependencies, and version details

For example, after installing a package with pip, you'll find its modules in `site-packages/package_name/` and metadata in `site-packages/package_name-1.0.0.dist-info/`.

A special case are **editable installs**.
They are normally created when developing, with `pip install -e .`.
Instead of copying files, it creates a `.pth` file in `site-packages/` that points to your source directory.
It is a simple text file with the target path that is understood as a link by Python's import system.
This means changes to your code are immediately available without reinstalling. 
Entry points are still created normally in the `bin/` directory, making the CLI commands work as expected.

## The package distribution workflow

Distributing a Python package follows a standardized four-step process:

<div class="mermaid">
%%{init: {"flowchart": {"defaultRenderer": "elk"}} }%%
graph LR

dev[Developer<br>sources] --**build**--> Package --**upload**--> pypi[(Package<br>Index)]
pypi --**discover &<br>download**--> p2[Package] --> iswheel{is wheel?}
iswheel --**yes**--> wheel[wheel] --**Install**-->t[Target<br>environment]
iswheel --"**no? Build!**"--> wheel

classDef default fill:#ddd,stroke:#ddd,stroke-width:0px;
classDef artifact fill:#FCBF49,stroke-width:0px;
classDef env fill:#003049,color:#fff;
class dev,t,pypi env;
class p2,Package,wheel artifact;
</div>

1. **Build** - Create source distributions (sdist) or wheels from your project
2. **Upload** - Push the built packages to PyPI or a private index
3. **Download** - Fetch packages from the index
4. **Install** - Extract and place files in the appropriate locations

Each step of this workflow can be handled by different tools, but they all produce the same standardized output.
This hasn't always been the case.
Python packaging has evolved significantly over the past two decades:

- **2000** - distutils and setup.py introduced
- **2004** - setuptools became the de-facto standard
- **2014** - Wheels standardized (PEP 427) - prebuilt distributions
- **2016** - pyproject.toml introduced (PEP 518) - declarative configuration
- **2017** - Build backends without setup.py (PEP 517) - separation of frontend and backend
- **2018+** - Modern all-in-one tools: poetry, pdm, rye, uv

The modern tooling landscape can be visualized like this:

<img src="/assets/images/python-packaging-venn-diagram.png" alt="Python packaging tools venn diagram" style="width:80%;"/>

*Source: [https://alpopkes.com/posts/python/packaging_tools/](https://alpopkes.com/posts/python/packaging_tools/)*

The key insight is the **separation between frontend and backend**:
- A **frontend** (like `pip` or `poetry`) installs build dependencies and orchestrates the build
- A **backend** (like `setuptools`, `flit`, or `poetry-core`) actually builds the package

This separation means you can use different combinations of tools while producing identical outputs.
The modern high-level tools like `poetry` are frontends that use other tools as a backend.

## Building and publishing packages

Now let's see how to build and publish a package.

**Building** a package is straightforward, because the `build` package takes care of invoking the right build backend. This creates both a source distribution and a wheel:

```console
❯ python -m build
* Creating virtualenv isolated environment...
* Installing packages in isolated environment... (poetry-core>=1.0.0)
* Getting build dependencies for sdist...
* Building sdist...
* Building wheel from sdist
Successfully built langc-0.1.0.tar.gz and langc-0.1.0-py3-none-any.whl
```

**Uploading** to PyPI needs another tool, namely `twine`:

```console
❯ twine upload --repository-url https://test.pypi.org/legacy/ dist/*
Uploading distributions to https://test.pypi.org/legacy/
Uploading langc-0.1.0-py3-none-any.whl
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 447.8/447.8 kB • 00:00 • 3.5 MB/s
```

**Downloading and installing** is what users do to get your package. From a package index:

```console
❯ pip install --index-url https://test.pypi.org/simple langc
Looking in indexes: https://test.pypi.org/simple
Collecting langc
  Downloading https://test-files.pythonhosted.org/packages/e7/4c/
  ...
```

Or directly from a wheel file:

```console
❯ pip install /home/christian/code/python-packaging/poetry/dist/langc-0.1.0-py3-none-any.whl
...
```

## Testing and deploying packages

### Testing the package

A common pitfall is testing your code directly from the source tree. This can miss issues like:

- Missing files that weren't included in the package
- Build dependencies leaking into your tests
- Import problems that only appear in the installed package

Instead, test the actual built package:

```shell
# Build the wheel
python -m build --wheel

# In a clean environment, install with test dependencies
pip install dist/*.whl[test]

# Copy test code and run tests
cp -r tests ./
pytest
```

This ensures you're testing exactly what users will install.

### Deploying with Docker

For deploying Python applications in Docker, there are two common approaches.

The **traditional approach**, where you copy the source code into the container and separately install dependencies:

```dockerfile
FROM python:3.9-slim-bookworm

COPY ./requirements.txt ./
RUN pip install -r requirements.txt --no-cache-dir

ENV PYTHONPATH "${PYTHONPATH}:/workspace"    # Needed for imports!

COPY ./mypackage ./mypackage                 # Don't forget files
COPY ./api ./api                             
COPY ./config ./config                       
COPY ./entrypoint.py ./entrypoint.py         

CMD ["python", "entrypoint.py"]
```

This works but has issues:
- PYTHONPATH manipulation required
- Easy to forget files
- Binary extensions need special handling
- Entry points aren't properly set up

The **wheel-based approach**, which relies on a real Python package, built as a wheel:

```dockerfile
FROM python:3.9-slim-bookworm

COPY ./dist/*.whl ./
RUN pip install *.whl

CMD ["myapi"]                                # Entry points just work!
```

This is cleaner because:
- No PYTHONPATH manipulation needed
- Binary extensions (Cython, PyO3) are handled correctly
- Resources are properly included
- Entry points work out of the box
- The package can be tested independently of Docker

The wheel-based approach adds one build step before Docker, but it creates a fully standardized workflow that's easier to test and maintain.

## Summary

Python packaging is simpler and more standardized than it appears:

1. **The import system** uses `sys.path` to locate modules in `site-packages/`
2. **The distribution workflow** follows a standard four-step process
3. **Modern tools** separate frontend and backend concerns
4. **Testing the package** (not directly the source tree) catches more issues
5. **Combining Python and Docker builds** yields a robust deployment workflow

The key is understanding that beneath the various tools lies a well-designed, standardized system. Whether you use pip, poetry, flit, or uv, they all work with the same underlying standards and produce compatible outputs.

For more details and complete working examples, check out my [python-packaging repository](https://github.com/chr1st1ank/python-packaging).

## Recommended reading
- [Packaging tools overview by Anna-Lena Popkes](https://alpopkes.com/posts/python/packaging_tools/)
- [Python packaging demystified by Bernát Gábor](https://bernat.tech/presentations/#py-packaging-us-21)
- [PyPA Packaging History](https://www.pypa.io/en/latest/history/)
