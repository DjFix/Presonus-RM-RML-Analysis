"""Assemble the exact approved final wave against registered Actual08."""
import sys

from assemble_actual07_authorized import actual_reference, normalize_review_evidence, ccl, BOOK
from context_runtime import guard, sha
from packet_cycle import CYCLE, ROOT, materialize, read, reference, save

P = CYCLE / "packeting"
AUTH = P / "ACTUAL08-VERIFIED-PROPOSED10-AUTHORITY-REVIEW01.json"
DIGEST = "ba97032f10922d954ea8699ed913322b85fe5c9c017640a06068317491de5231"
PROBE = P / "ACTUAL08-R22-RM-PROVIDER-PROBE-READBACK01.json"
INC = "uc-library/include/presonus/"
SRC = "uc-library/src/Presonus/"
CHANNEL = (INC + "SLChannel.hpp", SRC + "SLChannel.cpp")
MIXER = (INC + "MixerClientComponentBase.hpp", SRC + "MixerClientComponentBase.cpp")
LCD = (INC + "panel/LCDComponent.hpp", SRC + "Panel/LCDComponent.cpp")
CCL = "third_party/ccl-framework/core/portable/gui/"
COLOR_ROUTES = {
    636948: ("existing_implementation", "MixerClientComponentBase::getSelectedChannel", MIXER),
    637104: ("pinned_provider", "Core::Portable::GraphicsRenderer::drawBitmap", ccl("portable/gui/coregraphics")),
    **{site: ("pinned_provider", "Core::Portable::GraphicsRenderer::fillRect", ccl("portable/gui/coregraphics"))
       for site in (637208, 637264, 637320)},
}
PALETTE = (INC + "color/IColorConverter.hpp", INC + "color/MixerColorConverter.hpp", SRC + "Color/MixerColorConverter.cpp")
PALETTE_SITES = {
    386668: ("existing_implementation", "IColorConverter color-to-index typed slot", PALETTE),
    63612: ("existing_implementation", "IColorConverter color-to-index typed slot", PALETTE),
    386304: ("existing_implementation", "IColorConverter index-to-color typed slot", PALETTE),
    63248: ("existing_implementation", "IColorConverter index-to-color typed slot", PALETTE),
    **{site: ("pinned_provider", "Core::Portable::NumericParam::setValue", ccl("portable/coreparams"))
       for site in (386700, 63644)},
    **{site: ("pinned_provider", "Core::Portable::NumericParam::getValue", ccl("portable/coreparams"))
       for site in (386288, 63232)},
    **{site: ("existing_implementation", "SLChannelBase::getColorParameter", CHANNEL)
       for site in (386356, 63300)},
}
METER_ROUTES = {78460, 573536, 78400, 573476, 573392, 78316}


def boundary(task, site, names, native):
    if not names:
        if task == "cycle20_g01_s20":
            assert native["known_virtual_slots"][str(site)]["mangled"]
            kind, name, paths = COLOR_ROUTES[site]
            return kind, name, paths, "Replay the exact original receiver/vtable slot and compare the actual typed provider offline."
        if task in {"cycle20_g02_s16", "cycle20_g02_s17", "cycle20_g02_s18"} and site in METER_ROUTES:
            name = "Core::Portable::NumericParam::getValue" if task.endswith("s18") else "Core::Portable::NumericParam::setValue"
            return "pinned_provider", name, ccl("portable/coreparams"), "Bind genuine CCL numeric parameter and preserve the independently observed role and null boundaries."
        if task == "cycle20_g07_r22" and site in {618640, 121888}:
            paths = LCD + BOOK + (INC + "panel/MixerLCD.hpp", SRC + "Panel/MixerLCD.cpp") if site == 618640 else ()
            return ("existing_implementation", "RM typed LCDComponent::getBook(11) and existing Book roster" if paths else "CS18 abstract ILCDDelegate second slot",
                    paths, "Replay exact role forwarding. Use real RM tag 11 roster; keep the CS18 abstract call scoped without inventing a concrete receiver.")
        if task in {"cycle20_g10_s17", "cycle20_g10_s18"}:
            kind, name, paths = PALETTE_SITES[site]
            return kind, name, paths, "Replay exact role boundary, using concrete CS18 native palette and the bounded RM abstract slot fixture. Use the actual typed portable palette and CCL parameters."
        raise ValueError((task,site,names))
    assert len(names) == 1, names
    name = names[0]
    if name.startswith("Presonus::SLChannelBase::get"):
        return "existing_implementation", name, CHANNEL, "Use and replay the exact already admitted portable channel accessor."
    if name == "Presonus::MappableMixer::getColorConverter() const":
        return "existing_implementation", name, (INC + "MappableMixer.hpp", SRC + "MappableMixer.cpp") + PALETTE, "Bind the existing real typed palette provider."
    if name.startswith("Core::Portable::ColorParam::"):
        return "pinned_provider", name, ccl("portable/coreparams"), "Use genuine CCL color parameter with the observed offline propagation flag."
    if name == "Core::Vector<Presonus::IPresetHandler::Preset*>::resize(int)":
        return "pinned_provider", name, ("third_party/ccl-framework/core/public/corevector.h",), "Use the pinned Core vector shrink operation after original-owned raw allocations are released; cover actual unsized release and zero size."
    if name.startswith("Core::Portable::View::"):
        return "pinned_provider", name, ccl("portable/gui/coreview"), "Use the real pinned CCL View provider."
    if name.startswith("Core::Portable::Control::"):
        return "pinned_provider", name, ccl("portable/gui/corecontrols"), "Use the real pinned CCL Control provider."
    if name.startswith("Core::Portable::Component::~"):
        return "pinned_provider", name, ccl("portable/corecomponent"), "Observe the real pinned CCL base destruction."
    if name == "Presonus::Panel::Book::~Book()":
        return "existing_implementation", name, BOOK, "Observe actual typed Book cleanup on the exact relevant normal or unwind branch."
    if name in {"__aeabi_idiv","__divsi3","__dynamic_cast@@CXXABI_1.3","__floatunsisf","__aeabi_ui2f","__aeabi_fcmpgt","__floatsisf","__aeabi_i2f","__fixsfsi","__aeabi_f2iz",
                "operator delete(void*)@@GLIBCXX_3.4","__cxa_end_cleanup@@CXXABI_1.3"}:
        return "existing_implementation", name, (), "Exact original runtime boundary. Independently compare the real host numeric, RTTI, or lifecycle effect applicable to this call."
    raise ValueError((task,site,name))


