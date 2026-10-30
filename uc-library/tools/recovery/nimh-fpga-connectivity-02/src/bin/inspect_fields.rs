use prjcombine_entity::EntityId;
use prjcombine_interconnect::db::{BelAttribute, BelAttributeType, BelInfo};
use prjcombine_spartan6::{bitstream::BitPos, db::Database};
use prjcombine_types::bitrect::BitRect as _;
use serde_json::json;
use std::{
    fs::{self, File},
    io::{BufWriter, Write},
    path::Path,
};
fn main() {
    let a: Vec<_> = std::env::args().collect();
    assert_eq!(a.len(), 4);
    let db = Database::from_file(&a[1]).unwrap();
    let dev = db.devices.iter().find(|d| d.name == "xc6slx45").unwrap();
    let ex = db.chips[dev.chip].expand_grid(&db.int, &dev.disabled);
    let mut bs = ex.parse_bitstream(&fs::read(&a[2]).unwrap(), None);
    let fixes: Vec<_> = bs.frame_fixups.iter().map(|(&p, &v)| (p, v)).collect();
    for ((f, b), v) in fixes {
        bs.frame_data.set(f * 1040 + b, v);
    }
    let out = Path::new(&a[3]);
    fs::create_dir_all(out).unwrap();
    let mut f = BufWriter::new(File::create(out.join("field-encodings.jsonl")).unwrap());
    let mut overlap = vec![];
    for (tc, tile) in ex.egrid.tiles() {
        let class = &db.int.tile_classes[tile.class];
        let rects = ex.tile_bits(tc);
        if tc.col.to_idx() == 18 && matches!(tc.row.to_idx(), 8 | 40 | 72 | 104 | 120) {
            overlap.push(json!({"tile":tc.to_string(&db.int),"class":class.name,"rects":rects.values().map(|r|format!("{r:?}")).collect::<Vec<_>>()}));
        }
        for (slot, info) in &class.bels {
            let BelInfo::Bel(b) = info else { continue };
            let bc = &db.int.bel_classes[db.int.bel_class(slot)];
            for (id, attr) in &b.attributes {
                let name = &bc.attributes[id].name;
                if !((bc.name == "DCM" && name == "MODE")
                    || (bc.name == "GLOBAL" && name == "SPI_BUSWIDTH")
                    || (bc.name == "PCILOGICSE" && name == "PCI_CE_DELAY")
                    || (bc.name == "BUFPLL" && name.starts_with("DIVIDE")))
                {
                    continue;
                }
                let bits = match attr {
                    BelAttribute::Enum(e) => e.bits.clone(),
                    BelAttribute::BitVec(v) => v.iter().map(|p| p.bit).collect(),
                };
                let positions: Vec<_> = bits
                    .iter()
                    .map(|b| rects[b.rect].xlat_pos_fwd((b.frame, b.bit)))
                    .collect();
                let actual: Vec<_> = positions.iter().map(|&p| bs.get_bit(p)).collect();
                let patterns = if let BelAttribute::Enum(e) = attr {
                    let BelAttributeType::Enum(ec) = bc.attributes[id].typ else {
                        panic!()
                    };
                    e.values.iter().map(|(v,p)|json!({"value":db.int.enum_classes[ec].values[v],"bits_lsb_first":p.iter().collect::<Vec<_>>()})).collect::<Vec<_>>()
                } else {
                    vec![]
                };
                let record = json!({"tile":tc.to_string(&db.int),"class":class.name,"bel":db.int.bel_slots[slot].name,"attribute":name,"physical_bits":positions.iter().map(|p|format!("{p:?}")).collect::<Vec<_>>(),"storage_indices":positions.iter().map(|p|match p{BitPos::Main(f,b)=>Some(f*1040+b),BitPos::Bram(f,b)=>Some(bs.frame_data.len()+f*18720+b),BitPos::Iob(b)=>Some(bs.frame_data.len()+bs.bram_data.len()+b),_=>None}).collect::<Vec<_>>(),"bits_lsb_first":actual,"patterns":patterns});
                serde_json::to_writer(&mut f, &record).unwrap();
                writeln!(f).unwrap();
            }
        }
    }
    f.flush().unwrap();
    fs::write(
        out.join("clock-tile-geometry.json"),
        serde_json::to_string_pretty(&overlap).unwrap() + "\n",
    )
    .unwrap();
    println!("Saved exact field encodings and CMT/HCLK geometry.");
}
