# AGENTS.md

Working notes for agents (and people) changing this repository. The point is to
save you the time the last contributor already spent: the datum numbers you must
not move, how to export the part, how to prove a change did not break the fit,
and the traps that have already bitten.

Read [README.md](README.md) for what the part is and how to print it.
`vent_preview/` holds the measurement sheets behind every number quoted here.

## The part, in one paragraph

The bottom shell of the Vicharak Axon 0.3/0.2 case, reworked for the SENSE
device. The vendor geometry (screw bosses, rim, lid seat, corner posts, both end
grilles) is kept exactly as shipped; two features are added: a slot grille in
both long walls, and a 25 mm fan seat cut into the tray floor. The board goes in
component-side down, so the RK3588, its heatsink and the fan live in the layer
between the board and the floor.

## Commands

```sh
# export the print-ready STL (binary, manifold backend).
# Expect: "Status: NoError", "manifold", then the vertex and facet counts.
openscad -o "Axon0p3_0p2_Case_Bottom Part_121224.scad.stl" \
         --export-format binstl --backend=manifold \
         "Axon0p3_0p2_Case_Bottom Part_121224.scad"

python3 tools/check.py health  "Axon0p3_0p2_Case_Bottom Part_121224.scad.stl"
python3 tools/check.py diff    new.stl old.stl      # must say OK
python3 tools/check.py solid   part.stl -0.75 -0.50 13.2 -0.5   # wall/seat probes
```

`tools/check.py` needs only numpy. `diff` is the fit check: it compares two
exports' material maps on a 1 mm grid and fails if anything changed outside the
fan's 36 × 36 mm footprint.

## The datum — do not move these

Measured from this mesh and from Vicharak's board STEP. Everything else follows
from them.

| what | value | how it was measured |
| --- | --- | --- |
| board screw bosses | Ø2.65 mm holes at (±47.75, ±34.5) | enclosed voids in the floor, scan at z = −13 |
| the board | 101.50 × 75.00 × 1.60 mm, M2.5 holes 3.0 mm in from every edge | `AXON_3D_file_V0.3.step` + the docs |
| board centre | the case's (0, 0) — the screw rectangle is centred on the tray | bosses above, board holes above |
| floor | inner surface z = −14.6, outer −17.6, 3.0 mm, flat and free for &#124;x&#124; < 30, &#124;y&#124; < 25 | ray casts, `check.py solid` |
| vent band | z = −14.5 … −7.6, same band as the original end grilles | measured on the vendor mesh |
| RK3588 | 23.00 × 23.00 × 1.89 mm, centre (−0.75, −0.50) off the board centre, on the board's under-face | `AXON_3D_file_V0.3.step` |
| chip underside | z ≈ −5.9 in this part | board under-face at −4 minus 1.9 |
| interior obstacles | blocks on the −Y wall at x = −29…−17 and 31…40; panel ribs on the +Y wall at x = −29…−28 and 4…5 | material maps at z = −13 … 0 |

The board STEP also settles the orientation: with the board's x axis along the
case's +X and its y axis along the case's +Y, the 22-pin PCIe/SATA FPC on the
board's under-face lands on the 30 × 11 mm opening in the +Y wall. Mirror
`fan_center` if the board goes in the other way round.

## Rules that keep the part fitting

- **Never change the bosses, the rim, the lid seat, the corner posts or the two
  end grilles.** They are what the shipped case already fits; run `check.py diff`
  against the previous export before you commit.
- Keep the vent rows clear of the interior obstacles in the table above, and keep
  their band on z = −14.5 … −7.6 so the ring lines up with the end grilles.
- Keep the slot profile chamfered, not round-ended: an arc is tangent to the
  slot's flat sides and that tangency makes the exact boolean emit ~1600
  hair-thin facets.
- Keep the fan seat **cut, never added**. The floor is 3.0 mm thick, so a seat
  raised above it needs a union, and a union of a rounded ring with this
  converted mesh leaves 272 buried duplicate facets in the export.
- Keep the lid's cable opening (top of the +Y wall inner face at z = −4) as the
  reference for the board's under-face. Everything about the vertical budget
  hangs off it.

## Verification — what "done" means here

Evidence before assertions. A change is finished when all of these pass:

1. `openscad … --backend=manifold` prints `Status: NoError`, `manifold`, and the
   facet count you expect. Since the OpenSCAD export writes `polyhedron` faces
   with the opposite winding to STL, the signed volume of the export is negative;
   that is normal here — do not "fix" it by reversing the mesh, the boolean
   result stays correct and slicers flip it.
2. `python3 tools/check.py health part.stl` — open edges 0, and no non-manifold
   edges at a 1 µm weld. Check at `quantum=1e-6` when the number is small: a
   1 µm weld merges near-coincident vertices and invents edges shared by four
   faces.
