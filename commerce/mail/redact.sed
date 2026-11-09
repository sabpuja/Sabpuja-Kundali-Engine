# Mail logs must not carry recipient or sender addresses (the commerce privacy model keeps e-mail out of logs).
s/<[^<>@ ]+@[^<>@ ]+>/<redacted>/g
s/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/redacted@redacted/g
