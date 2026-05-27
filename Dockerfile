FROM postgres:15-alpine

# Install build tools (LLVM 19 matches what postgres:15-alpine was compiled with)
RUN apk add --no-cache \
    git \
    build-base \
    clang19 \
    llvm19-dev

# Build and install pgvector from source
RUN cd /tmp \
    && git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git \
    && cd pgvector \
    && make \
    && make install \
    && cd /tmp \
    && rm -rf pgvector
