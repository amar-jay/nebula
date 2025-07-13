# Formatter Expansion

The formatter expansion contains various placeholders that allow you to format numbers and text.

/// download | Download expansion
```
/papi ecloud download formatter
```
///

## Statistics

<span data-md-component="expansion-formatter">Fetching data...<br>If this text doesn't change, check that you allow javascript to be executed.</span>

## Source Code

The Source code of this expansion is available on [:simple-codeberg: Codeberg](https://codeberg.org/Andre601/Formatter-Expansion){ target="_blank" rel="nofollow" }

## Placeholders

- **Number**
    - [`%formatter_number_format[_[locale]:[pattern]]_<number>%`](format.md)
    - [`%formatter_number_from:<time_unit>_to:<time_unit>_<number>%`](from-to.md)
    - [`%formatter_number_round[_[precision]:[rounding_mode]]_<number>%`](round.md)
    - [`%formatter_number_shorten[_<rounding_mode>]_<number>%`](shorten.md)
    - [`%formatter_number_time[_<time_unit>]_<number>%`](time.md)
- **Text**
    - [`%formatter_text_capitalize[_<option>]_<text>%`](capitalize.md)
    - [`%formatter_text_length_<text>%`](length.md)
    - [`%formatter_text_lowercase_<text>%`](lowercase.md)
    - [`%formatter_text_replace_[target]_[replacement]_<text>%`](replace.md)
    - [`%formatter_text_substring_[start]:[end]_<text>%`](substring.md)
    - [`%formatter_text_uppercase_<text>%`](uppercase.md)

## External Placeholders support

Placeholders from other expansions can be used by using the `{<identifier>_<value>}` pattern instead of the usual `%<identifier>_<value>%` pattern.

## Using Percent Symbol (`%`) and Underscores (`_`) in placeholder

Due to how PlaceholderAPI handles placeholders can you not use the percent symbol in formatter. In addition can underscores also not be used as they can mess up the handling by the expansion.  
To still be able to use these characters does the formatter expansion offer two special placeholders named `{{prc}}` and `{{u}}` respectively, which get replaced by their respective values.

/// warning
You cannot use `{{prc}}` to use `%<identifier>_<value>%` placeholders in formatter. The expansion parses bracket-placeholders before converting its own placeholders.
///

## Config Options

The following Configuration options can be found in the `config.yml` of PlaceholderAPI under the `expansions -> formatter` section.

### `formatting.pattern`

| Type   | Default        |
|--------|----------------|
| String | `#,###,###.##` |

The Pattern that should be used for the formatting placeholder.  
Uses the [special Pattern Characters](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/text/DecimalFormat.html#special_pattern_character) of the DecimalFormat class in Java.

### `formatting.locale`

| Type   | Default |
|--------|---------|
| String | `en-US` |

The language and optional Country code to use.

/// warning
You have to use `-` instead of `_` for the country code option (i.e. `en-US` instead of `en_US`).
///

---

### `shorten.thousands`

| Type   | Default       |
|--------|---------------|
| String | `{{number}}K` |

Format used to indicate thousands. `{{number}}` will be replaced with the shortened number.

### `shorten.millions`

| Type   | Default       |
|--------|---------------|
| String | `{{number}}M` |

Format used to indicate millions. `{{number}}` will be replaced with the shortened number.

### `shorten.billions`

| Type   | Default       |
|--------|---------------|
| String | `{{number}}B` |

Format used to indicate billions. `{{number}}` will be replaced with the shortened number.

### `shorten.trillions`

| Type   | Default       |
|--------|---------------|
| String | `{{number}}T` |

Format used to indicate trillions. `{{number}}` will be replaced with the shortened number.

### `shorten.quadrillions`

| Type   | Default       |
|--------|---------------|
| String | `{{number}}Q` |

### `shorten.pattern`

| Type   | Default |
|--------|---------|
| String | `###.#` |

The Pattern that should be used for the shortened number.  
Uses the [special Pattern Characters](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/text/DecimalFormat.html#special_pattern_character) of the DecimalFormat class in Java.

### `shorten.rounding_mode`

| Type   | Default   |
|--------|-----------|
| String | `half-up` |

The rounding mode to use for the shortened number.

--8<-- "rounding-modes.md"

---

### `time.condensed`

| Type    | Default |
|---------|---------|
| Boolean | `false` |

Whether the value returned by the time placeholder should not contain spaces.

### `time.includeZeroDays`

| Type    | Default |
|---------|---------|
| Boolean | `false` |

Whether the value returned by the time placeholder should include zero days.

### `time.includeZeroHours`

| Type    | Default |
|---------|---------|
| Boolean | `false` |

Whether the value returned by the time placeholder should include zero hours.

### `time.includeZeroMinutes`

| Type    | Default |
|---------|---------|
| Boolean | `false` |

Whether the value returned by the time placeholder should include zero minutes.

### `time.includeZeroSeconds`

| Type    | Default |
|---------|---------|
| Boolean | `false` |

Whether the value returned by the time placeholder should include zero seconds.

### `time.includeZeroMilliseconds`

| Type    | Default |
|---------|---------|
| Boolean | `false` |

Whether the value returned by the time placeholder should include zero milliseconds.

### `time.days`

| Type   | Default       |
|--------|---------------|
| String | `{{number}}d` |

Format used to display days in the time placeholder. `{{number}}` will be replaced by the number of days.

### `time.hours`

| Type   | Default       |
|--------|---------------|
| String | `{{number}}h` |

Format used to display hours in the time placeholder. `{{number}}` will be replaced by the number of hours.

### `time.minutes`

| Type   | Default       |
|--------|---------------|
| String | `{{number}}m` |

Format used to display minutes in the time placeholder. `{{number}}` will be replaced by the number of minutes.

### `time.seconds`

| Type   | Default       |
|--------|---------------|
| String | `{{number}}s` |

Format used to display seconds in the time placeholder. `{{number}}` will be replaced by the number of seconds.

### `time.milliseconds`

| Type   | Default        |
|--------|----------------|
| String | `{{number}}ms` |

Format used to display milliseconds in the time placeholder. `{{number}}` will be replaced by the number of milliseconds.

### `time.belowZeroOutput`

| Type   | Default      |
|--------|--------------|
| String | `{{number}}` |

Sets the output that should be returned for the time placeholder when the provided number is less than zero.

- `{{number}}` will be replaced by the actual number.
- `"null"` will return `null` causing PlaceholderAPI to see the placeholder as invalid and return it as-is.

---

### `rounding.precision`

| Type   | Default |
|--------|---------|
| Number | `0`     |

Number of decimals that should be displayed.

### `rounding.mode`

| Type   | Default      |
|--------|--------------|
| String | `half-up`    |

The rounding behaviour that should be used by the rounding placeholder.

--8<-- "rounding-modes.md"

## Changelog

Please see the [CHANGELOG.md file on Codeberg](https://codeberg.org/Andre601/Formatter-Expansion/src/branch/master/CHANGELOG.md){ target="_blank" rel="nofollow" } for the latest changes.