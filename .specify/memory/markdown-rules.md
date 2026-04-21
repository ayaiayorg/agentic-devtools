# Markdown Output Rules

**Fenced code blocks**: Always include an explicit language specifier on the
opening fence of every fenced code block. Use the most specific identifier
available (e.g. `bash`, `python`, `json`, `yaml`, `toml`, `md`). For plain
text, diagrams, ASCII art, or console output, use `text`. Never start a
fenced code block with bare triple backticks; always open with ```` ```lang ````
and close with ```` ``` ````.
