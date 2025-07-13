# Selected

Returns a randomly selected entry from the provided list.

## Placeholder Patterns

- `%randomcolor_selected_<options>%`

## Options

### `options`

| Type   | Required | Default |
|--------|----------|---------|
| String | Yes      |         |

Comma-separated list of color and formatting codes.  
Each entry should **only** be the code without either `&` or `§` before it.

Example: `%randomcolor_selected_a,b,c,d%` would return either `§a`, `§b`, `§c` or `§d`

--8<-- "color-codes.md"

--8<-- "formatting-codes.md"