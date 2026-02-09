# systemd units

These example units assume you cloned the repo to `~/HyperMemory`.

## Install (user service)

```bash
mkdir -p ~/.config/systemd/user
cp systemd/mf-embeddings.service ~/.config/systemd/user/

systemctl --user daemon-reload
systemctl --user enable --now mf-embeddings.service

curl -s http://127.0.0.1:8080/health
```

To view logs:

```bash
journalctl --user -u mf-embeddings.service -f
```
