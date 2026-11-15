#include "presonus/surface/DawFxPageComponent.hpp"
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>
using namespace Core::Portable;
struct State {
  bool folder;
  int count;
  std::vector<std::string> trace;
};
struct Mode : NumericParam {
  State &state;
  Mode(const ParamInfo &info, State &s) : NumericParam(info), state(s) {}
  ParamValue getValue() const override {
    state.trace.push_back("mode");
    return NumericParam::getValue();
  }
};
namespace Presonus::Surface {
struct DawFxTestAccess {
  static int insert(const DawFxPageComponent &p) { return p.insertOffset_; }
  static int send(const DawFxPageComponent &p) { return p.sendOffset_; }
};
} // namespace Presonus::Surface
int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  int delta = std::stoi(argv[1]);
  auto axis = static_cast<WheelEvent::Axis>(std::stoi(argv[2]));
  unsigned cases = 0;
  for (bool present : {false, true})
    for (float value : {-1.f, 0.f, 1.f, 1.5f, 2.f})
      for (bool folder : {false, true})
        for (int count : {0, 1, 5, 6, 11, 101})
          for (int initial : {-1, 0, 5, 10, 2147483647}) {
            State s{folder, count, {}}, reference{folder, count, {}};
            ParamInfo info{};
            info.type = ParamInfo::kFloat;
            info.minValue = -100;
            info.maxValue = 100;
            Mode mode(info, s), referenceMode(info, reference);
            mode.setValue(value);
            referenceMode.setValue(value);
            auto bindings = [](State &state) {
              return presonus::surface::DawFxBindings{
                  &state,
                  [](void *p) {
                    auto &s = *static_cast<State *>(p);
                    s.trace.push_back("folder");
                    return s.folder;
                  },
                  [](void *p) {
                    auto &s = *static_cast<State *>(p);
                    s.trace.push_back("count");
                    return s.count;
                  },
                  [](void *p, bool force) {
                    static_cast<State *>(p)->trace.push_back(force ? "update1"
                                                                   : "update0");
                  }};
            };
            Presonus::Surface::DawFxPageComponent page(
                present ? &mode : nullptr, bindings(s), initial, 5);
            Presonus::Surface::DawFxPageComponent provider(
                present ? &referenceMode : nullptr, bindings(reference),
                initial, 5);
            s.trace.clear();
            reference.trace.clear();
            WheelEvent event(delta, axis);
            page.onWheelInput(event);
            // This is the existing production provider, not a synthetic model.
            provider.addListOffset(delta);
            using Access = Presonus::Surface::DawFxTestAccess;
            if (Access::insert(page) != Access::insert(provider) ||
                Access::send(page) != Access::send(provider) ||
                s.trace != reference.trace || event.delta != delta ||
                event.axis != axis)
              return 1;
            ++cases;
          }
  std::cout << cases << " provider regressions passed\n";
}
