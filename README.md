# dataclass_factory

[![PyPI version](https://badge.fury.io/py/dataclass-factory.svg)](https://badge.fury.io/py/dataclass-factory)
[![Build Status](https://travis-ci.org/Tishka17/dataclass_factory.svg?branch=master)](https://travis-ci.org/Tishka17/dataclass_factory)

**dataclass_factory** is modern way to convert dataclasses or other objects to and from more common types like dicts

## TL;DR

Install
```bash
pip install dataclass_factory
```

Use
```python
from dataclasses import dataclass
import dataclass_factory


@dataclass
class Book:
    title: str
    price: int
    author: str = "Unknown author"


data = {
    "title": "Fahrenheit 451",
    "price": 100,
}

factory = dataclass_factory.Factory()
book: Book = factory.load(data, Book)  # Same as Book(title="Fahrenheit 451", price=100)
serialized = factory.dump(book) 
``` 

* [Requirements](#requirements)
* [Advantages](#advantages)
* [Usage](#usage)
    * [Parsers and serializers](#parsers-and-serializers)
    * [Configuring](#configuring)
        * [More verbose errors](#more-verbose-errors)
        * [Schemas](#Schemas)
        * [Common schemas](#common-schemas)
        * [Name styles](#name-styles)
        * [Generic classes](#generic-classes)
        * [Omit default](#omit-default)
        * [Structure flattening](#structure-flattening)
        * [Additional steps](#additional-steps)
        * [Polymorphic parsing](#polymorphic-parsing)
        * [Schema inheritance](#schema-inheritance)
* [Supported types](#supported-types)
* [Updating from previous versions](#updating-from-previous-versions)

## Requirements

* python >= 3.6

You can use `dataclass_factory` with python 3.6 and `dataclass` library installed from pip. 

On python 3.7 it has no external dependencies outside of the Python standard library.

## Advantages

* No schemas or configuration needed for simple cases. Just create `Factory` and call `load`/`dump` methods
* Speed. It is up to 10 times faster than `marshmallow` and `dataclasses.asdict` (see [benchmarks](benchmarks))
* Automatic name style conversion (e.g. `snake_case` to `CamelCase`)
* Automatic skipping of "internal use" fields (with leading underscore)
* Enums, typed dicts, tuples and lists are supported from the box
* Unions and Optionals are supported without need to define them in schema
* Generic dataclasses can be automatically parsed as well
* Cyclic-referenced structures (such as linked-lists or trees) also can be converted

## Usage

### Parsers and serializers

To parse dict create `Factory`, get and use `parser`  or just call `load` method 

```python
factory = Factory()  # create it only once
parser = factory.parser(Book)  # save it to reuse multiple times
book = parser(data)
# or 
book = factory.load(data, Book) 
```

**Important**:
When parsing data of `Union` type parsing stops when no ValueError/TypeError detected. 
So the order of type arguments is important.


Serialization is also very simple: use `serializer` or `load` methods
```python
factory = Factory()  # create it only once
serializer = factory.serializer(Book)  # you can reuse ot
data = serializer(book)
# or 
data = factory.dump(book, Book) 
```

If no class is provided in `dump` method it will find serializer based on real type of object.

Every parser/serializer is created when it is used (or retrieved from factory) for first time. 
Factory caches all created parsers and serializers so create it only once for every settings bundle. 

**Important**:
When serializing data of `Union` type, type arguments are ignored and serializer is detected based on real data type.

### Configuring

```python
Factory(debug_path: bool, default_schema: Schema, schemas: Dict[Type, Schema])
```

#### More verbose errors

`debug_path` parameter is used to enable verbose error mode. 

It this mode `InvalidFieldError` is thrown when some dataclass field cannot be parsed. 
It contains `field_path` which is path to the field in provided data (key and indexes).

#### Schemas

`Schema` instances used to change behavior of parsing/serializing certain classes or in general.  

* `default_schema` is `Schema` which is used by default.
* `schemas` is dict, with types as keys, and corresponding `Schema` instances as values. 

If some setting is not set for schema (or set to `None`), setting from `default_schema` is used. 
If it is also not set, library default will be used

Schema consists of:
* `names_mapping` - specifies mapping between dataclass field name (key in mapping) and key in serialized form.
* `only_mapped` (*by default, False*) - if True, all fields which are not specified in `names_mapping` are skipped. 
* `only` - list of fields which are used during parsing and serialization. Has higher priority than `only_mapped` and `skip_internal` params
* `exclude_fields` - list of fields that are NOT used during parsing and serialization. Has higher priority than `only`
* `omit_default` (*by default, False*)  - allows to omit default values when serializing
* `skip_internal` (*by default, True*) - exclude fields with leading underscore (_). Affects fields, that are not specified in `only` and `names_mapping`. 
* `trim_trainling_underscore` (*by default, True*) - if True, trailing underscore (_) will be removed for all fields except specified in `names_mapping`.
* `name_style` (*by default, snake_case*) - target field name style. Applied for fields not specified in `names_mapping`.
* `serializer` - custom function which is used to dump data of type assigned with schema.
    Normally it should not be used in default schema
    It is also returned from `factory.serializer`
* `get_serializer` - custom function which is used to create callable which is used to dump data of type assigned with schema.
    Function signature: `get_serializer(cls: type, factory: AbstractFactory, debug_path: bool) -> Callable[[T], Any]`.
    You should remember the diff between `list` and `List` at `cls` arg.
    Schema can not have `serializer` and `get_serializer` at same time (checked when Factory generate serializer).
* `parser` - custom function which is used to load data of type assigned with schema.  
    Normally it should not be used in default schema
    It is also returned from `factory.parser`
* `get_parser` - custom function which is used to create callable which is used to load data of type assigned with schema.
    Function signature: `get_parser(cls_: type, factory: AbstractFactory, debug_path: bool) -> Callable[[Any], T]`.
    You should remember the diff between `list` and `List` at `cls` arg.
    Schema can not have `parser` and `get_parser` at same time (checked when Factory generate parser).
* `pre_parse`, `post_parse`, `pre_serialize`, `post_serialize` - callables that will be used as additional parsing/serializing steps.

Currently only `serializer` and `parser` are supported for non-dataclass types

Example, 
```python
@dataclass
class Person:
    _first_name: str
    last_name_: str


factory = Factory(schemas={
    Person: Schema(
        trim_trailing_underscore=True,
        skip_internal=False
    )}
)

person = Person("ivan", "petrov")
serial_person = {
    "_first_name": "ivan",
    "last_name": "petrov"
}

assert factory.dump(person) == serial_person
```

#### Common schemas

`schema_helpers` module contains several commonly used schemas:
* `unixtime_schema` - converts datetime to unixtime and vice versa
* `isotime_schema` - converts datetime to string containing ISO 8601. Supported only on Python 3.7+
* `uuid_schema` - converts UUID to string

Example:
```python
factory = Factory(
    schemas={
        UUID: schema_helpers.uuid_schema,
        datetime: schema_helpers.isotime_schema,
    }
)
```

#### Name styles

You have to follow PEP8 convention for fields names (snake_case) or style conversion will not work (`ValueError`)

```python
factory = Factory(default_schema=Schema(
    name_style=NameStyle.camel
))


@dataclass
class Person:
    first_name: str
    last_name: str


person = Person("ivan", "petrov")
serial_person = {
    "FirstName": "ivan",
    "LastName": "petrov"
}

assert factory.dump(person) == serial_person
```

Following name styles are supported:
* `snake` (snake_case)
* `kebab` (kebab-case)
* `camel_lower` (camelCaseLower)
* `camel` (CamelCase)
* `lower` (lowercase)
* `upper` (UPPERCASE)
* `upper_snake` (UPPER_SNAKE_CASE)
* `camel_snake` (Camel_Snake)
* `dot` (dot.case)
* `camel_dot` (Camel.Dot)
* `upper_dot` (UPPER.DOT)

#### Generic classes

It is possible to dump and load instances of generic dataclasses with. 
You can set schema for generic or concrete types with one limitation:
It is not possible to detect concrete type of dataclass when dumping.
So if you need to have different schemas for different concrete types you should explicitly set them when dumping your data.

```python
T = TypeVar("T")


@dataclass
class FakeFoo(Generic[T]):
    value: T


factory = Factory(schemas={
    FakeFoo[str]: Schema(name_mapping={"value": "s"}),
    FakeFoo: Schema(name_mapping={"value": "i"}),
})
data = {"i": 42, "s": "Hello"}
assert factory.load(data, FakeFoo[str]) == FakeFoo("Hello")
assert factory.load(data, FakeFoo[int]) == FakeFoo(42)
assert factory.dump(FakeFoo("hello"), FakeFoo[str]) == {"s": "hello"}  # concrete type is set explicitly
assert factory.dump(FakeFoo("hello")) == {"i": "hello"}  # generic type is detected automatically
```

#### Omit default

Many serializers allow to omit `None` values (it may be called `omit-empty` or something similar), but is not always correct. 
In some cases you have default value for field different from `None`, so parsing of produced dict will not reassemble original structure.

Opposite to that, we have `omit_default` option. It just skips values which are equals to default. 
If your default values are `None` it works just the same way as mentioned above `omit-empty`

```python
@dataclass
class Data:
    x: int = 1
    y: List = field(default_factory=list)
    z: str = field(default="test")

factory = Factory(default_schema = Schema(omit_default=True))

assert factory.dump(Data()) == {}
assert factory.dump(Data(x=1, y=[], z="hello")) == {"z": "hello"}

```

#### Structure flattening

Since version 2.2 you can flatten hierarchy of data when parsing.
Also it is possible to serialize flat dataclass to complex structure.

To enable configure thi behavior just use tuples instead of strings in field mapping.
Provide numbers to create lists and strings to create dicts.

For example if you have simple dataclass:
```python
@dataclass
class A:
    x: str
    y: str
```

And you want to parse following structure getting `A("hello", "world")` as a result:
```json
{
  "a": {
    "b": ["hello"]
  },
  "y": "world"
}
```

The only thing you need is to create such a schema and use `Factory`:
```python
schema = Schema[A](
    name_mapping={
        "x": ("a", "b", 0),
    }
)
factory = Factory(schemas={A: schema})
parsed_a = factory.load(data, A)
```

**Important:** When serializing to list all list items with no fields to place will be filled with None.

#### Additional steps

You can set `pre_parse`, `post_parse`, `pre_serialize` and `post_serialize` schema attributes to provide additional parsing/serializing steps.

For example, if you want to store some field as string containing json data and check value of other field you can write code like

```python
@dataclass
class Data:
    items: List[str]
    name: str


def post_serialize(data):
    data["items"] = json.dumps(data["items"])
    return data


def pre_parse(data):
    data["items"] = json.loads(data["items"])
    return data


def post_parse(data: Data) -> Data:
    if not data.name:
        raise ValueError("Name must not be empty")
    return data


data_schema = Schema[Data](
    post_serialize=post_serialize,
    pre_parse=pre_parse,
    post_parse=post_parse,
)

factory = Factory(schemas={Data: data_schema})
data = Data(['a', 'b'], 'My Name')
serialized = {'items': '["a", "b"]', 'name': 'My Name'}
assert factory.dump(data) == serialized
assert factory.load(serialized, Data) == data
try:
    factory.load({'items': '[]', 'name': ''}, Data)
except ValueError as e:
    print("Error detected:", e)  # Error detected: Name must not be empty

```  

**Important**: Data, passed to `pre_serialize` is not a copy. Be careful modifying it.

#### Polymorphic parsing

Very common case is to select class based on information in data.

If required fields differ between classes, no configuration required. But sometimes you want to make a selection more explicitly.
For example, if data field "type" equals to "item" data should be parsed as Item, if it is "group" then Group class should be used.

For such case you can use `type_checker` from `schema_helpers` module. It creates a function, which should be used on pre_parse step.

```python
from dataclass_factory import Factory, Schema
from dataclass_factory.schema_helpers import type_checker

@dataclass
class Item:
    name: str
    type: str


@dataclass
class Group:
    name: str
    type: str

Something = Union[Item, Group]


factory = Factory(schemas={
    Item: Schema(pre_parse=type_checker("item", field="type")),
    Group: Schema(pre_parse=type_checker("group")),  # `type` is default name for checked field
})

assert factory.load({"name": "some name", "type": "group"}, Something) == Group("some name")
```

If you need you own pre_parse function, you can set it as parameter for `type_checker` factory.

For more complex cases you can do any work on parse steps.
Just raise `ValueError` if you detected that current class is not acceptable for provided data, and parser will go to the next one

#### Schema inheritance  

In some case it is useful not to create instance of Schema, but child class.

```python
class DataSchema(Schema[Any]):
    skip_internal = True

    def post_parse(self, data):
        print("parsing done")
        return data


factory = Factory(default_schema=DataSchema(trim_trailing_underscore=False))

factory.load(1, int)  # prints: parsing done
```

**Important**:
1. Factory creates a copy of schema for each type filling missed args. If you need to get access to some data in schema, 
    get a working instance of schema with `Factory.schema` method
2. Single schema instance can be used multiple time simultaneously because of multithreading or recursive structures. 
    Be careful modifying data in schema

## Supported types

* numeric types (`int`, `float`, `Decimal`, `complex`)
* `bool`
* `str`, `bytearray`, `bytes`
* `List`
* `Tuple`, including something like `Tuple[int, ...]` or `Tuple[int, str, int]`
* `Dict`
* `Enum` is converted using its value
* `Optional`
* `Any`, using this type no conversion is done during parsing. But serialization is based on real data type
* `Union`
* `Literal` types, including variant from `typing_exstensions`
* `TypedDict` types with checking of `total`, including variant from `typing_exstensions`
* `dataclass` 
* `Generic` dataclasses 
* `datetime` and `UUID` can be converted using predefined schemas
* Custom classes can be parsed automatically using info from their `__init__` method.  
    Or you can provide custom parser/serializer

## Updating from previous versions
In versions 1.1+:
* separate `ParserFactory` and `SerializerFactory` should be refused in favor of `Factory`
* `trim_trailing_underscore` of factories parameter moved to `default_schema`
* `type_factories`, `name_styles` and `type_serializers` moved to `schemas` dict
    
In versions <1.1:
* `dict_factory` used with `asdict` function must be replaced with `Factory`-based serialization as it is much faster

In versions <1.0:
* `parse` method must be replaced with `Factory`-based parsing as it much faster
    
All old methods and classes are still available but are deprecated and will be removed in future versions
