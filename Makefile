# Adapted from various Makefiles from projects under
# https://github.com/masschallenge.
# All aspects that are copyrighted by MassChallenge or Nathan Wilson
# are available under the MIT License.


help:
	@echo Valid targets are:
	@echo help - Prints this help message
	@echo code-check - Runs pycodestyle on all python code in the project
	@echo coverage - Use pytest to run all tests and report on test coverage
	@echo test - Use pytest to run all tests. Use tests to run subset.
	@echo E.g., make test tests=test_create


VENV = venv
MODULE_NAME = mat

ifeq ($(OS),Windows_NT)
  CP = copy
  GIT_HOOKS_TARGET = .git\hooks\pre-commit
  GIT_HOOKS_SOURCE = git-hooks\pre-commit
  PYTHON = python
  ACTIVATE = $(VENV)\Scripts\activate && set PYTHONPATH=.
  RMDIR_CMD := rmdir /s /q
  virtualenv = $(shell where virtualenv.exe)
  PROJECT_PYFILES = \
    mat/accelerometer_factory.py \
    mat/appdata.py \
    mat/ascii85.py \
    mat/calibration_factories.py \
    mat/calibration.py \
    mat/converter.py \
    mat/cubic_accelerometer.py \
    mat/cubic_magnetometer.py \
    mat/data_file_registry.py \
    mat/gps.py \
    mat/header.py \
    mat/__init__.py \
    mat/lid_data_file.py \
    mat/light.py \
    mat/linear_accelerometer.py \
    mat/lis_data_file.py \
    mat/logger_cmd.py \
    mat/logger_controller.py \
    mat/logger_info_parser.py \
    mat/magnetometer_factory.py \
    mat/meter.py \
    mat/odlfile.py \
    mat/pressure.py \
    mat/sensor_data_file.py \
    mat/sensor_filter.py \
    mat/sensor_parser.py \
    mat/sensor.py \
    mat/temp_compensated_magnetometer.py \
    mat/temperature.py \
    mat/tiltcurve.py \
    mat/time_sequence.py \
    mat/utils.py \
    mat/v2_calibration.py \
    mat/v3_calibration.py \
    setup.py \
    tests/test_calibration.py \
    tests/test_compare_data_files.py \
    tests/test_converter.py \
    tests/test_data_converter.py \
    tests/test_gps.py \
    tests/test_header.py \
    tests/test_logger_controller.py \
    tests/test_sensor_data_file.py \
    tests/utils.py \

else
  CP = cp
  GIT_HOOKS_TARGET = .git/hooks/pre-commit
  GIT_HOOKS_SOURCE = git-hooks/pre-commit
  PYTHON = python3
  VENV_PYTHON = -p $(PYTHON)
  ACTIVATE = export PYTHONPATH=.; . $(VENV)/bin/activate
  RMDIR_CMD = rm -rf
  virtualenv = $(shell which virtualenv)
  PROJECT_PYFILES = *.py */*.py
endif


$(GIT_HOOKS_TARGET): $(GIT_HOOKS_SOURCE)
	@$(CP) $(GIT_HOOKS_SOURCE) $(GIT_HOOKS_TARGET)


ifeq ($(virtualenv),)
  NEED_VIRTUALENV = virtualenv
endif

virtualenv:
	@pip install virtualenv


$(VENV): $(NEED_VIRTUALENV) requirements.txt $(GIT_HOOKS_TARGET)
	@-$(RMDIR_CMD) $(VENV)
	@virtualenv $(VENV_PYTHON) $@
	@$(ACTIVATE) && pip install -r requirements.txt


code-check: $(VENV)
	@$(ACTIVATE) && flake8 $(PROJECT_PYFILES)


ifneq ($(tests),)
  TESTS = -k $(tests)
endif

test: $(VENV)
	@$(ACTIVATE) && pytest $(TESTS)


coverage: $(VENV)
	@$(ACTIVATE) && pytest --cov=$(MODULE_NAME) \
		--cov-report=term --cov-report=html $(TESTS)
