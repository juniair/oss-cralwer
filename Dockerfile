FROM python:3.7
ADD requirements.txt /app/requirements.txt
ADD ./crawler/ /app/
ADD ./data/ /HDD2/alice_proejct/alice_crawler/data
WORKDIR /app/
RUN pip install --trusted-host pypi.python.org -r requirements.txt
# ENTRYPOINT celery -A crawler worker --concurrency=2 --loglevel=debug