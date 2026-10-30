//! Independent analysis adapter: canonical global routing and primitive terminals.
//! No simulation, source HDL recovery, or physical board net names are implied.
use prjcombine_entity::{EntityBundleItemIndex, EntityId};
use prjcombine_interconnect::{
    db::{BelInfo, BelInput, CellSlotId, TileWireCoord, WireSlotId},
    grid::{ExpandedGrid, TileCoord, WireCoord},
};
use prjcombine_spartan6::{bitstream::Bitstream, db::Database, defs::bslots};
use prjcombine_types::bitrect::BitRect as _;
use serde_json::{Value, json};
use std::{
    collections::{BTreeMap, HashMap},
    fs::{self, File},
    io::{BufRead, BufReader, BufWriter, Write},
    path::Path,
};

fn row(w: &mut impl Write, v: Value) {
    serde_json::to_writer(&mut *w, &v).unwrap();
    writeln!(w).unwrap();
}
fn lines(p: &Path) -> impl Iterator<Item = Value> {
    BufReader::new(File::open(p).unwrap())
        .lines()
        .map(|x| serde_json::from_str(&x.unwrap()).unwrap())
}
fn pname((n, i): (&str, EntityBundleItemIndex)) -> String {
    match i {
        EntityBundleItemIndex::Single => n.to_string(),
        EntityBundleItemIndex::Array { index, .. } => format!("{n}[{index}]"),
    }
}
struct Graph<'a> {
    grid: &'a ExpandedGrid<'a>,
    nodes: BTreeMap<WireCoord, usize>,
    cache: HashMap<WireCoord, Option<usize>>,
    samples: Vec<Value>,
    sample_kinds: BTreeMap<String, usize>,
    counts: BTreeMap<String, usize>,
}
impl Graph<'_> {
    fn count(&mut self, s: &str) {
        *self.counts.entry(s.to_string()).or_default() += 1;
    }
    fn node(&mut self, tc: TileCoord, w: TileWireCoord) -> Option<usize> {
        self.count("endpoint_requests");
        let Some(raw) = self.grid.try_tile_wire(tc, w) else {
            self.count("absent_tile_cell");
            return None;
        };
        if let Some(&v) = self.cache.get(&raw) {
            return v;
        }
        let Some(canonical) = self.grid.resolve_wire(raw) else {
            self.count("blackhole_unique_wires");
            self.cache.insert(raw, None);
            return None;
        };
        assert_eq!(
            self.grid.resolve_wire(canonical),
            Some(canonical),
            "non-idempotent canonical wire"
        );
        let id = if let Some(&i) = self.nodes.get(&canonical) {
            i
        } else {
            let i = self.nodes.len();
            self.nodes.insert(canonical, i);
            i
        };
        let kind = format!("{:?}", self.grid.db.wires[raw.slot].kind);
        if canonical != raw {
            self.count("unique_nontrivial_aliases");
            let n = self.sample_kinds.entry(kind.clone()).or_default();
            if *n < 8 {
                self.samples.push(json!({"raw":raw.to_string(self.grid.db),"canonical":canonical.to_string(self.grid.db),"raw_kind":kind}));
                *n += 1;
            }
        }
        self.cache.insert(raw, Some(id));
        Some(id)
    }
    fn local(
        &mut self,
        tc: TileCoord,
        text: &str,
        wires: &HashMap<String, WireSlotId>,
    ) -> (Option<usize>, bool) {
        let (s, inv) = if let Some(s) = text.strip_prefix('~') {
            (s, true)
        } else {
            (text, false)
        };
        let class = &self.grid.db.tile_classes[self.grid[tc].class];
        let (cell, wire) = if class.cells.len() == 1 {
            (CellSlotId::from_idx(0), s)
        } else {
            let (cn, wn) = s.split_once('.').expect("cell-qualified local wire");
            (
                class
                    .cells
                    .iter()
                    .find(|(_, n)| n.as_str() == cn)
                    .unwrap()
                    .0,
                wn,
            )
        };
        let w = TileWireCoord {
            cell,
            wire: *wires
                .get(wire)
                .unwrap_or_else(|| panic!("unknown local wire {wire}")),
        };
        (self.node(tc, w), inv)
    }
}
fn bit(
    bs: &Bitstream,
    rects: &prjcombine_entity::EntityVec<
        prjcombine_types::bitrect::BitRectId,
        prjcombine_spartan6::bitstream::BitRect,
    >,
    p: prjcombine_types::bitrect::PolTileBit,
) -> bool {
    bs.get_bit(rects[p.bit.rect].xlat_pos_fwd((p.bit.frame, p.bit.bit))) ^ p.inv
}
fn main() {
    let args: Vec<_> = std::env::args().collect();
    assert_eq!(args.len(), 5, "db raw-image prior-decoded output");
    let out = Path::new(&args[4]);
    fs::create_dir_all(out).unwrap();
    let db = Database::from_file(&args[1]).unwrap();
    let dev = db.devices.iter().find(|d| d.name == "xc6slx45").unwrap();
    let ex = db.chips[dev.chip].expand_grid(&db.int, &dev.disabled);
    let mut bs = ex.parse_bitstream(&fs::read(&args[2]).unwrap(), None);
    let fixes: Vec<_> = bs.frame_fixups.iter().map(|(&p, &v)| (p, v)).collect();
    for ((f, b), v) in fixes {
        bs.frame_data.set(f * 1040 + b, v);
    }
    let tiles: HashMap<_, _> = ex
        .egrid
        .tiles()
        .map(|(tc, _)| (tc.to_string(&db.int), tc))
        .collect();
    let wires: HashMap<_, _> = db
        .int
        .wires
        .iter()
        .map(|(id, w)| (w.name.clone(), id))
        .collect();
    let mut g = Graph {
        grid: &ex.egrid,
        nodes: BTreeMap::new(),
        cache: HashMap::new(),
        samples: vec![],
        sample_kinds: BTreeMap::new(),
        counts: BTreeMap::new(),
    };
    let mut edges = BufWriter::new(File::create(out.join("global-edges.jsonl")).unwrap());
    let prior = Path::new(&args[3]);
    let mut edge_id = 0;
    for r in lines(&prior.join("routing-settings.jsonl")) {
        let tc = tiles[r["tile"].as_str().unwrap()];
        let kind = r.get("kind").and_then(Value::as_str).unwrap_or("Mux");
        let pairs: Vec<(&str, &str)> = if kind == "PairMux" {
            r["dst"]
                .as_array()
                .unwrap()
                .iter()
                .zip(r["src"].as_array().unwrap())
                .filter_map(|(d, s)| Some((s.as_str()?, d.as_str()?)))
                .collect()
        } else if kind == "BiPass" {
            vec![
                (r["a"].as_str().unwrap(), r["b"].as_str().unwrap()),
                (r["b"].as_str().unwrap(), r["a"].as_str().unwrap()),
            ]
        } else {
            vec![(r["src"].as_str().unwrap(), r["dst"].as_str().unwrap())]
        };
        for (s, d) in pairs {
            let (src, inv) = g.local(tc, s, &wires);
            let (dst, dinv) = g.local(tc, d, &wires);
            assert!(!dinv);
            let inv = inv ^ r.get("inverted").and_then(Value::as_bool).unwrap_or(false);
            row(
                &mut edges,
                json!({"id":edge_id,"src":src,"dst":dst,"inv":inv,"kind":kind,"tile":r["tile"],"src_local":s,"dst_local":d,"status":if src.is_some()&&dst.is_some(){"resolved"}else{"unmapped_endpoint"}}),
            );
            edge_id += 1;
        }
    }
    edges.flush().unwrap();
    let mut ambiguous = BufWriter::new(File::create(out.join("ambiguous-edges.jsonl")).unwrap());
    for r in lines(&prior.join("decoder-issues.jsonl")) {
        if r["kind"] != "routing_mux_unknown_pattern" {
            continue;
        }
        let tc = tiles[r["tile"].as_str().unwrap()];
        let (dst, _) = g.local(tc, r["dst"].as_str().unwrap(), &wires);
        let mut sources = vec![];
        for s in r["matches"].as_array().unwrap() {
            let (src, inv) = g.local(tc, s.as_str().unwrap(), &wires);
            sources.push(json!({"src":src,"inv":inv,"local":s}));
        }
        row(
            &mut ambiguous,
            json!({"tile":r["tile"],"dst":dst,"dst_local":r["dst"],"possible_sources":sources,"off_possible":r["off"],"raw":r["raw"]}),
        );
    }
    ambiguous.flush().unwrap();
    let mut terminals =
        BufWriter::new(File::create(out.join("primitive-terminals.jsonl")).unwrap());
    let mut primitives = BufWriter::new(File::create(out.join("primitives.jsonl")).unwrap());
    let mut dedicated =
        BufWriter::new(File::create(out.join("dedicated-neighbors.jsonl")).unwrap());
    let mut declared = 0;
    let mut mapped = 0;
    let mut missing = 0;
    for (tc, tile) in ex.egrid.tiles() {
        let class = &db.int.tile_classes[tile.class];
        let rects = ex.tile_bits(tc);
        for (slot, info) in &class.bels {
            let BelInfo::Bel(b) = info else { continue };
            let bc = &db.int.bel_classes[db.int.bel_class(slot)];
            let name = tc.cell.bel(slot).to_string(&db.int);
            row(
                &mut primitives,
                json!({"id":name,"class":bc.name,"tile":tc.to_string(&db.int),"tile_class":class.name,"attributes_present":b.attributes.iter().count()}),
            );
            for (id, n, ix, def) in bc.inputs.iter() {
                let pin = pname((n, ix));
                if let Some(input) = b.inputs.get(id) {
                    declared += 1;
                    let (w, inv) = match input {
                        BelInput::Fixed(p) => (p.tw, p.inv),
                        BelInput::Invertible(w, p) => (*w, bit(&bs, &rects, *p)),
                    };
                    let net = g.node(tc, w);
                    if net.is_some() {
                        mapped += 1;
                    } else {
                        missing += 1;
                    }
                    row(
                        &mut terminals,
                        json!({"primitive":name,"class":bc.name,"pin":pin,"direction":"input","net":net,"inv":inv,"local_wire":w.to_string(&db.int,class),"status":if net.is_some(){"mapped"}else{"unmapped"}}),
                    );
                } else {
                    row(
                        &mut terminals,
                        json!({"primitive":name,"class":bc.name,"pin":pin,"direction":"input","net":null,"status":if def.nonroutable{"nonroutable_schema"}else{"not_declared_in_instance"}}),
                    );
                }
            }
            for (id, n, ix, def) in bc.outputs.iter() {
                let pin = pname((n, ix));
                if let Some(ws) = b.outputs.get(id) {
                    for &w in ws {
                        declared += 1;
                        let net = g.node(tc, w);
                        if net.is_some() {
                            mapped += 1;
                        } else {
                            missing += 1;
                        }
                        row(
                            &mut terminals,
                            json!({"primitive":name,"class":bc.name,"pin":pin,"direction":"output","net":net,"local_wire":w.to_string(&db.int,class),"status":if net.is_some(){"mapped"}else{"unmapped"}}),
                        );
                    }
                } else {
                    row(
                        &mut terminals,
                        json!({"primitive":name,"class":bc.name,"pin":pin,"direction":"output","net":null,"status":if def.nonroutable{"nonroutable_schema"}else{"not_declared_in_instance"}}),
                    );
                }
            }
            for (id, n, ix, def) in bc.bidirs.iter() {
                let pin = pname((n, ix));
                if let Some(&w) = b.bidirs.get(id) {
                    declared += 1;
                    let net = g.node(tc, w);
                    if net.is_some() {
                        mapped += 1;
                    } else {
                        missing += 1;
                    }
                    row(
                        &mut terminals,
                        json!({"primitive":name,"class":bc.name,"pin":pin,"direction":"bidir","net":net,"local_wire":w.to_string(&db.int,class),"status":if net.is_some(){"mapped"}else{"unmapped"}}),
                    );
                } else {
                    row(
                        &mut terminals,
                        json!({"primitive":name,"class":bc.name,"pin":pin,"direction":"bidir","net":null,"status":if def.nonroutable{"nonroutable_schema"}else{"not_declared_in_instance"}}),
                    );
                }
            }
            if slot == bslots::SLICE[0] || slot == bslots::DSP {
                row(
                    &mut dedicated,
                    json!({"kind":"carry_neighbor_geometry","dst_primitive":name,"src_primitive":ex.bel_carry_prev(tc.cell.bel(slot)).map(|b|b.to_string(&db.int)),"scope":"Pinned geometry helper; internal cascade pin behavior is not synthesized by this exporter."}),
                );
            }
        }
    }
    terminals.flush().unwrap();
    primitives.flush().unwrap();
    dedicated.flush().unwrap();
    let mut nodes = BufWriter::new(File::create(out.join("global-nets.jsonl")).unwrap());
    let mut ordered: Vec<_> = g.nodes.iter().map(|(w, &id)| (id, w)).collect();
    ordered.sort_by_key(|(id, _)| *id);
    for (id, w) in ordered {
        row(
            &mut nodes,
            json!({"id":id,"wire":w.to_string(&db.int),"kind":format!("{:?}",db.int.wires[w.slot].kind),"constant":db.int.wires[w.slot].kind.is_tie()}),
        );
    }
    nodes.flush().unwrap();
    let mut pads = BufWriter::new(File::create(out.join("package-pads.jsonl")).unwrap());
    for (_, pkg, &bid) in &dev.bonds {
        if pkg != "csg324" {
            continue;
        }
        for (ball, ps) in &db.bonds[bid].pins {
            row(
                &mut pads,
                json!({"ball":ball,"pads":ps.iter().map(|p|p.to_string(&db.int)).collect::<Vec<_>>()}),
            );
        }
    }
    pads.flush().unwrap();
    fs::write(
        out.join("alias-samples.json"),
        serde_json::to_string_pretty(&g.samples).unwrap() + "\n",
    )
    .unwrap();
    let stats = json!({"global_wire_nodes":g.nodes.len(),"routing_edge_records":edge_id,"declared_terminal_wire_bindings":declared,"mapped_terminal_wire_bindings":mapped,"unmapped_terminal_wire_bindings":missing,"resolver_counts":g.counts,"canonical_idempotence_checked":"Every unique resolved local wire","scope":"Canonical physical wire segments with directed routing edges and abstract primitive terminals; defaults included; no behavioral utilization pruning."});
    fs::write(
        out.join("export-summary.json"),
        serde_json::to_string_pretty(&stats).unwrap() + "\n",
    )
    .unwrap();
    println!("{}", serde_json::to_string_pretty(&stats).unwrap());
}
