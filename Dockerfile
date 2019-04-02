FROM ubuntu:latest

ENV DB_TYPE            ""
ENV DB_HOST            ""
ENV DB_PORT            "3306"
ENV DB_PASSWORD        ""
ENV DB_USERNAME        ""
ENV REVISION_DB_NAME   "revision"
ENV HISTORY_TABLE_NAME ""
ENV STATIC_ALTER_DIR   "DBA_FILES/"
ENV PRE_COMMIT_HOOK    ""

RUN apt-get update && \
    apt-get install -y \
        python \
	gettext \
	wait-for-it \
        mysql-client

WORKDIR /schema-tool
COPY . .

WORKDIR /schemas
ENTRYPOINT ["/schema-tool/entrypoint.sh"]
CMD ["--help"]
