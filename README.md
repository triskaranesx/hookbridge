# hookbridge

Lightweight webhook relay server with filtering, retries, and payload transformation.

---

## Installation

```bash
pip install hookbridge
```

Or install from source:

```bash
git clone https://github.com/yourname/hookbridge.git && cd hookbridge && pip install -e .
```

---

## Usage

Start the relay server:

```bash
hookbridge start --config config.yaml
```

Example `config.yaml`:

```yaml
listen:
  port: 8080

routes:
  - name: github-to-slack
    source: /hooks/github
    destination: https://hooks.slack.com/services/your/webhook/url
    filter:
      field: action
      equals: opened
    transform:
      template: "New PR opened: {{ payload.pull_request.title }}"
    retries: 3
    retry_delay: 5
```

Send a webhook to `http://localhost:8080/hooks/github` and hookbridge will filter, transform, and forward it to the configured destination — retrying on failure.

---

## Features

- **Filtering** — forward only events that match defined conditions
- **Transformation** — reshape payloads using Jinja2 templates
- **Retries** — automatic retry with configurable delay and backoff
- **Multi-route** — relay a single source to multiple destinations

---

## License

MIT © 2024 Your Name