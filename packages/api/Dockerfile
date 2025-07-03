FROM public.ecr.aws/lambda/python:3.12

# Copy requirements and install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code
COPY . ${LAMBDA_TASK_ROOT}

# Set the handler
CMD [ "main.handler" ]
