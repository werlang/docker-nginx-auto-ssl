#!/usr/bin/env python

import os
import shutil
import subprocess

RESTY_CONF_DIR = "/usr/local/openresty/nginx/conf"
NGINX_CONF_DIR = "/etc/nginx/conf.d"

# openresty will change it later on his own, right now we're just giving it access
os.chmod("/etc/resty-auto-ssl", 0o777)

# Check if dhparam.pem file exists in the volume, generate if it doesn't
dhparam_path = "/etc/resty-auto-ssl/dhparam.pem"
if not os.path.isfile(dhparam_path):
    if os.environ.get("DIFFIE_HELLMAN"):
        subprocess.call(["openssl", "dhparam", "-out", dhparam_path, "2048"])
    else:
        shutil.copyfile(os.path.join(RESTY_CONF_DIR, "dhparam.pem"), dhparam_path)

# Prepare configuration files for each site specified
sites = os.environ.get("SITES")
if sites:
    # Check if the sites variable contains semicolons or new lines
    if ";" in sites:
        sites_separated = sites.split(";")
    else:
        # Handle multi-line input
        sites_separated = [line.strip() for line in sites.strip().splitlines() if line.strip()]

    for name_eq_endpoint in sites_separated:
        server_name, server_endpoint = name_eq_endpoint.split("=")[0], name_eq_endpoint.split("=")[1]
        raw_server_endpoint = server_endpoint.split("//")[-1]
        os.environ["SERVER_NAME"] = server_name
        os.environ["SERVER_ENDPOINT"] = raw_server_endpoint

        with open(os.path.join(RESTY_CONF_DIR, "server-proxy.conf"), "r") as template_file:
            template = template_file.read()

        config = template.replace("$SERVER_NAME", server_name).replace("$SERVER_ENDPOINT", raw_server_endpoint)

        with open(os.path.join(NGINX_CONF_DIR, f"{server_name}.conf"), "w") as conf_file:
            conf_file.write(config)

# If no sites are specified, check if the Nginx configuration directory is empty and copy the default server configuration
elif not os.listdir(NGINX_CONF_DIR):
    shutil.copyfile(os.path.join(RESTY_CONF_DIR, "server-default.conf"), os.path.join(NGINX_CONF_DIR, "default.conf"))

# Add "include force-https.conf;" directive to the OpenResty HTTP server configuration file if FORCE_HTTPS is set to "true"
if os.environ.get("FORCE_HTTPS") == "true":
    resty_http_conf = os.path.join(RESTY_CONF_DIR, "resty-server-http.conf")
    if "force-https.conf" not in open(resty_http_conf).read():
        with open(resty_http_conf, "a") as conf_file:
            conf_file.write("include force-https.conf;\n")

# Substitute environment variables in the OpenResty HTTP server configuration file
allowed_domains = os.environ.get("ALLOWED_DOMAINS", "")
letsencrypt_url = os.environ.get("LETSENCRYPT_URL", "")
resolver_address = os.environ.get("RESOLVER_ADDRESS", "")
storage_adapter = os.environ.get("STORAGE_ADAPTER", "")
redis_host = os.environ.get("REDIS_HOST", "")
redis_port = os.environ.get("REDIS_PORT", "")
redis_db = os.environ.get("REDIS_DB", "")
redis_key_prefix = os.environ.get("REDIS_KEY_PREFIX", "")

with open(os.path.join(RESTY_CONF_DIR, "resty-http.conf"), "r") as template_file:
    template = template_file.read()

config = template.replace("$ALLOWED_DOMAINS", allowed_domains).replace("$LETSENCRYPT_URL", letsencrypt_url).replace(
    "$RESOLVER_ADDRESS", resolver_address).replace("$STORAGE_ADAPTER", storage_adapter).replace("$REDIS_HOST", redis_host).replace(
    "$REDIS_PORT", redis_port).replace("$REDIS_DB", redis_db).replace("$REDIS_KEY_PREFIX", redis_key_prefix)

with open(os.path.join(RESTY_CONF_DIR, "resty-http.conf"), "w") as conf_file:
    conf_file.write(config)

# Execute the command specified in the '@' environment variable if provided.
command = os.environ.get("@")
if command:
    command_list = command.split()
    try:
        subprocess.run(command_list)  # Wait for the command to complete
    except Exception as e:
        print(f"Failed to start command '{command}': {e}")
        sys.exit(1)

# Now, execute OpenResty.
command_list = ["/usr/local/openresty/bin/openresty", "-g", "daemon off;"]
try:
    subprocess.run(command_list)  # Run OpenResty and wait for it to complete
except Exception as e:
    print(f"Failed to start OpenResty: {e}")
    sys.exit(1)