# Capitalize

The capitalize Text placeholder uppercases the first letter of either the full text or every single word depending on if an `<option>` was set or not.

## Placeholder Patterns

- `%formatter_text_capitalize_<text>%`
- `%formatter_text_capitalize_<option>_<text>%`

## Options

### `option`

| Type   | Required | Conditions | Default |
|--------|----------|------------|---------|
| String | No       |            |         |

Sets a specific mode to use for capitalizing the text.

/// details | Available options
    type: example

| Option          | Description                                                                          |
|-----------------|--------------------------------------------------------------------------------------|
| `!normal!`      | Default. Uppercases the first character of the text and ignores every other.         |
| `!strict!`      | Uppercases the first character of the text and lowercases every other.               |
| `!title!`       | Uppercases the first character of every word in the text and ignores every other.    |
| `!titlestrict!` | Uppercases the first character of every word in the text and lowercases every other. |
///

### `text`

| Type   | Required | Conditions | Default |
|--------|----------|------------|---------|
| String | Yes      |            |         |

The text to capitalize.

## Examples

```
/papi parse me %formatter_text_capitalize_capitalize me!%            -> Capitalize me!
/papi parse me %formatter_text_capitalize_!strict!_CAPITALIZE ME!%   -> Capitalize me!
/papi parse me %formatter_text_capitalize_!title!_i'm a TITLE!%      -> I'm A TITLE!
/papi parse me %formatter_text_capitalize_!titlestrict!_I'm a TITLE% -> I'm A Title!
```