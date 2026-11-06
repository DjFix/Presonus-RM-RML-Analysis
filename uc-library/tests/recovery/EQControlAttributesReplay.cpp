#include "core/portable/corecomponent.h"
#include "presonus/mixer_dsp/EQControl.hpp"
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <iostream>
#include <map>
#include <string>
#include <vector>
using namespace Core;
using namespace Core::Portable;
namespace {
struct Image : Bitmap {
  Image(int w, int h, int frames) : Bitmap(w, h, kBitmapRGBAlpha, 0) {
    setFrameCount(frames);
  }
  int references() const { return useCount; }
};
// Only fixture resource registration is exposed. All manager lookups, Bitmap
// reference operations, ViewAttributes and View behavior are real pinned CCL.
struct Images : BitmapManager {
  std::vector<Image *> images;
  Images() {
    for (auto values :
         {std::array<int, 3>{22, 30, 3}, {33, 40, 4}, {12, 24, 2}}) {
      auto *descriptor = new BitmapDescriptor;
      auto *image = new Image(values[0], values[1], values[2]);
      images.push_back(image);
      descriptor->setBitmap(image);
      descriptor->setAlwaysCached(true);
      addBitmap(images.size() == 1   ? "img"
                : images.size() == 2 ? "handle"
                                     : "band",
                descriptor);
    }
  }
};
Images &images() {
  static Images manager;
  return manager;
}
struct Controller : Component, ComponentViewController<Controller> {
  std::map<Parameter *, int> ids;
  std::vector<std::pair<std::string, int>> lookups;
  void *castTo(TypeID type) override {
    if (type == ViewController::kTypeID)
      return static_cast<ViewController *>(this);
    return Component::castTo(type);
  }
  int next = 4;
  Controller() {
    std::vector<ParamInfo> info;
    for (int i = 0; i < 4; ++i)
      for (const char *prefix :
           {"type", "gain", "q", "freq", "active", "selected"}) {
        ParamInfo p{};
        p.type = ParamInfo::kFloat;
        p.tag = static_cast<int>(info.size());
        std::string name = std::string(prefix) + std::to_string(i);
        std::snprintf(p.name, sizeof p.name, "%s", name.c_str());
        p.minValue = 0;
        p.maxValue = 20000;
        p.defaultValue = 1;
        p.midValue = 1;
        p.deltaValue = .002f;
        info.push_back(p);
      }
    ParamInfo hp{};
    hp.type = ParamInfo::kFloat;
    hp.tag = 99;
    std::snprintf(hp.name, sizeof hp.name, "hp");
    hp.maxValue = 20000;
    hp.defaultValue = 100;
    hp.midValue = 1;
    info.push_back(hp);
    // Real CCL ownsInfo=true copies each temporary descriptor independently.
    addParameters(info.data(), static_cast<int>(info.size()), true);
  }
  void *getObjectForView(CStringPtr name, CStringPtr type) override {
    auto *p = static_cast<Parameter *>(
        ComponentViewController<Controller>::getObjectForView(name, type));
    if (p && !ids.count(p))
      ids[p] = next++;
    lookups.emplace_back(name ? name : "", p ? ids[p] : 0);
    return p;
  }
  int id(Parameter *p) const { return p ? ids.at(p) : 0; }
};
Controller *controller = nullptr;
std::vector<std::vector<int>> sets;
} // namespace
extern "C" BitmapManager &
fixtureManager() asm("__wrap__ZN4Core8Portable15StaticSingletonINS0_"
                     "13BitmapManagerEE8instanceEv");
extern "C" BitmapManager &fixtureManager() { return images(); }
extern "C" void
realSetBand(Presonus::EQControl *, int, Presonus::EQControl::BandParams) asm(
    "__real__ZN8Presonus9EQControl7setBandEiNS0_10BandParamsE");
extern "C" void
captureSetBand(Presonus::EQControl *, int, Presonus::EQControl::BandParams) asm(
    "__wrap__ZN8Presonus9EQControl7setBandEiNS0_10BandParamsE");