3. `python3 tools/check.py diff new.stl old.stl` — "OK: every difference is
   inside the fan footprint", or, for a vent change, no difference outside the
   band z = −14.5 … −7.6.
4. `python3 tools/check.py solid part.stl <x> <y> …` on the feature you touched:
   the slot webs read 2.0 mm, the seat bore reads 25.7 mm wide at mid-height with
   a 0.5 mm ledge at the bottom, the seat mouth reads 26.7 mm at the inner face.
5. The preview sheets in `vent_preview/` are documentation, not a build step.
   Regenerate them by hand when a change makes them wrong.

## The mesh block

`object1` is a cleaned copy of the vendor STEP/STL export, not the export itself:

- welded 48 852 duplicated per-facet vertices down to 2 784;
- removed two floating zero-volume patches (8 and 32 facets);
- repaired 63 non-manifold edges, made the facet winding coherent;
- planar-aware quadric decimation 16 284 → 6 000 facets (mean deviation 0.001 mm,
  99th percentile 0.025 mm, max 0.088 mm; the 1 mm end grilles keep 98 % of their
  open area).

Do not hand-edit the point or face list. To regenerate, take
`AXON_3D_file_V0.3.step` from the docs, run it through PyMeshLab in this order —
`remove_duplicate_vertices`, `remove_unreferenced_vertices`, `remove_null_faces`,
`remove_duplicate_faces`, `repair_non_manifold_edges`,
`repair_non_manifold_vertices`, `remove_connected_component_by_face_number`
(minimum size 1000), `re_orient_faces_coherently`, then
`decimation_quadric_edge_collapse` with `planarquadric=True` and a target of
6 000 — and check the counts after every filter.

## Parameters

All at the top of their sections. `vent_*` in the VENT SECTION (`vent_slot_w`,
`vent_pitch`, `vent_z_bot/top`, `vent_corner`, `vent_bevel`, and the row lists);
`fan_*` in the FAN SECTION (`fan_size`, `fan_clearance`, `fan_corner_r`,
`fan_hole_d`, `fan_lead`, `fan_ledge`, `fan_center`, plus `fan_seat` and
`fan_seat_raised`). Mirror slot rows in both walls when you change one.

## Traps that have already cost time

1. **A union with this mesh can leave buried duplicate facets.** The seat ring
   cost 272 duplicated needle faces at its base even though the minimal case
   (a block sunk into a plate) is clean. Cut features into the floor; do not add
   material to it.
2. **Cutting into the floor leaves faces buried in it.** Keep every cutter at
   least 0.1 mm clear of the floor's inner surface (−14.6), or sunk a defined
   amount, never exactly on it.
3. **A round-ended (capsule) slot is tangent to its own sides** and makes the
   boolean emit ~1600 hair-thin facets. The chamfered rectangle is deliberate.
4. **Rays that graze a feature lie.** Sampling exactly on a slot's centre line
   hits the slot cap's edge, and a horizontal ray through a wall that tapers in y
   measures the wall's slope, not the slot's width. Offset the sample grid (the
   0.37 mm offset in `check.py`) and probe at a height in the slot's straight
   part.
5. **The vendor mesh is a triangle soup.** Weld before any topological test, or
   every edge reads as open. And a 1 µm weld invents non-manifold edges — check
   at 1e-6 before believing a small count.
6. **PyMeshLab fails quietly on a wrong parameter name.** `threshold` is not a
   parameter of `meshing_remove_duplicate_vertices`; when a filter fails, an
   empty mesh or a filter that did nothing follows. Print the vertex and face
   counts after every filter.
7. **OpenSCAD's STL winding is inverted for `polyhedron`.** The export's signed
   volume is negative and always has been. Slicers detect and flip it; do not
   "repair" it.
8. **Splicing this file to build a test variant is easy to get wrong.** The mesh
   block, the VENT SECTION and the FAN SECTION each define modules the others
   call; a truncated splice silently drops a module and OpenSCAD only warns, so
   you get a plausible export of the wrong geometry. Diff the facet count.
9. **`sense-Top/` is a separate part.** A change here must not require a change
   there: the rim and the lid seat stay as the vendor shipped them.

## Do not

- **Move the board datum** (the bosses) or the rim and lid seat.
- **Add material to the floor** — cut, do not build up.
- **Change the vent band or profile** without re-running the bridge and support
  check: the 0.8 mm flat cap and the ~59° bevels are what make the part
  support-free.
- **Commit a derived binary** (STL, renders, preview sheets) without the source
  change that produced it, and regenerate the STL from the current `.scad`
  rather than committing an export of an older revision.
- **Re-commit the vendor files under new names.** `senseBottom/` and `sense-Top/`
  are the reference copies of what Vicharak shipped.
