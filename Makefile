# Makefile for owlkit development

.PHONY: help install install-dev test test-unit test-integration test-coverage lint format clean build

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install owlkit package
	pip install -e .

install-dev:  ## Install development dependencies
	pip install -e ".[dev]"
	pip install pytest pytest-cov pytest-mock black isort mypy flake8

test:  ## Run all tests
	pytest

test-unit:  ## Run unit tests only
	pytest -m "not integration"

test-integration:  ## Run integration tests only
	pytest -m integration

test-coverage:  ## Run tests with coverage report
	pytest --cov=owlkit --cov-report=html --cov-report=term

test-watch:  ## Run tests in watch mode
	pytest -f

lint:  ## Run linting checks
	flake8 owlkit tests
	mypy owlkit
	black --check owlkit tests
	isort --check-only owlkit tests

format:  ## Format code
	black owlkit tests
	isort owlkit tests

clean:  ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build:  ## Build package
	python setup.py sdist bdist_wheel

install-deps:  ## Install all dependencies for testing
	pip install sbpack
	pip install cwltool

test-quick:  ## Run quick subset of tests
	pytest tests/test_credentials.py tests/test_cli.py -v

test-docker:  ## Run Docker-related tests
	pytest -m docker -v

test-sbpack:  ## Run sbpack-related tests  
	pytest tests/test_sbpack.py -v

test-cwl:  ## Run CWL-related tests
	pytest tests/test_cwl.py -v

check:  ## Run all checks (lint + test)
	make lint
	make test

ci:  ## Run CI pipeline locally
	make install-dev
	make lint
	make test-coverage