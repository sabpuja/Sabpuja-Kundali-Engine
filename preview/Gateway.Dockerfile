FROM caddy:2.10.2-alpine
# Gateway listens only on unprivileged :8080; strip binary's low-port file capability.
# This allows cap_drop: ALL + no-new-privileges without exec permission failures.
RUN setcap -r /usr/bin/caddy
