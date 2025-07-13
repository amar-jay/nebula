# Replace

Replaces the provided `[target]` with the provided `[replacement]` in `<text>`.

## Placeholder Patterns

- `%formatter_text_replace_[target]_[replacement]_<text>%`

## Options

### `target`

| Type   | Required | Conditions | Default |
|--------|----------|------------|---------|
| String | No       |            |         |

The target text that should be replaced.  
`{{r=<pattern>}}` can be used to use a Regex pattern `<pattern>` to replace in the text.

### `replacement`

| Type   | Required | Conditions | Default |
|--------|----------|------------|---------|
| String | No       |            |         |

The text to replace the target with.

### `text`

| Type   | Required | Conditions | Default |
|--------|----------|------------|---------|
| String | Yes      |            |         |

The text to have values replaced in.

## Examples

```
/papi parse me %formatter_text_replace_ __Re pla ce%                            -> Replace
/papi parse me %formatter_text_replace_{{u}}__Re_pla_ce me%                     -> Replace me
/papi parse me %formatter_text_replace_{{r=[0-9]}}__Replace 0 only 1 numbers 2% -> Replace  only  numbers
```