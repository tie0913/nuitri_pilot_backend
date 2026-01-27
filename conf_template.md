
# Description
This is the demo configuration for the whole backend server configuration.
If you would like to configure your application locally, you may create a config file in the root directory of this project and name it .env 

The content of this .env file should contain item below

# Port Configuration
PORT= 7001
# Email Sender Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_PASSWORD="jeic myvu opql afef"
SMTP_FROM="nuitripilot@gmail.com"
# Logger Configuration
LOG_LEVEL="INFO"

# JWT TOKEN
JWT__SECRET=super-secret-dev-key
JWT__ALGORITHM=HS256
JWT__ACCESS_TOKEN_EXPIRE_MINUTES=300

# MongoDB Connection Configuration
MONGO_URL=""
MONGO_PORT=
MONGO_USER=""
MONGO_PWD=""
MONGO_SCHEMA_NAME=""
MONGO_MAX_POOL_SIZE=5
MONGO_MIN_POOL_SIZE=1
MONGO_DIRECT_CONNECTION=true
MONGO_DEFAILT_REPLICA_SET_NAME=

# OPENAI PARAM
OPEN_AI_MODEL="gpt-4o-mini"
OPEN_AI_API_KEY=