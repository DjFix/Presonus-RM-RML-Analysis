#include "presonus/mixer_update/FirmwareUpdateComponent.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
using namespace Core::Portable;
namespace {
bool capture = false;
std::vector<std::string> events;
std::vector<unsigned> lookups;
const char *strings[] = {"", "Firmware", "Updating panel: 50%", "initial"};
const ParamInfo textInfo[] = {PARAM_STRING(1, "alert", 0),
                              PARAM_STRING(2, "title", 0),
                              PARAM_STRING(3, "message", 0)};
const ParamInfo progressInfo =
    PARAM_FLOAT(4, "progress", -100, 100, 0, 0, 0, 0, 0, 0);
struct Text final : StringParam {
  unsigned tag;
  Text(const ParamInfo &info) : StringParam(info), tag(info.tag) {}
  void fromString(const char *s, bool edit) override {
    if (capture) {
      unsigned index = 0;
      while (index < 4 && std::strcmp(s, strings[index]))
        ++index;
      assert(index < 4);
      events.push_back("text:" + std::to_string(tag) + ":" +
                       std::to_string(index) + ":" + std::to_string(edit));
    }
    StringParam::fromString(s, edit);
  }
};
struct Progress final : NumericParam {
  Progress() : NumericParam(progressInfo) {}
  void setValue(float v, bool edit) override {
    if (capture) {
      std::uint32_t bits;
      std::memcpy(&bits, &v, 4);
      events.push_back("progress:" + std::to_string(bits) + ":" +
                       std::to_string(edit));
    }
    NumericParam::setValue(v, edit);
  }
};
struct Listener final : Presonus::UC::IFirmwareUpdateListener {
  void onProgress(const char *s, float value) override {
    if (capture) {
      unsigned index = 0;
      while (index < 4 && std::strcmp(s, strings[index]))
        ++index;
      assert(index < 4);
      std::uint32_t bits;
      std::memcpy(&bits, &value, 4);
      events.push_back("listener:" + std::to_string(index) + ":" +
                       std::to_string(bits));
    }
  }
};
struct Fixture final : Presonus::Mixer::FirmwareUpdateComponent {
  Fixture(Parameter *p, Presonus::UC::IFirmwareUpdateListener *l)
      : FirmwareUpdateComponent(presonus::mixer_update::CallbackSourcePort{},
                                nullptr, 0, p, l) {}
  void own(Parameter *p) { paramList.add(p); }
};
} // namespace
extern "C" Parameter *
realByTag(const Component *,
          int) asm("__real__ZNK4Core8Portable9Component17getParameterByTagEi");
extern "C" Parameter *wrapByTag(const Component *c, int tag) asm(
    "__wrap__ZNK4Core8Portable9Component17getParameterByTagEi");
extern "C" Parameter *wrapByTag(const Component *c, int tag) {
  if (capture)
    lookups.push_back(tag);
  return realByTag(c, tag);
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream in(argv[1]);
  if (!in)
    return 2;
  unsigned entry, method, mask, present, listener, bits, a, b, c, n, m,
      checked = 0;
  while (in >> entry >> method >> mask >> present >> listener >> bits >> a >>
         b >> c) {
    std::array<unsigned, 3> finalText{};
    for (auto &v : finalText)
      in >> v;
    in >> n;
    std::vector<unsigned> wantedLookups(n);
    for (auto &v : wantedLookups)
      in >> v;
    in >> m;
    std::vector<std::string> wanted(m);
    for (auto &v : wanted)
      in >> v;
    auto progress = std::make_unique<Progress>();
    Listener target;
    Fixture component(present ? progress.get() : nullptr,
                      listener ? &target : nullptr);
    std::array<Text *, 3> texts{};
    for (unsigned tag = 1; tag <= 3; ++tag)
      if (mask & (1U << (tag - 1))) {
        auto *p = new Text(textInfo[tag - 1]);
        p->fromString("initial", false);
        texts[tag - 1] = p;
        component.own(p);
      }
    if (mask & 8U)
      component.own(progress.release());
    events.clear();
    lookups.clear();
    capture = true;
    float value;
    std::memcpy(&value, &bits, 4);
    if (method == 0)
      component.setText(strings[a], strings[b]);
    else if (method == 1)
      component.onProgress(strings[a], strings[b], value);
    else if (method == 2)
      component.dismissAlert();
    else if (method == 3)
      component.doAlert(strings[a], strings[b], strings[c]);
    else
      return 3;
    capture = false;
    if (events != wanted || lookups != wantedLookups) {
      std::cerr << "order mismatch " << checked << '\n';
      return 4;
    }
    for (unsigned i = 0; i < 3; ++i)
      if (texts[i])
        assert(std::strcmp(texts[i]->getText().str(), strings[finalText[i]]) ==
               0);
    ++checked;
  }
  if (checked != 11520)
    return 5;
  {
    Fixture empty(nullptr, nullptr);
    bool caught = false;
    try {
      empty.dismissAlert();
    } catch (const std::logic_error &) {
      caught = true;
    }
    assert(caught);
  }
  std::cout << "{\"passed\":true,\"cases\":" << checked
            << ",\"mandatory_missing_param_port_guard\":true}\n";
}
