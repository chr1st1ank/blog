# Supplements for the blog posts about Locating memory leaks in a Python service

Explanations can be found [in the blog post](https://blog.krudewig-online.de/2022/09/04/locating-memory-leaks-in-services-part1.html).

## Python example code
### Setting up the environment
The Python environment was created with [pyenv](https://github.com/pyenv/pyenv), [virtualenv](https://virtualenv.pypa.io/en/latest/) and [piptools](https://github.com/jazzband/pip-tools).

To use it run:
```shell
# Install the Python interpreter itself:
pyenv install 3.10.3
# Set the Python interpreter as default for the folder:
pyenv local 3.10.3
# Create a virtual environment:
pyenv exec python -m venv .venv/
# Activate the environment:
source ./.venv/bin/activate
# Install the dependencies:
python -m piptools sync requirements.txt
# Compile the cython extension
python setup.py build_ext --inplace
```

The initial setup was done with:
```shell
# Install the Python interpreter itself:
pyenv install 3.10.3
# Set the Python interpreter as default for the folder:
pyenv local 3.10.3
# Create a virtual environment:
pyenv exec python -m venv .venv/
# Install pip-tools:
python -m pip install --upgrade pip pip-tools
# Freeze the dependencies:
python -m piptools compile --output-file requirements.txt requirements.in
# Install the dependencies:
python -m pip install -r requirements.txt 
```

### Running
With the environment activated as described above the example webservice can be run with:
```bash
python api/api.py
```


