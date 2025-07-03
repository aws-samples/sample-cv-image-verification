FROM public.ecr.aws/lambda/python:3.12

WORKDIR /app

COPY ./requirements.txt ./
RUN python3 -m pip install -r requirements.txt --no-cache-dir 

RUN mkdir -p /tmp/model_cache

COPY . ${LAMBDA_TASK_ROOT}

CMD [ "verification_job_processor.handler" ]