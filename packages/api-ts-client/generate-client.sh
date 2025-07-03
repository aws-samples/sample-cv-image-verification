# This script generates a TypeScript client from an OpenAPI specification.
# 
# Steps:
# 1. Fetch the OpenAPI specification from a local server and save it as openapi.json.
# 2. Set the Docker default platform to linux/arm64.
# 3. Remove the existing src directory.
# 4. Run the OpenAPI Generator Docker container to generate the TypeScript client code.
#    - Mount the current directory to /local in the container.
#    - Use the openapi.json file as the input specification.
#    - Generate the client code using the typescript-fetch generator.
#     - Output the generated code to the src directory.
#    - Set additional properties for the generator, such as enum property naming to UPPERCASE.
# 5. Build the generated client code using npm.

#!/bin/sh

set -e

curl -o openapi.json http://localhost:8000/openapi.json

rm -rf ../api/api_client

mkdir -p ../api/api_client

cp openapi.json ../api/api_client/openapi.json

export DOCKER_DEFAULT_PLATFORM=linux/arm64

rm -rf ./src

rm -rf ./docs

docker run --rm -v "${PWD}:/local" openapitools/openapi-generator-cli generate \
    -i /local/openapi.json \
    -g typescript-fetch \
    -o /local/src

npm run build