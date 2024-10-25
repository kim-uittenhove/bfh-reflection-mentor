# Required for JWT authentication
import jwt
from dotmap import DotMap
import asyncio
from typing import Optional
from starlette.requests import Request
import chainlit as cl
import os
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("Post auth included")

# Load environment variables from .env file
load_dotenv()

# Parse moodle payload.
def parse_payload_moodle(payload):
    adminRoleKey = 'http://purl.imsglobal.org/vocab/lis/v2/institution/person#Administrator'
    isAdmin = adminRoleKey in payload.platformContext.roles
    role = 'admin' if isAdmin else 'student'
    return cl.User(identifier=payload.user, metadata={
        "user": payload.user,
        "role": role,
        "provider": "header",
        "platform-id": payload.platformId,
        "courseid": payload.platformContext.context.id
    })

# Parse prolific payload.
def parse_payload_prolific(payload):
    logger.debug("Parsing prolific payload")
    return cl.User(identifier = f"{payload.studyId}~{payload.prolificId}", metadata={
        "user": payload.prolificId,
        "provider": "prolific",
        "studyId": payload.studyId,
        "exp": payload.exp,
        "returnUrl": "https://docs.google.com/document/d/e/2PACX-1vRvyIlu7bCIuXjXQ-v0vn9jzOqATCbINgz8FtsEpdRpgsOBUJqXw4EZyf22Z9heBReDzeKQsTkev7LS/pub"
    })

# Select parser based on the environment variable - defaults to moodle.
def get_payload_parser():
    parser_type = os.getenv('PAYLOAD_PARSER', 'moodle')

    # Log the parser being used
    logger.debug(f"Using {parser_type} parser")

    parsers = {
        'moodle': parse_payload_moodle,
        'prolific': parse_payload_prolific
    }
    return parsers.get(parser_type, parse_payload_moodle)

def post_auth_cb(request: Request) -> Optional[cl.User]:
    if not request:
        return None

    async def get_form():
        form = await request.form()
        return form

    async def get_json():
        json = await request.json()
        return json

    contentType = request.headers.get('Content-Type')

    if contentType == 'application/json':
        json = asyncio.run(get_json())
        result = json.get('formData')
    else:
        result = asyncio.run(get_form())

    if not result.get('token'):
        return None

    try:
        token = result.get('token')
        # Read rsa public key
        file = open('rs256.rsa.pub', mode='r')
        key = file.read()
        file.close()
        payload = jwt.decode(token, key, algorithms=["RS256"])
        payload = DotMap(payload)

        # Get the appropriate parser function
        parser = get_payload_parser()

        # Use the parser to process the payload
        return parser(payload)

    except:
        logger.error("JWT decode failed")
        return None
