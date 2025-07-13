# Math Expansion

The Math expansion allows you to perform simple to complex math equations.

/// download | Download expansion
```
/papi ecloud download math
```
///

## Statistics

<span data-md-component="expansion-math">Fetching data...<br>If this text doesn't change, check that you allow javascript to be executed.</span>

## Source Code

The Source code of this expansion is available on [:simple-codeberg: Codeberg](https://codeberg.org/Andre601/Math-Expansion){ target="_blank" rel="nofollow" }

## Placeholders

- [`%math[_[decimals]:[rounding_mode]]_<expression>%`](placeholder.md)

## External Placeholders support

Placeholders from other expansions can be used by using the `{<identifier>_<value>}` pattern instead of the usual `%<identifier>_<value>%` pattern.

/// warning | Important
Only placeholders returning numbers can work reliably in the expansion.
///

## Using Percent Symbol (`%`) in Math expression

Due to how PlaceholderAPI handles placeholders can you not use the percent symbol directly in math expressions.  
However, the Math expansion provides a `[prc]` placeholder that gets replaced by a `%` symbol before evaluation the math expression.

/// warning
You cannot use `[prc]` to use `%<identifier>_<value>%` placeholders in math expressions. Placeholders are parsed before `[prc]` is.  
Use the bracket-based pattern instead.
///

## Special Math Functions

EvalEx, the library used by Math expansion for the parsing of expressions, provides so-called functions.  
Functions are unique key-words that can be used to perform more complex calculations that could otherwise not be done through normal text.

As an example, to obtain the square root of `100` you would use `SQRT(100)`.

See EvalEx's [Functions page](https://ezylang.github.io/EvalEx/references/functions.html){ target="_blank" rel="nofollow" } for a full list.

/// note
Functions are case-insensitive.
///

## Config Options

### `Decimals`

| Type   | Default |
|--------|---------|
| Number | `0`     |

Sets the default numbers of decimal places to display in the final number.

### `Rounding`

| Type   | Default   |
|--------|-----------|
| String | `half-up` |

Sets the default rounding mode to apply to the final number.

### `Debug`

| Type    | Default |
|---------|---------|
| Boolean | `false` |

Enables or disables Debug mode.  
When enabled will errors in console also print stacktraces.

### `Disable-Warnings`

| Type    | Default |
|---------|---------|
| Boolean | `false` |

Enables or disables the supressing of warnings similar to the following:

```
[00:00:00 WARN]: [PlaceholderAPI] [math] Invalid Placeholder detected!
[00:00:00 WARN]: [PlaceholderAPI] [math] Placeholder: %math_1-%
[00:00:00 WARN]: [PlaceholderAPI] [math] Cause: '1-' is not a valid Math Expression
```

It is recommended to **not** enable this option, as it can make it more difficult to find the cause of a placeholder not working.

## Changelog

Please see the [CHANGELOG.md file on Codeberg](https://codeberg.org/Andre601/Math-Expansion/src/branch/master/CHANGELOG.md){ target="_blank" rel="nofollow" } for the latest changes.