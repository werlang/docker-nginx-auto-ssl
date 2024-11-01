# About this fork
This repo was forked from [valian/docker-nginx-auto-ssl](https://github.com/valian/docker-nginx-auto-ssl). I have made the following enhancements:

- **Entry Point Change:** The original `entrypoint.sh` has been replaced with `entrypoint.py`, a Python script that performs the same functionality. This change was made because I am more comfortable using Python for modifications and enhancements.
- **Multiline Environment Variable Support:** The `SITES` environment variable can now be specified as a multiline string, which is particularly useful for managing multiple sites to proxy. Please see the format in the example below.
- **Multi-Architecture Support:** The Docker image has been rebuilt to support both x86 and ARM architectures. The updated image can be found on [Docker Hub](https://hub.docker.com/r/pswerlang/nginx-auto-ssl).


# docker-nginx-auto-ssl
*The simpliest solution to add SSL cert to your site*

![build](https://img.shields.io/docker/cloud/build/valian/docker-nginx-auto-ssl.svg)
![build](https://img.shields.io/docker/pulls/valian/docker-nginx-auto-ssl.svg)

Docker image for automatic generation of SSL certs using Let's encrypt and Open Resty, with reasonable SSL settings, HTTP/2 and WebSockets support out-of-the-box.
You can specify allowed domains and simple proxies using ENV variables, and easily override `nginx.conf` to your needs. 

This is possible thanks to [OpenResty](https://github.com/openresty/openresty) and [lua-resty-auto-ssl](https://github.com/GUI/lua-resty-auto-ssl).

**Image status**: used in production. Some backward-compatible changes may be added in the future.

# Usage

## Quick start

To generate and automatically renew certificates for your application, use the following commands:

```Bash
# replace these values
export DOMAIN=yourdomain.com
export APP_ADDRESS=localhost:8080

# install docker first, and then run following command
docker run -d \
  --name nginx-auto-ssl \
  --restart on-failure \
  --network host \
  -e ALLOWED_DOMAINS="$DOMAIN" \
  -e SITES="$DOMAIN=$APP_ADDRESS" \
  -v ssl-data:/etc/resty-auto-ssl \
  pswerlang/nginx-auto-ssl

# display logs from container, to check if everything is fine.
docker logs nginx-auto-ssl
```

[Docker-compose](https://docs.docker.com/compose/) example:

```yaml
# compose.yaml
services:
  nginx:
    image: pswerlang/nginx-auto-ssl
    restart: on-failure
    ports:
      - 80:80
      - 443:443
    volumes:
      - ssl_data:/etc/resty-auto-ssl
    environment:
      ALLOWED_DOMAINS: 'yourdomain.com'
      SITES: 'yourdomain.com=myapp:80'
  
  # your application, listening on port specified in `SITES` env variable
  myapp:
    image: nginx

volumes:
  ssl_data:
```

start using
```Bash
docker-compose up -d
```

Both cases will work when request to `yourdomain.com` will reach just-deployed nginx (so when it will be running on your server, with correctly defined DNS entry).

Available configuration options: 

 | Variable | Example | Description
 | --- | --- | ---|
 | ALLOWED_DOMAINS | `(www\|api).example.com`, `example.com`, `([a-z]+.)?example.com` | Regex pattern of allowed domains. Internally, we're using [ngx.re.match](https://github.com/openresty/lua-nginx-module#ngxrematch). By default we accept all domains |
 | DIFFIE_HELLMAN | `true` | Force regeneration of `dhparam.pem`. If not specified, default one is used. |
 | SITES | `db.com=localhost:5432; *.app.com=localhost:8080`, `_=localhost:8080` | Shortcut for defining multiple proxies, in form of `domain1=endpoint1; domain2=endpoint2`. Default template for proxy is [here](https://github.com/Valian/docker-nginx-auto-ssl/blob/master/snippets/server-proxy.conf). Name `_` means default server, just like in nginx configuration |
 | FORCE_HTTPS | `true`, `false` | If `true`, automatically adds location to `resty-server-http.conf` redirecting traffic from http to https. `true` by default. |
 | LETSENCRYPT_URL | `https://acme-v02.api.letsencrypt.org/directory`, `https://acme-staging-v02.api.letsencrypt.org/directory` | Let's Encrypt server URL to use |
 | RESOLVER_ADDRESS | `8.8.8.8`, `127.0.0.53` | DNS resolver used for OCSP stapling. `8.8.8.8` by default. To disable ipv6 append `ipv6=off`, eg `8.8.8.8 ipv6=off` |
 | STORAGE_ADAPTER | `file`, `redis` | Location to store generated certificates. Best practice is `redis` in order to avoid I/O blocking in OpenResty and make the certs available across multiple containers (for a load balanced environment) . `file` by default |
 | REDIS_HOST | `hostname`, `ip address` | The redis host name to use for cert storage. Required if  `STORAGE_ADAPTER=redis`|
 | REDIS_PORT | `port number` | The redis port number. `6379` by default|
 | REDIS_DB | `db_number` | The Redis database number used by lua-resty-auto-ssl to save certificates. `0` by default |
 | REDIS_KEY_PREFIX | `some-prefix` | Prefix all keys stored in Redis with this string. `''` by default |

## Proxying Multiple Sites

If you want to proxy multiple sites, you can run:

```yaml
# compose.yaml
services:
  nginx:
    image: pswerlang/nginx-auto-ssl
    restart: on-failure
    ports:
      - 80:80
      - 443:443
    environment:
      ALLOWED_DOMAINS: 'example.com'
      SITES: |
        example.com=myapp:80
        api.example.com=api:80
        app.example.com=app:80
```

## Customization

### Includes from `/etc/nginx/conf.d/*.conf`

Additional server blocks are automatically loaded from `/etc/nginx/conf.d/*.conf`. If you want to provide your own configuration, you can either use volumes or create custom image.

Example server configuration (for example, named `server.conf`)

```nginx
server {
  listen 443 ssl default_server;
  
  # remember about this line!
  include resty-server-https.conf;

  location / {
    proxy_pass http://app;
  }
  
  location /api {
    proxy_pass http://api;
  }
}
```

Volumes method

```yaml
# compose.yaml
services:
  nginx:
    image: pswerlang/nginx-auto-ssl
    restart: on-failure
    ports:
      - 80:80
      - 443:443
    volumes:
      # instead of . use directory with your configurations
      - .:/etc/nginx/conf.d
```

Custom image way

```Dockerfile
FROM pswerlang/nginx-auto-ssl

# instead of . use directory with your configurations
COPY . /etc/nginx/conf.d
```

```Bash
docker build -t docker-nginx-auto-ssl .
docker run [YOUR_OPTIONS] docker-nginx-auto-ssl
```


## Using `$SITES` with your own template

You have to override `/usr/local/openresty/nginx/conf/server-proxy.conf` either using volume or custom image. Basic templating is implemented for variables `$SERVER_NAME` and `$SERVER_ENDPOINT`. 

Example template:

```nginx
server {
  listen 443 ssl;
  server_name $SERVER_NAME;

  include resty-server-https.conf;

  location / {
    proxy_pass http://$SERVER_ENDPOINT;
  }
}
```


## Custom Nginx Configuration

If additional customization is required, you can provide your own Nginx configuration.

Example `Dockerfile`:
```Dockerfile
FROM pswerlang/nginx-auto-ssl

COPY nginx.conf /usr/local/openresty/nginx/conf/
```

Minimal working `nginx.conf`:
```nginx
events {
  worker_connections 1024;
}

http {
  
  # required
  include resty-http.conf;

  server {
    listen 443 ssl;
    
    # required
    include resty-server-https.conf;
    
    # you should add your own locations here    
  }

  server {
    listen 80 default_server;
    
    # required
    include resty-server-http.conf;
  }
}
```

Minimal `nginx.conf` with support for `$SITES` and `conf.d` includes

```nginx
events {
  worker_connections 1024;
}

http {

  include resty-http.conf;

  server {
    listen 80 default_server;
    include resty-server-http.conf;
  }
  
  # you can insert your blocks here or inside conf.d
  
  include /etc/nginx/conf.d/*.conf;
}
```

Build and run it using
```Bash
docker build -t docker-nginx-auto-ssl .
docker run [YOUR_OPTIONS] docker-nginx-auto-ssl
```

## How does it work?

A short walktrough of what's going on here.

- [The docker entrypoint](https://github.com/Valian/docker-nginx-auto-ssl/blob/master/entrypoint.sh#L29) is responsible for preparing a location block for each site declared in `SITES` env variable. [This file is used as a template](https://github.com/Valian/docker-nginx-auto-ssl/blob/master/snippets/server-proxy.conf).
- when request comes to port 80, it's by default redirected to 443 (HTTP -> HTTPS redirection)
- when request comes to port 443, HTTPS certificate is resolved by lua code (relevant [file in this repo](https://github.com/Valian/docker-nginx-auto-ssl/blob/master/snippets/resty-server-https.conf) and [source code from lua-resty-auto-ssl](https://github.com/auto-ssl/lua-resty-auto-ssl/blob/master/lib/resty/auto-ssl/ssl_certificate.lua)). If certificate exists for a given domain and is valid, it's returned. Otherwise, a process of generating new certificate starts. It's initialized [here](https://github.com/auto-ssl/lua-resty-auto-ssl/blob/master/lib/resty/auto-ssl/ssl_providers/lets_encrypt.lua) and uses https://github.com/dehydrated-io/dehydrated for all the Let's Encrypt-related communication. It starts challenge process, prepares files for challenge and receives certificates. All of that is done in a couple of seconds, while the original request waits for the response. 
- challenge files are prepared and served under `/.well-known/acme-challenge/` ([relevant file from this repo ](https://github.com/Valian/docker-nginx-auto-ssl/blob/master/snippets/resty-server-http.conf) and source code from [lua-resty-auto-ssl](https://github.com/auto-ssl/lua-resty-auto-ssl/blob/71259605a3868b287ac0501d5850594b3f1b9cbb/lib/resty/auto-ssl/servers/challenge.lua))

There's more to it, eg locks across all workers to only generate one certificate for a domain at a time, upload of the certificate to shared storage if configured, checking if domain is whitelisted, communication with Let's Encrypt etc. All in all, it's fairly efficient and shouldn't add any noticeable overhead to nginx. 

# CHANGELOG

* **01-11-2024** - Added multi-architecture support, Python entrypoint, and multiline SITES support
* **11-11-2019** - Added gzip support and dropped TLS 1.0 and 1.1 #33
* **18-04-2019** - Added WebSocket support #22
* **29-05-2017** - Fixed duplicate redirect location after container restart #2
* **19-12-2017** - Support for `$SITES` variable   
* **2-12-2017** - Dropped HSTS by default
* **25-11-2017** - Initial release  


# LICENCE

MIT
