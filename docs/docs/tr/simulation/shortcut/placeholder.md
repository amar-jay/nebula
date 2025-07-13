# Placeholder

Parses the content of the provided String and returns the result.

## Placeholder Patterns

- `%shortcut_<file>%`
- `%shortcut_<file>:<replacements>%`

## Options

### `file`

| Type   | Required | Default |
|--------|----------|---------|
| String | Yes      |         |

Name of the file within the `shortcuts` folder. The `.txt` can be omitted from the filename itself (i.e. `%shortcut_example%` will resolve to `example.txt`).

### `replacements`

| Type   | Required | Default |
|--------|----------|---------|
| String | No       |         |

A colon (`:`) separated list of values that should replace the corresponding `{n}` placeholder in the TXT file.

`n` would be a number starting at zero and would match a provided entry in the replacement list (i.e. `{0}` would be first entry, `{1}` the second and so on).

## Examples

```
%shortcut_example%              -> Returns the text of example.txt.
%shortcut_example:apple:banana% -> Replaces {0} with apple and {1} with banana and returns the result.
```