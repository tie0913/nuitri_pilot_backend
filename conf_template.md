
# Description
This is the demo configuration for the whole backend server configuration.
If you would like to configure your application locally, you may create a config file in the root directory of this project and name it .env 

The content of this .env file should contain item below

#Port Configuration
PORT= 7001
#Email Sender Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_PASSWORD="jeic myvu opql afef"
SMTP_FROM="nuitripilot@gmail.com"
#Logger Configuration
LOG_LEVEL="INFO"

#JWT TOKEN
JWT__SECRET=super-secret-dev-key
JWT__ALGORITHM=HS256
JWT__ACCESS_TOKEN_EXPIRE_MINUTES=300