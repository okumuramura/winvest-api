set CODE=winvest

flake8 --jobs 4 --statistics --show-source %CODE%
pylint --rcfile=setup.cfg %CODE%
mypy %CODE%
black --line-length=80 --target-version py39 --skip-string-normalization --check %CODE%
