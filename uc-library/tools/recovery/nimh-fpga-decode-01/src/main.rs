use prjcombine_entity::EntityId;
use prjcombine_interconnect::db::{
    BelAttribute, BelAttributeType, BelInfo, BelInput, SwitchBoxItem,
};
use prjcombine_spartan6::{
    bitstream::{BRAM_FRAME_LEN, BitPos, BitRect, Bitstream, FRAME_LEN},
    db::Database,
};
use prjcombine_types::bitrect::{BitRect as _, TileBit};
use serde_json::{Value, json};
use std::{
    collections::BTreeMap,
    fs::{self, File},
    io::{BufWriter, Write},
    path::Path,
};

fn write_row(w: &mut impl Write, v: Value) {
    serde_json::to_writer(&mut *w, &v).unwrap();
    writeln!(w).unwrap();
}

struct Coverage<'a> {
    bs: &'a Bitstream,
    referenced: Vec<u8>,
    resolved: Vec<u8>,
    stats: BTreeMap<String, usize>,
}

impl Coverage<'_> {
    fn count(&mut self, s: &str) {
        *self.stats.entry(s.to_string()).or_default() += 1;
    }
    fn pos(&self, rects: &[BitRect], bit: TileBit) -> Option<BitPos> {
        let r = *rects.get(bit.rect.to_idx())?;
        if matches!(r, BitRect::Null) {
            return None;
        }
        let pos = r.xlat_pos_fwd((bit.frame, bit.bit));
        let present = match pos {
            BitPos::Main(f, b) => {
                b < FRAME_LEN && (f < self.bs.frame_present.len() && self.bs.frame_present[f])
            }
            BitPos::Bram(f, b) => {
                b < BRAM_FRAME_LEN
                    && (f < self.bs.bram_frame_present.len() && self.bs.bram_frame_present[f])
            }
            BitPos::Iob(b) => self.bs.iob_present && b < self.bs.iob.len(),
            BitPos::Reg(r, b) => self.bs.regs.contains_key(&r) && b < 32,
            BitPos::RegPresent(_) => true,
            BitPos::Fixup(_, _) => false,
        };
        if present { Some(pos) } else { None }
    }
    fn index(&self, p: BitPos) -> Option<usize> {
        match p {
            BitPos::Main(f, b) => Some(f * FRAME_LEN + b),
            BitPos::Bram(f, b) => Some(self.bs.frame_data.len() + f * BRAM_FRAME_LEN + b),
            BitPos::Iob(b) => Some(self.bs.frame_data.len() + self.bs.bram_data.len() + b),
            _ => None,
        }
    }
    fn read(&mut self, rects: &[BitRect], bits: &[TileBit]) -> Option<Vec<bool>> {
        let mut v = Vec::new();
        for &b in bits {
            let Some(p) = self.pos(rects, b) else {
                self.count("unmapped_field_reads");
                return None;
            };
            if let Some(i) = self.index(p) {
                self.referenced[i] = 1;
            }
            v.push(self.bs.get_bit(p));
        }
        Some(v)
    }
    fn accept(&mut self, rects: &[BitRect], bits: &[TileBit]) {
        for &b in bits {
            if let Some(p) = self.pos(rects, b) {
                if let Some(i) = self.index(p) {
                    self.resolved[i] = 1;
                }
            }
        }
    }
}

fn hex_bits(bits: &[bool]) -> String {
    let mut s = String::new();
    for chunk in bits.chunks(4).rev() {
        let mut v = 0;
        for (i, &b) in chunk.iter().enumerate() {
            if b {
                v |= 1 << i;
            }
        }
        s.push(char::from_digit(v, 16).unwrap());
    }
    s
}

