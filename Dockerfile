FROM python:3.11

WORKDIR /usr/app
COPY ./app /usr/app
COPY ./.env /usr/app

# Install everything required for chainlit custom build (with post authentication).
RUN curl -L https://deb.nodesource.com/nsolid_setup_deb.sh | bash -s -- 18
RUN apt-get update && apt-get install nodejs -y
RUN node --version
RUN if [ -z "$(command -v npm)" ]; then \
    curl -L https://www.npmjs.com/install.sh | sh; \
    fi \
    && npm --version
RUN npm install -g pnpm
RUN git clone --branch prolific_variant --depth 1 https://github.com/virtuelleakademie/chainlit.git
RUN mkdir -p chainlit/frontend/dist && mkdir -p chainlit/libs/copilot/dist
RUN cd chainlit/backend && pip install -e .
RUN cd chainlit/frontend && pnpm install --no-frozen-lockfile && pnpm run build
# End install everything required for chainlit custom build (with post authentication)

RUN mkdir -p /var/log/lancedb
RUN pip install -r requirements.txt
RUN chainlit init
# Add customized chainlit stuff into the .chainlit folder.
COPY ./app/.chainlit /usr/app/.chainlit
RUN chmod 755 /usr/app/.chainlit/config.toml

ENTRYPOINT ["chainlit", "run", "app.py", "--host=0.0.0.0", "--port=80", "--headless"]
