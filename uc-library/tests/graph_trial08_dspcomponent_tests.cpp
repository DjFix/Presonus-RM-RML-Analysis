#include "presonus/trial08/DspComponent.hpp"
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>
// Test-only field-free completion gives the opaque application handle a real
// object lifetime. No original fields, layout, vtable or provider is claimed.
namespace Presonus::Dsp {
class IController {};
} // namespace Presonus::Dsp
struct TestBoundary : Presonus::dspcomponent_port::Boundary {
  unsigned flag;
  std::vector<std::string> trace;
  explicit TestBoundary(unsigned f) : flag(f) {}
  int count(Presonus::Dsp::IController &) override {
    trace.push_back("slot_0xc");
    return 0;
  }
  float value(Presonus::Dsp::IController &, int) override { std::abort(); }
  void set(Presonus::Dsp::IController &, int, float) override { std::abort(); }
  unsigned flags(Presonus::Dsp::IController &) override {
    trace.push_back("slot_0x3c");
    return flag;
  }
  void acknowledge(Presonus::Dsp::IController &) override {
    trace.push_back("slot_0x40");
  }
  bool readout(Presonus::Dsp::IController &, int) override { std::abort(); }
  int load(const Core::Portable::InputStorage &) override {
    trace.push_back("base_load");
    return 37;
  }
  void idle() override { trace.push_back("base_idle"); }
  void changed(Core::Portable::Parameter *, int) override {
    trace.push_back("base_param");
  }
};
int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  std::string method = argv[1];
  if (method == "c1") {
    std::string input = argv[2];
    auto colon = input.find(':');
    bool present = input.substr(0, colon) == "1";
    std::string name = input.substr(colon + 1);
    Presonus::Dsp::IController live;
    int cleaned = 0;
    struct Child : Core::Portable::Component {
      int &cleaned;
      explicit Child(int &c) : Component("child"), cleaned(c) {}
      ~Child() { ++cleaned; }
    };
    {
      Presonus::DspComponent constructed(name.c_str(),
                                         present ? &live : nullptr);
      auto &core = constructed.coreComponent();
      auto &attrs = constructed.linkAttributes();
      auto &state = constructed.lifecycleState();
      if (std::string(core.getName()) != name.substr(0, 31) ||
          core.getParent() != nullptr || core.countChildren() != 0 ||
          core.countParameters() != 0 || core.getStorageTag() != 0 ||
          attrs.countAttributes() != 0)
        return 8;
      std::cout << "{\"serverFlag\":" << state.serverFlag
                << ",\"baseFlag\":" << state.baseFlag
                << ",\"targetedFlag\":" << state.targetedFlag
                << ",\"slave\":" << state.slave
                << ",\"enabled\":" << state.enabled
                << ",\"partner\":" << (state.partner ? 1 : 0)
                << ",\"controller\":"
                << (constructed.getController() == (present ? &live : nullptr)
                        ? (present ? 0x1001000 : 0)
                        : -1)
                << ",\"readoutCount\":" << constructed.readoutCount() << "}";
      const std::string copiedName(core.getName());
      if (!name.empty())
        name[0] = 'Q';
      if (std::string(core.getName()) != copiedName)
        return 11;
      attrs.set("lifecycle-test", 42);
      if (attrs.countAttributes() != 1)
        return 9;
      core.addChild(new Child(cleaned));
    }
    if (cleaned != 1)
      return 10;
    return 0;
  }
  long long value = std::stoll(argv[2]);
  Presonus::DspComponent c("fixture", nullptr);
  if (method == "castTo") {
    std::cout << (c.castTo(static_cast<int>(value)) ? 0x1000000 : 0);
    return 0;
  }
  if (method == "getController") {
    // Numeric labels are used only for pointer identity; never dereferenced.
    auto *label = reinterpret_cast<Presonus::Dsp::IController *>(
        static_cast<uintptr_t>(value));
    Presonus::DspComponent identity("fixture", label);
    std::cout << reinterpret_cast<uintptr_t>(identity.getController());
    return 0;
  }
  if (method == "isDspParameter") {
    Core::Portable::ParamInfo info{};
    info.type = static_cast<int>(value);
    Core::Portable::NumericParam p(info);
    std::cout << c.isDspParameter(&p);
    return 0;
  }
  TestBoundary b(static_cast<unsigned>(value));
  Presonus::Dsp::IController liveController;
  Presonus::DspComponent control("fixture", value ? &liveController : nullptr);
  control.bind(b);
  int result = 0;
  if (method == "construct")
    control.construct();
  else if (method == "syncValues")
    control.syncValues(value != 0);
  else if (method == "syncReadouts")
    control.syncReadouts();
  else if (method == "onIdle")
    control.onIdle();
  else if (method == "paramChanged")
    control.paramChanged(nullptr, 0x1001000);
  else if (method == "load") {
    Core::Portable::Attributes attributes(
        Core::Portable::AttributeAllocator::getDefault());
    Core::Portable::InputStorage storage(attributes);
    result = control.load(storage);
  } else
    return 3;
  std::cout << "{\"count\":" << control.readoutCount()
            << ",\"result\":" << result << ",\"trace\":[";
  for (size_t i = 0; i < b.trace.size(); ++i) {
    if (i)
      std::cout << ",";
    std::cout << "\"" << b.trace[i] << "\"";
  }
  std::cout << "]}";
  return 0;
}
