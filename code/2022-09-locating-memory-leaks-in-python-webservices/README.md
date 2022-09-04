# Supplements for the blog post "Machine Learning Models Light as a Feather with ONNX"

Explanations can be found [in the blog post](https://blog.krudewig-online.de/2022/04/15/Machine-Learning-Models-Light-as-a-Feather.html).


## Monitoring stack
The minimal monitoring stack in the `/monitoring` folder collects and displays metrics about local Python processes.
It can be run from the folder with:

```shell
docker-compose up -d
```

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
# Install the dependencies:
./.venv/bin/pip install -r requirements.txt 
# Activate the environment:
source ./.venv/bin/activate
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
./.venv/bin/pip install pip-tools
# Freeze the dependencies:
./.venv/bin/pip-compile --output-file requirements.txt requirements.in
# Install the dependencies:
./.venv/bin/pip install -r requirements.txt 
```

### Running
With the environment activated as described above the example webservice can be run with:
```bash
python api/api.py
```


