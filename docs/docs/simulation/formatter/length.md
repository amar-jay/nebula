# Length

Returns the length of the provided text, including spaces.

## Placeholder Patterns

- `%formatter_text_length_<text>%`

## Options

### `text`

| Type   | Required | Conditions | Default |
|--------|----------|------------|---------|
| String | Yes      |            |         |

The text to return the length of.

## Examples

```
/papi parse me %formatter_text_length_Length% -> 6
```