fn main() {
    let args: Vec<_> = std::env::args().collect();
    assert_eq!(args.len(), 4, "database bitstream output-directory");
    let out = Path::new(&args[3]);
    fs::create_dir_all(out).unwrap();
    let db = Database::from_file(&args[1]).unwrap();
    let dev = db.devices.iter().find(|d| d.name == "xc6slx45").unwrap();
    let chip = &db.chips[dev.chip];
    let expanded = chip.expand_grid(&db.int, &dev.disabled);
    let data = fs::read(&args[2]).unwrap();
    let mut bs = expanded.parse_bitstream(&data, None);
    assert_eq!(
        bs.regs[&prjcombine_spartan6::bitstream::Reg::Idcode] & 0x0fffffff,
        0x04008093
    );
    // Preserve parser's initial-versus-final distinction, then decode the final
    // state after the later FDRI writes, without changing upstream parser code.
    let mut fixups: Vec<_> = bs
        .frame_fixups
        .iter()
        .map(|(&(f, b), &value)| (f, b, value))
        .collect();
    fixups.sort();
    let fixup_rows:Vec<_>=fixups.iter().map(|&(f,b,value)|json!({"frame":f,"bit":b,"before":bs.frame_data[f*FRAME_LEN+b],"after":value})).collect();
    fs::write(
        out.join("frame-fixups.json"),
        serde_json::to_string_pretty(&fixup_rows).unwrap() + "\n",
    )
    .unwrap();
    for &(f, b, value) in &fixups {
        bs.frame_data.set(f * FRAME_LEN + b, value);
    }
    let mut frames = BufWriter::new(File::create(out.join("frames.jsonl")).unwrap());
    for (kind, info, present, bits, width) in [
        (
            "main",
            &bs.frame_info,
            &bs.frame_present,
            &bs.frame_data,
            FRAME_LEN,
        ),
        (
            "bram",
            &bs.bram_frame_info,
            &bs.bram_frame_present,
            &bs.bram_data,
            BRAM_FRAME_LEN,
        ),
    ] {
        for (i, addr) in info.iter().enumerate() {
            let v: Vec<bool> = (0..width).map(|b| bits[i * width + b]).collect();
            write_row(
                &mut frames,
                json!({"kind":kind,"index":i,"type":addr.typ,"region":addr.region,"major":addr.major,"minor":addr.minor,"present":present[i],"bits":width,"value_hex_msb_first":hex_bits(&v)}),
            );
        }
    }
    let iob: Vec<bool> = bs.iob.iter().collect();
    write_row(
        &mut frames,
        json!({"kind":"iob","present":bs.iob_present,"bits":iob.len(),"value_hex_msb_first":hex_bits(&iob)}),
    );
    frames.flush().unwrap();
    let mut regs = BufWriter::new(File::create(out.join("registers.json")).unwrap());
    write_row(
        &mut regs,
        json!(
            bs.regs
                .iter()
                .map(|(k, v)| (format!("{k:?}"), *v))
                .collect::<BTreeMap<_, _>>()
        ),
    );
    regs.flush().unwrap();
    let total = bs.frame_data.len() + bs.bram_data.len() + bs.iob.len();
    let raw: Vec<u8> = bs
        .frame_data
        .iter()
        .chain(bs.bram_data.iter())
        .chain(bs.iob.iter())
        .map(u8::from)
        .collect();
    fs::write(out.join("configuration-bits.u8"), &raw).unwrap();
    let mut c = Coverage {
        bs: &bs,
        referenced: vec![0; total],
        resolved: vec![0; total],
        stats: BTreeMap::new(),
    };
    let mut settings = BufWriter::new(File::create(out.join("primitive-settings.jsonl")).unwrap());
    let mut routes = BufWriter::new(File::create(out.join("routing-settings.jsonl")).unwrap());
    let mut issues = BufWriter::new(File::create(out.join("decoder-issues.jsonl")).unwrap());
    let mut tiles = BufWriter::new(File::create(out.join("tiles.jsonl")).unwrap());
    for (tc, tile) in expanded.egrid.tiles() {
        let class = &db.int.tile_classes[tile.class];
        let name = tc.to_string(&db.int);
        c.count(&format!("tiles.{}", class.name));
        let rects: Vec<_> = expanded.tile_bits(tc).values().copied().collect();
        write_row(
            &mut tiles,
            json!({"tile":name,"class":class.name,"rects":rects.iter().map(|x|format!("{x:?}")).collect::<Vec<_>>()}),
        );
        for (slot, info) in &class.bels {
            let bel = &db.int.bel_slots[slot].name;
            match info {
                BelInfo::Bel(b) => {
                    let bclass = &db.int.bel_classes[db.int.bel_class(slot)];
                    for (aid, attr) in &b.attributes {
                        let a = &bclass.attributes[aid];
                        let (bits, pol): (Vec<TileBit>, Vec<bool>) = match attr {
                            BelAttribute::BitVec(b) => (
                                b.iter().map(|p| p.bit).collect(),
                                b.iter().map(|p| p.inv).collect(),
                            ),
                            BelAttribute::Enum(e) => (e.bits.clone(), vec![false; e.bits.len()]),
                        };
                        c.count("attributes_total");
                        if let Some(v) = c.read(&rects, &bits) {
                            let logical: Vec<bool> =
                                v.iter().zip(&pol).map(|(b, inv)| b ^ inv).collect();
                            let mut value = json!(hex_bits(&logical));
                            let mut valid = true;
                            if let BelAttribute::Enum(e) = attr {
                                let BelAttributeType::Enum(ec) = a.typ else {
                                    panic!()
                                };
                                let matches: Vec<_> = e
                                    .values
                                    .iter()
                                    .filter(|(_, pat)| pat.iter().eq(v.iter().copied()))
                                    .map(|(id, _)| db.int.enum_classes[ec].values[id].clone())
                                    .collect();
                                valid = matches.len() == 1;
                                value = json!(matches);
                            }
                            if valid {
                                c.accept(&rects, &bits);
                                c.count("attributes_decoded");
                            } else {
                                c.count("attributes_unknown_pattern");
                                write_row(
                                    &mut issues,
                                    json!({"kind":"attribute_unknown_pattern","tile":name,"class":class.name,"bel":bel,"attribute":a.name,"raw":hex_bits(&v)}),
                                );
                            }
                            write_row(
                                &mut settings,
                                json!({"tile":name,"class":class.name,"bel":bel,"bel_class":bclass.name,"attribute":a.name,"type":format!("{:?}",a.typ),"width":bits.len(),"value":value,"valid":valid}),
                            );
                        } else {
                            c.count("attributes_unmapped");
                            write_row(
                                &mut issues,
                                json!({"kind":"attribute_unmapped","tile":name,"class":class.name,"bel":bel,"attribute":a.name,"bits":format!("{bits:?}")}),
                            );
                        }
                    }
                    for (iid, input) in &b.inputs {
                        if let BelInput::Invertible(w, bit) = input {
                            if let Some(v) = c.read(&rects, &[bit.bit]) {
                                c.accept(&rects, &[bit.bit]);
                                c.count("input_inverters_decoded");
                                write_row(
                                    &mut settings,
                                    json!({"tile":name,"class":class.name,"bel":bel,"input":format!("{iid:?}"),"wire":w.to_string(&db.int,class),"inverted":v[0]^bit.inv}),
                                );
                            }
                        }
                    }
                }
                BelInfo::SwitchBox(sb) => {
                    for item in &sb.items {
                        match item {
                            SwitchBoxItem::Mux(m) => {
                                c.count("routing_mux_total");
                                if let Some(v) = c.read(&rects, &m.bits) {
                                    let matches: Vec<_> = m
                                        .src
                                        .iter()
                                        .filter(|(_, pat)| pat.iter().eq(v.iter().copied()))
                                        .map(|(w, _)| w.to_string(&db.int, class))
                                        .collect();
                                    let off = m
                                        .bits_off
                                        .as_ref()
                                        .map(|pat| pat.iter().eq(v.iter().copied()))
                                        .unwrap_or(false);
                                    if matches.len() + usize::from(off) == 1 {
                                        c.accept(&rects, &m.bits);
                                        c.count("routing_mux_decoded");
                                        if off {
                                            c.count("routing_mux_off");
                                        } else {
                                            c.count("routing_mux_selected");
                                            write_row(
                                                &mut routes,
                                                json!({"tile":name,"class":class.name,"dst":m.dst.to_string(&db.int,class),"src":matches[0]}),
                                            );
                                        }
                                    } else {
                                        c.count("routing_mux_unknown_pattern");
                                        write_row(
                                            &mut issues,
                                            json!({"kind":"routing_mux_unknown_pattern","tile":name,"class":class.name,"dst":m.dst.to_string(&db.int,class),"raw":hex_bits(&v),"matches":matches,"off":off}),
                                        );
                                    }
                                }
                            }
                            SwitchBoxItem::ProgBuf(p) => {
                                if let Some(v) = c.read(&rects, &[p.bit.bit]) {
                                    c.accept(&rects, &[p.bit.bit]);
                                    c.count("routing_prog_buf_decoded");
                                    if v[0] ^ p.bit.inv {
                                        write_row(
                                            &mut routes,
                                            json!({"tile":name,"kind":"ProgBuf","dst":p.dst.to_string(&db.int,class),"src":p.src.to_string(&db.int,class)}),
                                        );
                                    }
                                }
                            }
                            SwitchBoxItem::ProgInv(p) => {
                                if let Some(v) = c.read(&rects, &[p.bit.bit]) {
                                    c.accept(&rects, &[p.bit.bit]);
                                    c.count("routing_prog_inv_decoded");
                                    write_row(
                                        &mut routes,
                                        json!({"tile":name,"kind":"ProgInv","dst":p.dst.to_string(&db.int,class),"src":p.src.to_string(&db.int,class),"inverted":v[0]^p.bit.inv}),
                                    );
                                }
                            }
                            SwitchBoxItem::Pass(p) => {
                                if let Some(v) = c.read(&rects, &[p.bit.bit]) {
                                    c.accept(&rects, &[p.bit.bit]);
                                    c.count("routing_pass_decoded");
                                    if v[0] ^ p.bit.inv {
                                        write_row(
                                            &mut routes,
                                            json!({"tile":name,"kind":"Pass","dst":p.dst.to_string(&db.int,class),"src":p.src.to_string(&db.int,class)}),
                                        );
                                    }
                                }
                            }
                            SwitchBoxItem::BiPass(p) => {
                                if let Some(v) = c.read(&rects, &[p.bit.bit]) {
                                    c.accept(&rects, &[p.bit.bit]);
                                    c.count("routing_bipass_decoded");
                                    if v[0] ^ p.bit.inv {
                                        write_row(
                                            &mut routes,
                                            json!({"tile":name,"kind":"BiPass","a":p.a.to_string(&db.int,class),"b":p.b.to_string(&db.int,class)}),
                                        );
                                    }
                                }
                            }
                            SwitchBoxItem::PairMux(m) => {
                                c.count("routing_pairmux_total");
                                if let Some(v) = c.read(&rects, &m.bits) {
                                    let matches: Vec<_> = m
                                        .src
                                        .iter()
                                        .filter(|(_, pat)| pat.iter().eq(v.iter().copied()))
                                        .map(|(ws, _)| {
                                            ws.iter()
                                                .map(|w| w.map(|w| w.to_string(&db.int, class)))
                                                .collect::<Vec<_>>()
                                        })
                                        .collect();
                                    if matches.len() == 1 {
                                        c.accept(&rects, &m.bits);
                                        c.count("routing_pairmux_decoded");
                                        write_row(
                                            &mut routes,
                                            json!({"tile":name,"kind":"PairMux","dst":m.dst.iter().map(|w|w.to_string(&db.int,class)).collect::<Vec<_>>(),"src":matches[0]}),
                                        );
                                    } else {
                                        c.count("routing_pairmux_unknown_pattern");
                                        write_row(
                                            &mut issues,
                                            json!({"kind":"pairmux_unknown_pattern","tile":name,"raw":hex_bits(&v),"matches":matches}),
                                        );
                                    }
                                }
                            }
                            SwitchBoxItem::PermaBuf(p) => {
                                c.count("routing_permanent_exported");
                                write_row(
                                    &mut routes,
                                    json!({"tile":name,"kind":"PermaBuf","dst":p.dst.to_string(&db.int,class),"src":p.src.to_string(&db.int,class)}),
                                );
                            }
                            other => {
                                c.count("routing_unsupported_item");
                                write_row(
                                    &mut issues,
                                    json!({"kind":"unsupported_routing","tile":name,"item":format!("{other:?}")}),
                                );
                            }
                        }
                    }
                }
                BelInfo::TestMux(m) => {
                    c.count("test_mux_total");
                    if let Some(v) = c.read(&rects, &m.bits) {
                        let primary = m.bits_primary.iter().eq(v.iter().copied());
                        let groups: Vec<_> = m
                            .groups
                            .iter()
                            .enumerate()
                            .filter(|(_, pat)| pat.iter().eq(v.iter().copied()))
                            .map(|(i, _)| i)
                            .collect();
                        if usize::from(primary) + groups.len() == 1 {
                            c.accept(&rects, &m.bits);
                            c.count("test_mux_decoded");
                            for (dst, w) in &m.wires {
                                let src = if primary {
                                    Some(w.primary_src)
                                } else {
                                    w.test_src[groups[0]]
                                };
                                if let Some(src) = src {
                                    write_row(
                                        &mut routes,
                                        json!({"tile":name,"kind":"TestMux","primary":primary,"dst":dst.to_string(&db.int,class),"src":src.to_string(&db.int,class)}),
                                    );
                                }
                            }
                        } else {
                            c.count("test_mux_unknown_pattern");
                            write_row(
                                &mut issues,
                                json!({"kind":"test_mux_unknown_pattern","tile":name,"bel":bel,"raw":hex_bits(&v),"primary":primary,"groups":groups}),
                            );
                        }
                    }
                }
            }
        }
    }
    settings.flush().unwrap();
    routes.flush().unwrap();
    issues.flush().unwrap();
    tiles.flush().unwrap();
    fs::write(out.join("database-referenced-mask.u8"), &c.referenced).unwrap();
    fs::write(out.join("decoded-mask.u8"), &c.resolved).unwrap();
    let summary = json!({"device":dev.name,"mode":format!("{:?}",bs.mode),"main_frames":bs.frame_info.len(),"main_frames_present":bs.frame_present.iter().filter(|x|*x).count(),"bram_frames":bs.bram_frame_info.len(),"bram_frames_present":bs.bram_frame_present.iter().filter(|x|*x).count(),"iob_present":bs.iob_present,"frame_fixups":bs.frame_fixups.len(),"main_bits":bs.frame_data.len(),"bram_bits":bs.bram_data.len(),"iob_bits":bs.iob.len(),"total_configuration_bits":total,"database_referenced_bits":c.referenced.iter().filter(|&&x|x!=0).count(),"decoded_bits":c.resolved.iter().filter(|&&x|x!=0).count(),"unresolved_bits":c.resolved.iter().filter(|&&x|x==0).count(),"unresolved_set_bits":raw.iter().zip(&c.resolved).filter(|(b,k)|**b!=0&&**k==0).count(),"statistics":c.stats,"coverage_scope":"Unique main/BRAM/IOB storage bits; register fields excluded from denominator. Referenced differs from valid-pattern decoded. Defaults/unused fields are included, not utilization or semantic proof."});
    fs::write(
        out.join("coverage.json"),
        serde_json::to_string_pretty(&summary).unwrap() + "\n",
    )
    .unwrap();
    let mut bond = BufWriter::new(File::create(out.join("package-csg324.txt")).unwrap());
    for (_, pkg, &bid) in &dev.bonds {
        if pkg == "csg324" {
            db.bonds[bid].dump(&mut bond, &db.int).unwrap();
        }
    }
    bond.flush().unwrap();
    println!("{}", serde_json::to_string_pretty(&summary).unwrap());
}
