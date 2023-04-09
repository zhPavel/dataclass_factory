* Sane defaults for JSON processing, no configuration is needed for simple cases.
* Separated model definition and rules of conversion
  that allow preserving [SRP](https://blog.cleancoder.com/uncle-bob/2014/05/08/SingleReponsibilityPrinciple.html)
  and have different representations for one model.
* Speed. It is one of the fastest data parsing and serialization libraries.
* There is no forced model representation, adaptix can adjust to your needs.
* Support [dozens](https://adaptix.readthedocs.io/en/latest/specific_types_behavior.html) of types,
  including different model kinds:
  ``@dataclass``, ``TypedDict``, ``NamedTuple``, and [``attrs``](https://www.attrs.org/en/stable/)
* Working with cyclic-referenced structures (such as linked lists or trees).
* Saving [path](https://adaptix.readthedocs.io/en/latest/tutorial.html#struct-path)
  where an exception is raised (including unexpected errors).
* Easy [integration](https://adaptix.readthedocs.io/en/latest/tutorial.html#struct-path)
  with Sentry, Datadog, and other monitoring systems.
* Machine-readable [errors](https://adaptix.readthedocs.io/en/latest/tutorial.html#error-handling)
  that could be dumped.
* Support for user-defined generic models.
* Automatic name style conversion (e.g. `snake_case` to `camelCase`).
* [Predicate system](https://adaptix.readthedocs.io/en/latest/tutorial.html#predicate-system)
  that allows to concisely and precisely override some behavior.
* Disabling additional checks to speed up data loading from trusted sources.
* No auto casting by default. The loader does not try to guess value from plenty of input formats.