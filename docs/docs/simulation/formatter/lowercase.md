# Lowercase

Forces the provided text to be lowercased.

## Placeholder Patterns

- `%formatter_text_lowercase_<text>%`

## Options

### `text`

| Type   | Required | Conditions | Default |
|--------|----------|------------|---------|
| String | Yes      |            |         |

The text to lowercase.

## Examples

```
/papi parse me %formatter_text_lowercase_LOWERCASE% -> lowercase
```