extern "C" void captureSetBand(Presonus::EQControl *eq, int i,
                               Presonus::EQControl::BandParams p) {
  const auto &stored = eq->portableParameterState().at(i);
  assert(stored.slot3 == p.slot3 && stored.gain == p.gain && stored.q == p.q &&
         stored.frequency == p.frequency && stored.slot4 == p.slot4 &&
         stored.slot5 == p.slot5);
  sets.push_back({i, controller->id(p.slot3), controller->id(p.gain),
                  controller->id(p.q), controller->id(p.frequency),
                  controller->id(p.slot4), controller->id(p.slot5),
                  eq->portableBandImage(i) != nullptr,
                  eq->portableBandState().at(i).forceCurve});
  realSetBand(eq, i, p);
}
int main() {
  int flags, count, entries, repeat;
  while (std::cin >> flags >> count >> entries >> repeat) {
    assert(!images().images[0]->isReferenced() &&
           !images().images[1]->isReferenced() &&
           !images().images[2]->isReferenced());
    Controller ctl;
    controller = &ctl;
    sets.clear();
    {
      Presonus::EQControl eq(Rect(0, 0, 100, 50));
      auto *state = eq.portableConstructorState();
      for (int tag = 0; tag < 3; ++tag)
        ctl.ids[state->hpfParameters.byTag(tag)] = tag + 1;
      eq.bindPortableViewController(ctl);
      DefaultAllocatedAttributes a;
      a.set("numBands", count);
      a.set("bufferedDraw", bool(flags & 1) ? 1 : 0);
      a.set("handleDiameter", 17);
      if (flags & 2)
        a.set("hpf", flags & 4 ? "hp" : "missing");
      if (flags & (8 | 2048)) {
        auto *r = a.makeAttributes("displayRange");
        r->set("minFreq", 20);
        if (!(flags & 2048))
          r->set("maxFreq", 20000);
        if (!(flags & 2048))
          r->set("minLevel", -24);
        if (!(flags & 2048))
          r->set("maxLevel", 18);
      }
      if (flags & 16)
        a.set("image", "img");
      if (flags & 32)
        a.set("handle", "handle");
      Rect rect(3, -4, flags & 64 ? 3 : 83, flags & 64 ? -4 : 46);
      a.set("size", ResourceAttributes::packRect(rect));
      if (flags & 128)
        a.set("offLineColor", static_cast<int64>(0x7f332211));
      auto *style = a.makeAttributes("style");
      style->set("forecolor", static_cast<int64>(0xffa0b0c0));
      if (entries) {
        auto *q = a.makeQueue("bands");
        for (int i = 0; i < entries; ++i) {
          if (i == 0 && flags & 1024)
            q->append(42);
          auto *r = q->appendAttributes(a.getAllocator());
          for (const char *key :
               {"type", "gain", "q", "freq", "active", "selected"}) {
            if (flags & 256 &&
                (std::string(key) == "q" || std::string(key) == "selected"))
              continue;
            auto name = std::string(key) + std::to_string(i);
            r->set(key, name.c_str());
          }
          if (flags & 512)
            r->set("handle", "band");
        }
      }
      eq.setAttributes(a);
      if (repeat) {
        flags ^= 33;
        a.set("bufferedDraw", flags & 1 ? 1 : 0);
        if (flags & 32)
          a.set("handle", "handle");
        else
          a.remove("handle");
        eq.setAttributes(a);
      }
      rect = state->control.getSize();
      if (rect.getWidth() > 0 && rect.getHeight() > 0) {
        assert((eq.portableBitmap() != nullptr) == eq.isBufferedDraw());
        assert(eq.portableBufferPresent() == eq.isBufferedDraw());
      }
      if (flags & 2048)
        assert(!state->frequency.sourceRangeSupported());
      std::cout << "{\"count\":" << eq.portableRequestedBandCount()
                << ",\"buffered\":" << eq.isBufferedDraw()
                << ",\"diameter\":" << state->handleDiameter << ",\"rect\":["
                << rect.left << ',' << rect.top << ',' << rect.right << ','
                << rect.bottom << "],\"color\":["
                << int(state->offlineColor.red) << ','
                << int(state->offlineColor.green) << ','
                << int(state->offlineColor.blue) << ','
                << int(state->offlineColor.alpha) << "],\"ranges\":[";
      int n = 0;
      for (const Interpolator *p : std::array<const Interpolator *, 4>{
               &state->gain, &state->y, &state->frequency, &state->x}) {
        if (n++)
          std::cout << ',';
        std::cout << '[' << p->getMinRange() << ',' << p->getMaxRange() << ','
                  << p->getMidRange() << ']';
      }
      std::cout << "],\"lookups\":[";
      n = 0;
      for (const auto &[name, id] : ctl.lookups) {
        if (n++)
          std::cout << ',';
        std::cout << "[" << (name.empty() ? "null" : "\"" + name + "\"") << ','
                  << id << ']';
      }
      std::cout << "],\"sets\":[";
      n = 0;
      for (const auto &v : sets) {
        if (n++)
          std::cout << ',';
        std::cout << '[' << v[0] << ",[";
        for (int j = 1; j < 7; ++j) {
          if (j > 1)
            std::cout << ',';
          std::cout << v[j];
        }
        std::cout << "]," << v[7] << ',' << v[8] << ']';
      }
      std::cout << "],\"image_refs\":[";
      n = 0;
      for (auto *image : images().images) {
        if (n++)
          std::cout << ',';
        std::cout << image->references();
      }
      std::cout << "]}\n";
      // Real interpolation endpoint/clipping observations on configured
      // providers.
      if (flags & 8) {
        assert(state->frequency.sourceRangeSupported());
        assert(eq.freqToX(20) == 0);
        assert(eq.freqToX(20000) == rect.getWidth());
        assert(state->gain.rangeToNormalized(-100) == 0);
        assert(state->gain.rangeToNormalized(100) == 1);
      }
    }
    for (auto *image : images().images)
      assert(!image->isReferenced());
  }
}