def main():
    wave = int(sys.argv[1])
    assert sha(AUTH) == DIGEST
    authority = read(AUTH)
    assert authority["active"] == read(ROOT / "dependency-graph/ACTIVE.json")
    guard(ROOT, authority["active"])
    spec = authority["waves"][wave - 1]
    inventory = P / f"actual08-final10-projected-wave{wave:02}-inventory01/INVENTORY.json"
    authorized = {item["task"]: item for items in spec["owners"].values() for item in items}
    manifest = read(inventory)
    assert len(authorized) == (7,2,1)[wave-1]
    for lane in manifest["lanes"]:
        assert [row["task_id"] for row in lane["tasks"]] == [item["task"] for item in spec["owners"][lane["name"]]]
    prefix = P / f"actual08-authorized-wave{wave:02}"
    renewed = prefix.with_name(prefix.name + "-inputs01.json")
    reviews = {}
    for lane in manifest["lanes"]:
        for row in lane["tasks"]:
            task, candidate = row["task_id"], row["candidate"]
            want = authorized[task]
            assert row["targets"] == want["originals"] and candidate["work_item_id"] == want["work_item_id"]
            assert sorted(row["production"]) == sorted(want["owned_files"])
            if "catalog_revision" not in candidate:
                candidate["catalog_revision"] = candidate["equivalence_decision"]["revision"]
            observed = candidate["native_lifecycle_observation"]
            assert sha(ROOT / observed["path"]) == observed["sha256"]
            native = read(ROOT / observed["path"])
            prior = dict(observed, kind="review_record", scope="Independent exact role-native observation")
            evidence = [prior, reference(AUTH, "review_record", "Exact live provider predecessor and owner verification")]
            site_reviews = {}
            all_paths = set(candidate.get("frozen_provider_files", {}))
            for key, item in row["boundaries"].items():
                kind, name, paths, why = boundary(task, item["observed"]["site"], item["routing_context"]["target_names"], native)
                if task == "cycle20_g07_r22" and paths:
                    provider_evidence = [reference(PROBE, "review_record", "Actual compiled and rerun RM tag-11 Book provider proof")]
                else:
                    provider_evidence = []
                all_paths.update(paths)
                site_reviews[key] = dict(kind="dependency", reason=why, dependency=dict(kind=kind, name=name,
                    binding_domain=why, evidence=[prior, *provider_evidence, *(actual_reference(path) for path in paths)]))
            objective = candidate["bounded_selection_work"]
            for path in want["observed_source_hashes"]:
                if path.startswith("uc-library/") and path not in row["production"]:
                    if any(name in path for name in ("MeterBallistics.hpp", "Book.hpp", "LCDComponent", "MixerLCD")):
                        all_paths.add(path)
            evidence.extend(actual_reference(path) for path in sorted(all_paths))
            work = dict(objective=objective, owned_files=row["production"], oracle_plan="Compare each original executable range independently with actual typed host effects and pinned providers.")
            reviews[task] = dict(target=row["target"], work_item_id=candidate["work_item_id"], native_evidence_sha256=row["native"]["sha256"],
                reviewer="Root-approved Actual08 exact role and local typed-provider review", namespace=candidate["scope"], objective=objective,
                domain="Exact original offline role behavior and reviewed typed source-port ownership.", execution_boundaries=site_reviews,
                extra_source_reads=sorted(all_paths), requirements={name: dict(status="bounded_work", reason=objective,
                evidence=evidence, work=work) for name in ("declarations", "state", "lifecycle", "providers")})
    assert set(reviews) == set(authorized)
    save(renewed, manifest)
    rendered = prefix.with_name(prefix.name + "-review01.json")
    grant = f"Root explicitly approved Actual08 wave {wave} under authority {DIGEST}, sets 7/2/1, exact graph 5073f783026c2afed57eb662c1e3ebe25e9d77e8d0c334c922ad49e5fc8a1917."
    save(rendered, normalize_review_evidence(dict(tasks=reviews, smaller_batch_authorization=grant, production_continuation=grant)))
    output = prefix.with_name(prefix.name + "-plans01")
    materialize(renewed, rendered, output, prefix.with_name(prefix.name + "-capture01"))
    print(output / "TASKS.json")


if __name__ == "__main__":
    main()
