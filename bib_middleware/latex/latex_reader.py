#!/usr/bin/env python3
"""

See EOF for license/metadata/notes as applicable
"""

##-- builtin imports
from __future__ import annotations

# import abc
import datetime
import enum
import functools as ftz
import itertools as itz
import logging as logmod
import pathlib as pl
import re
import time
import types
import weakref
# from copy import deepcopy
# from dataclasses import InitVar, dataclass, field
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Final, Generic,
                    Iterable, Iterator, Mapping, Match, MutableMapping,
                    Protocol, Sequence, Tuple, TypeAlias, TypeGuard, TypeVar,
                    cast, final, overload, runtime_checkable, Generator)
from uuid import UUID, uuid1

##-- end builtin imports

##-- lib imports
import more_itertools as mitz
##-- end lib imports

import bibtexparser
import bibtexparser.model as model
from bibtexparser import exceptions as bexp
from bibtexparser import middlewares as ms
from bibtexparser.model import MiddlewareErrorBlock
from bibtexparser.middlewares.middleware import BlockMiddleware, LibraryMiddleware
from bibtexparser.middlewares.names import parse_single_name_into_parts, NameParts

from pylatexenc.latex2text import LatexNodes2Text, MacroTextSpec, get_default_latex_context_db

##-- logging
logging = logmod.getLogger(__name__)
##-- end logging

DEFAULT_DECODE_RULES : Final[dict] = {
    "BM-reader-simplify-urls" : MacroTextSpec("url", simplify_repl="%s"),
}

class LatexReader(ms.LatexDecodingMiddleware):
    """ Latex->unicode transform.
    all strings in the library, except urls, files, doi's and crossrefs
    """

    _skip_fields = ["url", "file", "doi", "crossref"]

    @staticmethod
    def metadata_key() -> str:
        return "BM-latex-reader"

    @staticmethod
    def build_decoder(*, rules:None|dict=None, **kwargs) -> LatexNodes2Text:
        context_db = get_default_latex_context_db()
        rules         = rules or DEFAULT_DECODE_RULES.copy()
        logging.debug("Building Latex Decoder: %s", rules)
        for x, y in rules.items():
            match y:
                case list() if all(isinstance(y2, MacroTextSpec) for y2 in y):
                    context_db.add_context_category(x, prepend=True, macros=y)
                case MacroTextSpec():
                     context_db.add_context_category(x, prepend=True, macros=[y])
                case _:
                    raise TypeError("Bad Decode Rules Specified", y)

        return LatexNodes2Text(latex_context=context_db, **kwargs)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._total_rules = DEFAULT_DECODE_RULES
        self._total_options = {
            "keep_braced_groups" : kwargs.get('keep_braced_groups', False),
            "math_mode"          : kwargs.get('math_mode', 'text'),
        }
        self.rebuild_decoder()

    def rebuild_decoder(self, *, rules:dict=None, **kwargs):
        self._total_rules.update(rules or {})
        self._total_options.update(kwargs)
        self._decoder                = LatexReader.build_decoder(rules=self._total_rules, **self._total_options)

    def transform_entry(self, entry: Entry, library: Library) -> Block:
        errors = []
        for field in entry.fields:
            if any(x in field.key for x in self._skip_fields):
                continue
            if isinstance(field.value, str):
                field.value, e = self._transform_python_value_string(field.value)
                errors.append(e)
            elif isinstance(field.value, ms.NameParts):
                field.value.first = self._transform_all_strings(
                    field.value.first, errors
                )
                field.value.last = self._transform_all_strings(field.value.last, errors)
                field.value.von = self._transform_all_strings(field.value.von, errors)
                field.value.jr = self._transform_all_strings(field.value.jr, errors)
            else:
                logging.info(
                    f"[{self.metadata_key()}] Cannot python-str transform field {field.key}"
                    f" with value type {type(field.value)}"
                )

        errors = [e for e in errors if e != ""]
        if len(errors) > 0:
            errors = bexp.PartialMiddlewareException(errors)
            return MiddlewareErrorBlock(block=entry, error=errors)
        else:
            return entry


    def _test_string(self, text) -> str:
        return self._decoder.latex_to_text(text)
