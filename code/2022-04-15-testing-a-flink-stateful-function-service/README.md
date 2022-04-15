# Supplements for the blog post "Machine Learning Models Light as a Feather with ONNX"

Explanations can be found [in the blog post](https://blog.krudewig-online.de/2022/04/15/Machine-Learning-Models-Light-as-a-Feather.html).


## About the greeter example

Example stateful function pipeline in the `/greeter` folder is taken from https://github.com/apache/flink-statefun-playground/tree/release-3.2/go/greeter.

It can be build and run from the folder with:

```shell
docker build -t greeter-function .
docker run --rm -it -p 8000:8000 greeter-function
```

## About the Python environment for the test code

The Python environment was created with [pyenv](https://github.com/pyenv/pyenv), [virtualenv](https://virtualenv.pypa.io/en/latest/) and [piptools](https://github.com/jazzband/pip-tools).

To use it run:
```shell
# Install the Python interpreter itself:
pyenv install 3.10.3
# Set the Python interpreter as default for the folder:
pyenv local 3.10.3
# Create a virtual environment:
pyenv exec python -m venv .venv/pyenv
# Install the dependencies:
./.venv/bin/pip install -r requirements.txt 
# Activate the environment:
source ./.venv/bin/activate
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
./.venv/bin/pip install pip-tools
# Freeze the dependencies:
./.venv/bin/pip-compile --output-file requirements.txt requirements.in
# Install the dependencies:
./.venv/bin/pip install -r requirements.txt 
```