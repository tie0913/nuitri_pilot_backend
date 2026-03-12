
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
OPEN_AI_TIMEOUT_S=15
OPEN_AI_MAX_RETRIES=0
OPEN_AI_TOTAL_TIMEOUT_S=50

# Optional AI client overrides
AI_MODEL="gpt-4o-mini"
AI_TIMEOUT_SECONDS=30
AI_TEMPERATURE=0

# AI audit policy
# 1 = fail-closed for code=1 outputs, 0 = do not auto-fail code=1 in audit
AI_AUDIT_FAIL_CODE1=1
# 1 = require grounded feedback terms, 0 = disable grounded-feedback check
AI_AUDIT_REQUIRE_GROUNDED_FEEDBACK=1
# minimum feedback words for successful (code=0) outputs
AI_AUDIT_MIN_FEEDBACK_WORDS=20
