FROM python:3.11-alpine

WORKDIR /app

COPY Pipfile Pipfile.lock ./

RUN pip install pipenv && \
	pipenv install --deploy --system && \
	pip uninstall pipenv -y

COPY hestia ./hestia

CMD ["python", "-m", "hestia.main"]
