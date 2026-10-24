# Third-party notices

The project adopts **AGPL-3.0-only** as its project license and plans to use the Swiss Ephemeris software locally. See `LICENSE` for the full license.

## Swiss Ephemeris upstream license notice

Source: https://github.com/aloistr/swisseph/blob/master/LICENSE
The following notice is preserved verbatim from upstream:

```text
/* Copyright (C) 1997 - 2021 Astrodienst AG, Switzerland.  All rights reserved.

  License conditions
  ------------------

  This file is part of Swiss Ephemeris.

  Swiss Ephemeris is distributed with NO WARRANTY OF ANY KIND.  No author
  or distributor accepts any responsibility for the consequences of using it,
  or for whether it serves any particular purpose or works at all, unless he
  or she says so in writing.  

  Swiss Ephemeris is made available by its authors under a dual licensing
  system. The software developer, who uses any part of Swiss Ephemeris
  in his or her software, must choose between one of the two license models,
  which are
  a) GNU Affero General Public License (AGPL)
  b) Swiss Ephemeris Professional License

  The choice must be made before the software developer distributes software
  containing parts of Swiss Ephemeris to others, and before any public
  service using the developed software is activated.

  If the developer choses the AGPL software license, he or she must fulfill
  the conditions of that license, which includes the obligation to place his
  or her whole software project under the AGPL or a compatible license.
  See https://www.gnu.org/licenses/agpl-3.0.html

  If the developer choses the Swiss Ephemeris Professional license,
  he must follow the instructions as found in http://www.astro.com/swisseph/ 
  and purchase the Swiss Ephemeris Professional Edition from Astrodienst
  and sign the corresponding license contract.

  The License grants you the right to use, copy, modify and redistribute
  Swiss Ephemeris, but only under certain conditions described in the License.
  Among other things, the License requires that the copyright notices and
  this notice be preserved on all copies.

  Authors of the Swiss Ephemeris: Dieter Koch and Alois Treindl

  The authors of Swiss Ephemeris have no control or influence over any of
  the derived works, i.e. over software or services created by other
  programmers which use Swiss Ephemeris functions.

  The names of the authors or of the copyright holder (Astrodienst) must not
  be used for promoting any software, product or service which uses or contains
  the Swiss Ephemeris. This copyright notice is the ONLY place where the
  names of the authors can legally appear, except in cases where they have
  given special permission in writing.
*/
```

## Python binding
The initial local adapter depends on `pyswisseph==2.10.3.2`. Before release, inventory its license, transitive packages and embedded Swiss Ephemeris version, preserve its notices and record package hashes in an approved lock/manifest.

## IANA time zone data: `tzdata` Python package
The engine depends on `tzdata==2026.5` (IANA Time Zone Database 2026e), installed from PyPI. It is not copied into this repository; `src/sabpuja_kundali/tzif-manifest.json` records only the SHA-256 of each TZif file it loads.

- Package license: Apache License 2.0 (wheel metadata `License: Apache-2.0`; license files `LICENSE` and `licenses/LICENSE_APACHE`).
- Package copyright notice: "Copyright (c) 2020, Paul Ganssle (Google)" and "Copyright (c) 2026, Stan Ulbrych".
- The IANA tz source files compiled into the package state that they are in the public domain.
- Any distribution that includes the package must keep its license files.

This notice list is not a completed license review: LEG-01 and a qualified legal review of network (AGPL) use remain pending.

## Geographic data (not yet bundled)
Planned offline GeoNames database requires dataset-specific attribution and review. No runtime remote geolocation service is authorized.

Do not copy upstream binaries, planetary files or other datasets into this repository before their licensing, integrity, size and source revisions have been reviewed.
