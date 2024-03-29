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

##-- logging
logging = logmod.getLogger(__name__)
printer = logmod.getLogger("doot._printer")
##-- end logging

import bibtexparser
import bibtexparser.model as model
from bibtexparser import middlewares as ms
from bibtexparser.middlewares.middleware import BlockMiddleware, LibraryMiddleware
from bibtexparser.middlewares.names import parse_single_name_into_parts, NameParts

class DoiValidator(BlockMiddleware):
    """
      Validate Doi's, check for retractions
    """

    @staticmethod
    def metadata_key():
        return "jg-doi-validator"

    def transform_entry(self, entry, library):
        for field in entry.fields:
            if not ("file" in field.key or "look_in" in field.key):
                continue

            base = pl.Path(field.value)
            match base.parts[0]:
                case "/":
                    field.value = base
                case "~":
                    field.value = base.expanduser().absolute()
                case _:
                    field.value = self._lib_root / base

            if not field.value.exists():
                printer.warning("On Import file does not exist: %s", field.value)

        return entry
