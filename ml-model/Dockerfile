FROM public.ecr.aws/lambda/python:3.10
RUN pip install numpy scikit-learn joblib threadpoolctl
COPY app.py ${LAMBDA_TASK_ROOT}
COPY model.joblib ${LAMBDA_TASK_ROOT}
CMD ["app.lambda_handler"]
