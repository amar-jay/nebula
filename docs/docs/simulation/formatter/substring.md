# Substring

Returns a specific area of `<text>` based on the provided `[start]` and `[end]` options.

## Placeholder Patterns

- `%formatter_text_substring_[start]:[end]_<text>%`

## Options

### `start`

| Type            | Required | Conditions                                | Default |
|-----------------|----------|-------------------------------------------|---------|
| Number / String | No       | [If Number] `0 ≤ x ≤ (text.length() - 1)` | `0`     |

The start index of the String. If no number is provided will the first position of the matching text be used.

/// warning | start is 0-indexed
The number for start is 0-indexed, meaning `0 = 1`, `1 = 2` and so on.
///

### `end`

| Type            | Required | Conditions                                                     | Default         |
|-----------------|----------|----------------------------------------------------------------|-----------------|
| Number / String | No       | [If Number] `0 ≤ x ≤ text.length()`<br>[If Number] `start < x` | `text.length()` |

The end index of the String. If no number is provided will the last position of the matching text be used.

### `text`

| Type   | Required | Conditions | Default |
|--------|----------|------------|---------|
| String | Yes      |            |         |

The text to get the Substring of.

## Examples

```
/papi parse me %formatter_text_substring_3:9_Substring%                -> string
/papi parse me %formatter_text_substring_:3_Substring%                 -> Sub
/papi parse me %formatter_text_substring_3:_Substring%                 -> string
/papi parse me %formatter_text_substring_,:_Substring,Another String%  -> ,Another String
/papi parse me %formatter_text_substring_:,_Substring,Another String%  -> Substring
```